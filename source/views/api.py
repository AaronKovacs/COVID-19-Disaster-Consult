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

from sqlakeyset import get_page, serialize_bookmark, unserialize_bookmark

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
from ..models.graph_cache import GraphCache
from ..models.site import Site

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('API')

@api.route('/')
class SiteGet(Resource):
    def get(self, site):
        session = Session()

        site = session.query(Site).filter_by(slug=site).first()
        siteJS = site.publicJSON()

        session.close()

        return jsonify({'site': siteJS})


        

@api.route('/links')
class LinksGet(Resource):
    def get(self, site):
        page = request.args.get('page')
        currentPage = ''
        if page is not None and page != '':
            currentPage = urllib.parse.unquote(page)


        session = Session()

        linksJS = []
        links = get_page(session.query(Link).filter_by(site=site).filter_by(public=True).order_by(desc(Link.created), Link.id), per_page=5, page=currentPage)
        next_page = links.paging.bookmark_next
        if links.paging.has_next == False:
            next_page = ""

        for link in links:
            linksJS.append(link.publicJSON())

        session.close()

        return jsonify({'links': linksJS, 'page': next_page})


        

@api.route('/contents')
class TableOfContents(Resource):
    def get(self, site):
        session = Session()

        table_of_contents = []
        all_categories = session.query(Category).filter_by(site=site).all()
        for cat in all_categories:
            use_sections = []

            category_sections = session.query(CategorySection).filter_by(site=site).filter_by(category=cat.id).order_by(CategorySection.order, CategorySection.id).all()
            for link in category_sections:
                section = session.query(Section).filter_by(site=site).filter_by(id=link.section).first()
                if section is not None:
                    if section.public:
                        use_sections.append({ 'name': section.title, 'id': section.id })

            table_of_contents.append({ 'name': cat.title, 'id': cat.id, 'sections': use_sections })

        session.close()

        return jsonify({'table_of_contents': table_of_contents})

@api.route('/literature')
class LiteratureGet(Resource):
    def get(self, site):
        page = request.args.get('page')
        currentPage = ''
        if page is not None and page != '':
            currentPage = urllib.parse.unquote(page)

        session = Session()

        litJS = []
        lits = get_page(session.query(Literature).filter_by(site=site).filter_by(public=True).order_by(desc(Literature.created), Literature.id), per_page=5, page=currentPage)
        next_page = lits.paging.bookmark_next
        if lits.paging.has_next == False:
            next_page = ""

        for lit in lits:
            litJS.append(lit.publicJSON())

        session.close()

        return jsonify({'literature': litJS, 'page': next_page})

@api.route('/other')
class Other(Resource):
    def get(self, site):
        sectionID = 's1gemu'

        session = Session()

        section = session.query(Section).filter_by(site=site).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(site=site).filter_by(section=sectionID).order_by(desc(SectionPost.created), SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(site=site).filter_by(id=link.post).first()
            if post is not None and post.public == False:
                postsJS.append(post.publicJSON())

        session.close()

        return jsonify({ 'section': sectionJS, 'posts': postsJS })


@api.route('/provider/categories')
class ProviderCategories(Resource):
    def get(self, site):
        session = Session()

        catJS = []
        for cat in session.query(Category).filter_by(special_type='resource').filter_by(site=site).order_by(Category.order, Category.id).all():
            catJS.append(cat.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return jsonify({'categories': catJS})

@api.route('/categories/<categoryID>')
class ViewCategory(Resource):
    def get(self, categoryID, site):
        session = Session()

        category_sections = session.query(CategorySection).filter_by(site=site).filter_by(category=categoryID).order_by(CategorySection.order, CategorySection.id).all()
        sectionsJS = []
        for link in category_sections:
            section = session.query(Section).filter_by(site=site).filter_by(id=link.section).first()
            if section is not None and section.public is True:
                sectionsJS.append(section.publicJSON())

        session.close()
        return jsonify({'sections': sectionsJS})

@api.route('/section/<sectionID>')
class ViewSection(Resource):
    def get(self, sectionID, site):

        session = Session()

        section = session.query(Section).filter_by(site=site).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(site=site).filter_by(section=sectionID).order_by(SectionPost.order, SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(site=site).filter_by(id=link.post).first()
            if post is not None and post.public is True:
                postsJS.append(post.publicJSON())

        session.close()

        return jsonify({'posts': postsJS})

@api.route('/literature/<literatureID>')
class ViewLiterature(Resource):
    def get(self, literatureID, site):
        session = Session()

        lit = session.query(Literature).filter_by(site=site).filter_by(public=True).filter_by(id=literatureID).first()
        if lit is None:
            abort(404)

        litJS = lit.publicJSON()

        litLinks = session.query(LiteratureLink).filter_by(site=site).filter_by(literature=literatureID).all()
        linksJS = []
        for content in litLinks:
            linksJS.append(content.publicJSON())


        session.close()

        return jsonify({'literature': litJS, 'links': linksJS})

@api.route('/download')
class Download(Resource):
    def get(self, site):
        session = Session()

        js = {}

        js['site'] = session.query(Site).filter_by(slug=site, public=True).first().publicJSON()

        js['categories'] = []
        for obj in session.query(Category).filter_by(site=site, public=True).all():
            js['categories'].append(obj.publicJSON())

        js['sections'] = []
        for obj in session.query(Section).filter_by(site=site, public=True).all():
            js['sections'].append(obj.publicJSON())

        js['posts'] = []
        for obj in session.query(Post).filter_by(site=site, public=True).all():
            js['posts'].append(obj.publicJSON())


        session.close()
        return jsonify(js)



@api.route('/us/graph')
class USGraphData(Resource):
    def get(self, site):
        session = Session()
        us_graph = session.query(GraphCache).filter_by(country='us', data_type='country').first()
        if us_graph is None:
            abort(404)
        js = json.loads(us_graph.json)
        session.close()
        return jsonify(js)


@api.route('/graph/summary')
class GraphSummaryData(Resource):
    def get(self, site):
        session = Session()
        us_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
        if us_graph is None:
            abort(404)
        js = json.loads(us_graph.json)
        session.close()
        return jsonify(js)