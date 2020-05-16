import json
import uuid
import os
import threading
import requests
import datetime

from urllib.parse import urlparse
import urllib.parse

from random import randrange

from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth1

from urllib.request import Request, urlopen
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from flask import Flask, request, render_template, g, jsonify, Blueprint, current_app, make_response
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, HTTPAuth
from flask_restplus import Resource, Api, abort, Namespace
from flask import redirect, render_template, url_for
from flask_mail import Mail, Message
from flask_login import login_required, login_user, logout_user 

from sqlalchemy import or_
from sqlalchemy import DateTime
from sqlalchemy import desc

from ..helpers.helpers import *
from ..helpers.namespace import APINamespace
from ..database.database import Session
from ..configuration.config import PASSWORD_SECRET_KEY

from ..models.user import User
from ..models.post import Post
from ..models.section import Section
from ..models.category import Category
from ..models.category_section import CategorySection
from ..models.post_content import PostContent
from ..models.section_post import SectionPost
from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Sections')

@api.route('/<sectionID>/add/posts')
class AddPostSectionViewPosts(Resource):
    @login_required
    def get(self, sectionID):
        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        postsJS = []
        posts = session.query(Post).order_by(desc(Post.created), Post.id).all()
        for post in posts:
            postsJS.append(post.publicJSON())

        session.close()


        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/sections/admin_panel_section_add_posts.html', posts=postsJS, section=sectionJS), 200, headers)

@api.route('/<sectionID>/add/<postID>')
class AddPostSection(Resource):
    @login_required
    def get(self, sectionID, postID):
        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()

        if section == None:
            abort(404)

        post = session.query(Post).filter_by(id=postID).first()

        if post == None:
            abort(404)

        sectionpost = session.query(SectionPost).filter_by(section=sectionID, post=postID).first()
        if sectionpost is None:
            sectionpost = SectionPost()

        sectionpost.post = postID
        sectionpost.section = sectionID

        session.add(sectionpost)
        session.commit()
        session.close()

        track_activity('Added post to section', sectionID, 'section')

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Sections_view_section', id=sectionID))


@api.route('/<sectionID>/delete')
class DeleteSection(Resource):
    @login_required
    def get(self, sectionID):
        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()
        if section is None:
            abort(404)
        session.delete(section)

        post_links = session.query(SectionPost).filter_by(section=sectionID).all()
        for content in post_links:
            session.delete(content)


        session.commit()
        session.close()

        track_activity('Deleted section', sectionID, 'section')

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Sections_list_sections'))

@api.route('/<sectionID>/<postID>/post/delete')
class DeletePost(Resource):
    @login_required
    def get(self, postID, sectionID):
        session = Session()

        link = session.query(SectionPost).filter_by(section=sectionID, post=postID).first()
        if link is not None:
            session.delete(link)

        session.commit()
        session.close()

        track_activity('Deleted post from section', sectionID, 'section')

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Sections_view_section', id=sectionID))


@api.route('/list')
class ListSections(Resource):
    @login_required
    def get(self):
        session = Session()

        sectionsJS = []
        sections = session.query(Section).order_by(desc(Section.last_updated), Section.id).all()
        for section in sections:
            sectionsJS.append(section.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/sections/admin_panel_sections.html', sections=sectionsJS), 200, headers)

@api.route('/view')
class ViewSection(Resource):
    @login_required
    def get(self):
        sectionID = request.args.get('id')
        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()
        if section is None:
            abort(404)

        section_posts = session.query(SectionPost).filter_by(section=sectionID).order_by(SectionPost.order, SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(id=link.post).first()
            if post is not None:
                js = post.publicJSON()
                js['order'] = link.order
                postsJS.append(js)

        sectionJS = section.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/sections/admin_panel_view_section.html', section=sectionJS, posts=postsJS), 200, headers)

@api.route('/<sectionID>/<postID>/order')
class UpdateSectionOrder(Resource):
    @login_required
    def post(self, sectionID, postID):
        order = request.form['order']
       
        session = Session()

        category_section = session.query(SectionPost).filter_by(section=sectionID, post=postID).first()
        if category_section is None:
            return redirect(url_for('Sections_view_section', id=sectionID))
        category_section.order = order
        session.commit()
        session.close()

        track_activity('Changed order of section', sectionID, 'section')

        return redirect(url_for('Sections_view_section', id=sectionID))


@api.route('/create')
class CreateSection(Resource):
    @login_required
    def post(self):
        sectionID = request.args.get('id', None)


        title = request.form['title']
        content = request.form['content']
        public = False
        if request.form.get('public') != None:
            public = True

        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()
        if section is None:
            section = Section()

        section.title = title
        section.description = content
        section.public = public

        session.add(section)
        session.commit()
        sectionID = section.id
        session.close()

        track_activity('Updated section', sectionID, 'section')

        return redirect(url_for('Sections_view_section', id=sectionID))
    @login_required
    def get(self):
        sectionID = request.args.get('id')
        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()
        if section is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/sections/admin_panel_create_section.html', section=Section().blankJSON()), 200, headers)

        sectionJS = section.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/sections/admin_panel_create_section.html', section=sectionJS), 200, headers)

