import datetime
import uuid
import os
import json

from flask import Flask, request, render_template, g, jsonify, Blueprint, redirect, url_for, make_response, Response
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from flask_restplus import Resource, Api, abort, fields
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS,cross_origin

from sqlalchemy import or_
from sqlalchemy import DateTime
from sqlalchemy import desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta

from flask_login import LoginManager, login_required, login_user, logout_user 

from source.helpers.helpers import BError

from source.configuration.config import PASSWORD_SECRET_KEY

from source.views.posts import api as posts
from source.views.sections import api as sections
from source.views.categories import api as categories
from source.views.links import api as links
from source.views.literatures import api as literatures
from source.views.pages import api as pages

from source.views.authentication import api as authentication

from source.database.database import Session, engine
from source.database.base import Base

from source.models.user import User
from source.models.post import Post
from source.models.section import Section
from source.models.category import Category
from source.models.category_section import CategorySection
from source.models.post_content import PostContent
from source.models.section_post import SectionPost
from source.models.post_image import PostImage
from source.models.link import Link
from source.models.literature import Literature
from source.models.literature_link import LiteratureLink

# Create all tables
Base.metadata.create_all(bind=engine)

# Create app
application = Flask(__name__, template_folder='./source/templates', static_folder='./source/static')

login_manager = LoginManager()
login_manager.init_app(application)

application.config['DEBUG'] = False
application.config['SECRET_KEY'] = PASSWORD_SECRET_KEY

@application.route("/")
def redirect_home():
    return redirect(url_for('Pages_home'))


api = Api(application, title='COVID-19 Disaster Consult', version='1.0', doc=False)
api.add_namespace(pages, path='')
api.add_namespace(posts, path='/posts')
api.add_namespace(sections, path='/sections')
api.add_namespace(categories, path='/categories')
api.add_namespace(links, path='/links')
api.add_namespace(literatures, path='/literatures')

api.add_namespace(authentication, path='/auth')

@login_manager.user_loader
def load_user(user_id):
    session = Session()
    user = session.query(User).filter_by(id=user_id).first()
    if user is None:
        session.close()
        return None
    session.expunge(user)
    session.close()
    return user


@application.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('Authentication_login'))

@application.route('/register/success')
def registerSuccess():
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('successful_register.html'), 200, headers)


@application.route('/admin')
@login_required
def admin():
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('admin_panel.html'), 200, headers)

# Error Pages
@application.errorhandler(401)
def login_failed(e):
    return redirect(url_for('Authentication_login'))

@application.errorhandler(403)
def unauthorized_access(e):
    return Response('<p>Login failed. Unauthorized access. Please contact an administrator to get login privileges.</p>')

@application.errorhandler(410)
def register_failed(e):
    return Response('<p>Register failed</p>')


def render(template):
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template(template), 200, headers)
