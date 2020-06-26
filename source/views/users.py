import json
import uuid
import os
import threading
import requests
import datetime
import PIL
import copy
import boto3
import botocore
import io
import extraction

from urllib.parse import urlparse
import urllib.parse

from urllib.request import Request, urlopen
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask import send_from_directory

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

from ..configuration.config import S3_BUCKET, S3_KEY, S3_SECRET, S3_LOCATION

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

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Users')

@api.route('/list')
class ListUsers(Resource):
    @login_required
    def get(self, site):
        session = Session()

        usersJS = []
        users = session.query(User).order_by(desc(User.last_updated), User.id).all()
        for user in users:
            usersJS.append(user.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/users/admin_panel_users.html', users=usersJS, site=site), 200, headers)

@api.route('/view')
class View(Resource):
    @login_required
    def get(self, site):
        userID = request.args.get('id')
        session = Session()

        user = session.query(User).filter_by(id=userID).first()
        if user is None:
            abort(404)

        userJS = user.publicJSON()
        profileJS = user.profile(session).publicJSON()

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/users/admin_panel_view_user.html', user=userJS, profile=profileJS, site=site), 200, headers)

@api.route('/create')
class CreateUser(Resource):
    @login_required
    def post(self, site):
        userID = request.args.get('id', None)


        realname = request.form['realname']
        username = request.form['username']
        email = request.form['email']
        privilege = request.form['privilege']

        title = request.form['title']
        website = request.form['website']
        section = request.form['section']
        order = request.form['order']
        content = request.form['content']

        session = Session()

        user = session.query(User).filter_by(id=userID).first()
       
        user.realname = realname
        user.username = cleanUsername(username)
        user.email = email
        user.privilege = privilege

        profile = user.profile(session)

        profile.title = title
        profile.website = website
        profile.section = section
        profile.order = order
        profile.content = content


        session.commit()

        session.close()

        return redirect(url_for('Users_view', id=userID, site=site))

    @login_required
    def get(self, site):
        userID = request.args.get('id')
        session = Session()

        user = session.query(User).filter_by(id=userID).first()

        userJS = user.publicJSON()
        profileJS = user.profile(session).publicJSON()

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/users/admin_panel_create_user.html', user=userJS, profile=profileJS, site=site), 200, headers)

def cleanUsername(username):
    cleaned_string = ''
    available_chars = 'abcdefghijklmnopqrstuvwxyz1234567890_'

    for character in username.lower():
        if character in available_chars:
            cleaned_string += character

    return cleaned_string[0:20]