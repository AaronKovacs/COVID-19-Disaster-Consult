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

from .posts import uploadImage, resizeIOImage, allowed_file, alphaNumericID, ALLOWED_EXTENSIONS

from ..models.user import User
from ..models.post import Post
from ..models.section import Section
from ..models.category import Category
from ..models.category_section import CategorySection
from ..models.post_content import PostContent
from ..models.section_post import SectionPost
from ..models.post_image import PostImage
from ..models.site_url import SiteURL

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('URLs')

@api.route('/list')
class ListUrls(Resource):
    @login_required
    def get(self, site):
        session = Session()

        dict_urls = {}
        urls = session.query(SiteURL).order_by(desc(SiteURL.order), SiteURL.id).all()
        for url in urls:
            if url.section not in dict_urls:
                dict_urls[url.section] = []
            dict_urls[url.section].append(url.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/urls/admin_panel_urls.html', urls=dict_urls, site=site), 200, headers)

    @login_required
    def post(self, site):
        session = Session()

        title = request.form['title']
        url = request.form['url']
        section = request.form['section']

        session.add(SiteURL(site=site, title=title, url=url, section=section))
        session.commit()
        session.close()

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('URLs_list_urls', site=site))

@api.route('/<urlID>/delete')
class DeleteURL(Resource):
    @login_required
    def get(self, urlID, site):
        session = Session()

        url = session.query(SiteURL).filter_by(site=site, id=urlID).first()
        if url is None:
            abort(404)
        session.delete(url)

        session.commit()
        session.close()

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('URLs_list_urls', site=site))

@api.route('/<urlID>/order')
class UpdateURLOrder(Resource):
    @login_required
    def post(self, urlID, site):
        order = request.form['order']
       
        session = Session()

        url = session.query(SiteURL).filter_by(site=site, id=urlID).first()
        if url is None:
            return redirect(url_for('URLs_list_urls', site=site))

        url.order = order
        session.commit()
        session.close()


        return redirect(url_for('URLs_list_urls', site=site))
