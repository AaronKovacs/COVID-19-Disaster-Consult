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

from flask import Flask, request, render_template, g, jsonify, Blueprint, current_app, make_response, send_from_directory
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
from ..models.feedback import Feedback
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
            if link.public:
                linksJS.append(link.publicJSON())

        litJS = []
        lits = session.query(Literature).order_by(desc(Literature.created), Literature.id).limit(3)
        for lit in lits:
            if lit.public:
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
            if link.public:
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
            if link.public:
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
                if post.public:
                    postsJS.append(post.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/other_information.html', section=sectionJS, posts=postsJS), 200, headers)


@api.route('/categories')
class Categories(Resource):
    def get(self):
        session = Session()

        fixed_categories = ['srxnj8', 's7gmcl', 's7qekp', 's9v3pn', 'szlxjv']

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

        fixed_categories = ['srxnj8', 's7gmcl', 's7qekp', 's9v3pn', 'szlxjv']

        catJS = []
        for cat_id in fixed_categories:
            cat = session.query(Category).filter_by(id=cat_id).first()
            if cat is not None:
                catJS.append(cat.publicJSON())

        category_sections = session.query(CategorySection).filter_by(category=categoryID).order_by(CategorySection.order, CategorySection.id).all()
        sectionsJS = []
        for link in category_sections:
            section = session.query(Section).filter_by(id=link.section).first()
            if section is not None:
                if section.public:
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


        table_of_contents = []
        all_categories = session.query(Category).all()
        for cat in all_categories:
            use_sections = []

            category_sections = session.query(CategorySection).filter_by(category=cat.id).order_by(CategorySection.order, CategorySection.id).all()
            for link in category_sections:
                section = session.query(Section).filter_by(id=link.section).first()
                if section is not None:
                    if section.public:
                        use_sections.append({ 'name': section.title, 'id': section.id })

            table_of_contents.append({ 'name': cat.title, 'id': cat.id, 'sections': use_sections })




        section = session.query(Section).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(section=sectionID).order_by(SectionPost.order, SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(id=link.post).first()
            if post is not None:
                if post.public:
                    postsJS.append(post.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/section.html', section=sectionJS, posts=postsJS, category=categoryJS, table_contents=table_of_contents), 200, headers)

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

@api.route('/privacy')
class Privacy(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/privacy.html'), 200, headers)

@api.route('/medical')
class Medical(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/medical.html'), 200, headers)

@api.route('/tos')
class TOS(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/tos.html'), 200, headers)

@api.route('/cookies')
class Cookies(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/cookies.html'), 200, headers)
    
@api.route('/sponsor')
class Sponsor(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/sponsor.html'), 200, headers)

@api.route('/aboutus')
class Aboutus(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/about_us.html'), 200, headers)


@api.route('/feedback')
class SubmitFeedback(Resource):
    def post(self):
        email = request.form.get('email', '')
        feedback = request.form['feedback']
        ftype = request.args.get('ftype')

        session = Session()
        session.add(Feedback(email=email, text=feedback, ftype=ftype))

        session.commit()
        session.close()

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Pages_submit_feedback'))#make_response(render_template('pages/success_feedback.html'), 200, headers)

    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('pages/success_feedback.html'), 200, headers)       


# Mark file expose
@api.route('/loaderio-be2727d05bae7704d76a1b78f85fa5bb.txt')
class LoaderIO(Resource):
    def get(self):
        return send_from_directory('./source/static', filename='loaderio-be2727d05bae7704d76a1b78f85fa5bb.txt')
