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
from ..models.post_image import PostImage
from ..models.link import Link
from ..models.literature import Literature
from ..models.literature_link import LiteratureLink
from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Pages')#Api(blueprint)

@api.route('/home')
class Home(Resource):
    def get(self):
        session = Session()

        linksJS = []
        links = session.query(Link).order_by(desc(Link.created), Link.id).limit(2)
        for link in links:
            linksJS.append(link.publicJSON())

        litJS = []
        lits = session.query(Literature).order_by(desc(Literature.created), Literature.id).limit(3)
        for lit in lits:
            litJS.append(lit.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/home.html', links=linksJS, literatures=litJS), 200, headers)


@api.route('/news')
class ViewAllNews(Resource):
    def get(self):
        session = Session()

        linksJS = []
        links = session.query(Link).order_by(desc(Link.created), Link.id).all()
        for link in links:
            linksJS.append(link.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/view_all_links.html', links=linksJS), 200, headers)

@api.route('/literature')
class ViewAllLiterature(Resource):
    def get(self):
        session = Session()

        literatureJS = []
        literatures = session.query(Literature).order_by(desc(Literature.created), Literature.id).all()
        for link in literatures:
            literatureJS.append(link.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/view_all_literature.html', literatures=literatureJS), 200, headers)


@api.route('/other')
class Other(Resource):
    def get(self):
        sectionID = 's1gemu'


        session = Session()

        section = session.query(Section).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(section=sectionID).order_by(desc(SectionPost.created), SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(id=link.post).first()
            if post is not None:
                postsJS.append(post.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/other_information.html', section=sectionJS, posts=postsJS), 200, headers)


@api.route('/categories')
class Categories(Resource):
    def get(self):
        session = Session()

        fixed_categories = ['srxnj8', 's7gmcl', 's9v3pn', 'szlxjv']

        catJS = []
        for cat_id in fixed_categories:
            cat = session.query(Category).filter_by(id=cat_id).first()
            if cat is not None:
                catJS.append(cat.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/provider_select.html', categories=catJS), 200, headers)

@api.route('/categories/<categoryID>')
class ViewCategory(Resource):
    def get(self, categoryID):
        session = Session()

        category = session.query(Category).filter_by(id=categoryID).first()
        categoryJS = category.publicJSON()

        fixed_categories = ['srxnj8', 's7gmcl', 's9v3pn', 'szlxjv']

        catJS = []
        for cat_id in fixed_categories:
            cat = session.query(Category).filter_by(id=cat_id).first()
            if cat is not None:
                catJS.append(cat.publicJSON())

        category_sections = session.query(CategorySection).filter_by(category=categoryID).order_by(desc(CategorySection.created), CategorySection.id).all()
        sectionsJS = []
        for link in category_sections:
            section = session.query(Section).filter_by(id=link.section).first()
            if section is not None:
                sectionsJS.append(section.publicJSON())

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/provider_select.html', categories=catJS, sections=sectionsJS, category=categoryJS), 200, headers)

@api.route('/section/<sectionID>')
class ViewSection(Resource):
    def get(self, sectionID):
        categoryID = request.args.get('categoryID', None)

        session = Session()

        category = session.query(Category).filter_by(id=categoryID).first()
        categoryJS = None
        if category is not None:
            categoryJS = category.publicJSON()

        category_sections = session.query(CategorySection).filter_by(category=categoryID).order_by(desc(CategorySection.created), CategorySection.id).all()
        allsectionsJS = []
        for link in category_sections:
            section = session.query(Section).filter_by(id=link.section).first()
            if section is not None:
                allsectionsJS.append(section.publicJSON())

        section = session.query(Section).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(section=sectionID).order_by(desc(SectionPost.created), SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(id=link.post).first()
            if post is not None:
                postsJS.append(post.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/section.html', section=sectionJS, posts=postsJS, category=categoryJS, sections=allsectionsJS), 200, headers)

@api.route('/literature/<literatureID>')
class ViewLiterature(Resource):
    def get(self, literatureID):
        session = Session()

        lit = session.query(Literature).filter_by(id=literatureID).first()
        if lit is None:
            abort(404)

        litLinks = session.query(LiteratureLink).filter_by(literature=literatureID).all()
        linksJS = []
        for content in litLinks:
            linksJS.append(content.publicJSON())

        litJS = lit.publicJSON()

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/view_literature.html', literature=litJS, links=linksJS), 200, headers)



@api.route('/contact')
class Contact(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/contact.html'), 200, headers)
