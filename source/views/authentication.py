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

api = APINamespace('Authentication', description='Registering and authenticating.')#Api(blueprint)

@api.route('/register')
class Register(Resource):
    def post(self):
        username = request.form['username']
        password = request.form['password']
        realname = request.form['realname']
        email = request.form['email']

        session = Session()

        user = session.query(User).filter_by(username=username.lower()).first()
        if user is not None:
            session.close()
            return redirect(url_for('Authentication_register', alert='Error: User with that username already exists.'))
        user = session.query(User).filter_by(email=email).first()
        if user is not None:
            session.close()
            return redirect(url_for('Authentication_register', alert='Error: User with that email already exists.'))

        user = User(username=username.lower(), realname=realname, email=email)
        user.hash_password(password)
        session.add(user)
        session.commit()
        session.close()
        return redirect(url_for('registerSuccess'))
        
    def get(self):
        alert = request.args.get('alert', None)
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('register.html', alert=alert), 200, headers)

@api.route('/login')
class Login(Resource):
    def post(self):
        session = Session()
        username = request.form['username']
        password = request.form['password']
        user = session.query(User).filter_by(username=username.lower()).first()
        if user is None:
            session.close()
            return redirect(url_for('Authentication_login', alert='Error: User does not exist.'))


        if user.verify_password(password):
            if user.privilege == 0:
                return abort(403)
            session.expunge(user)
            login_user(user)
            session.close()
            return redirect(url_for('admin_select'))
        
    def get(self):
        alert = request.args.get('alert', None)
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('login.html', alert=alert), 200, headers)
