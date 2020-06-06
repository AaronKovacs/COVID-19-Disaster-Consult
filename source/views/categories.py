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

api = APINamespace('Categories')

@api.route('/<categoryID>/add/sections')
class AddSectionCategoryViewSections(Resource):
    @login_required
    def get(self, categoryID, site):
        session = Session()

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        categoryJS = category.publicJSON()

        sectionsJS = []
        sections = session.query(Section).filter_by(site=site).order_by(desc(Section.created), Section.id).all()
        for section in sections:
            sectionsJS.append(section.publicJSON())

        session.close()


        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/categories/admin_panel_category_add_sections.html', sections=sectionsJS, category=categoryJS, site=site), 200, headers)

@api.route('/<categoryID>/add/<sectionID>')
class AddSectionCategory(Resource):
    @login_required
    def get(self, categoryID, sectionID, site):
        session = Session()

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()

        if category == None:
            abort(404)

        section = session.query(Section).filter_by(site=site).filter_by(id=sectionID).first()

        if section == None:
            abort(404)

        sectioncategory = session.query(CategorySection).filter_by(site=site).filter_by(category=categoryID, section=sectionID).first()
        if sectioncategory is None:
            sectioncategory = CategorySection(site=site)

        sectioncategory.category = categoryID
        sectioncategory.section = sectionID

        session.add(sectioncategory)
        session.commit()
        session.close()

        track_activity('Added section to category', categoryID, 'category', site)
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Categories_view_category', id=categoryID, site=site))

@api.route('/<categoryID>/delete')
class DeleteCategory(Resource):
    @login_required
    def get(self, categoryID, site):
        session = Session()

        section = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        if section is None:
            abort(404)
        session.delete(section)

        post_links = session.query(CategorySection).filter_by(site=site).filter_by(category=categoryID).all()
        for content in post_links:
            session.delete(content)

        session.commit()
        session.close()

        track_activity('Deleted category', categoryID, 'category', site)
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Categories_list_categories', site=site))

@api.route('/<categoryID>/<sectionID>/section/delete')
class DeleteSection(Resource):
    @login_required
    def get(self, categoryID, sectionID, site):
        session = Session()

        link = session.query(CategorySection).filter_by(site=site).filter_by(category=categoryID, section=sectionID).first()
        if link is not None:
            session.delete(link)

        session.commit()
        session.close()

        track_activity('Deleted section from category', categoryID, 'category', site)
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Categories_view_category', id=categoryID, site=site))

@api.route('/list')
class ListCategories(Resource):
    @login_required
    def get(self, site):
        session = Session()

        categoriesJS = []
        categories = session.query(Category).filter_by(site=site).order_by(desc(Category.last_updated), Category.id).all()
        for category in categories:
            categoriesJS.append(category.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/categories/admin_panel_categories.html', categories=categoriesJS, site=site), 200, headers)

@api.route('/view')
class ViewCategory(Resource):
    @login_required
    def get(self, site):
        categoryID = request.args.get('id')
        session = Session()

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        if category is None:
            abort(404)

        category_sections = session.query(CategorySection).filter_by(site=site).filter_by(category=categoryID).order_by(CategorySection.order, CategorySection.id).all()
        sectionsJS = []
        for link in category_sections:
            section = session.query(Section).filter_by(site=site).filter_by(id=link.section).first()
            if section is not None:
                js = section.publicJSON()
                js['order'] = link.order
                sectionsJS.append(js)

        categoryJS = category.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/categories/admin_panel_view_category.html', category=categoryJS, sections=sectionsJS, site=site), 200, headers)

@api.route('/<categoryID>/<sectionID>/order')
class UpdateCategoryOrder(Resource):
    @login_required
    def post(self, categoryID, sectionID, site):
        order = request.form['order']
       
        session = Session()

        category_section = session.query(CategorySection).filter_by(site=site).filter_by(section=sectionID, category=categoryID).first()
        if category_section is None:
            return redirect(url_for('Categories_view_category', id=categoryID))
        category_section.order = order
        session.commit()
        session.close()

        track_activity('Updated order of sections in category', categoryID, 'category', site)
        return redirect(url_for('Categories_view_category', id=categoryID, site=site))



@api.route('/create')
class CreateCategory(Resource):
    @login_required
    def post(self, site):
        categoryID = request.args.get('id', None)


        title = request.form['title']
        content = request.form['content']
        public = False
        if request.form.get('public') != None:
            public = True

        session = Session()

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        if category is None:
            category = Category(site=site)

        category.title = title
        category.description = content
        category.public = public

        session.add(category)
        session.commit()
        categoryID = category.id
        session.close()

        track_activity('Updated category', categoryID, 'category', site)

        return redirect(url_for('Categories_view_category', id=categoryID, site=site))

    @login_required
    def get(self, site):
        categoryID = request.args.get('id')
        session = Session()

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        if category is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/categories/admin_panel_create_category.html', category=Section().blankJSON(), site=site), 200, headers)

        categoryJS = category.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/categories/admin_panel_create_category.html', category=categoryJS, site=site), 200, headers)

