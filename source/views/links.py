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

api = APINamespace('Links')

ALLOWED_EXTENSIONS = set(['png', 'jpeg', 'jpg', 'image'])

@api.route('/list')
class ListLinks(Resource):
    @login_required
    def get(self):
        session = Session()

        linksJS = []
        links = session.query(Link).order_by(desc(Link.created), Link.id).all()
        for link in links:
            linksJS.append(link.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/links/admin_panel_links.html', links=linksJS), 200, headers)

@api.route('/view')
class View(Resource):
    @login_required
    def get(self):
        linkID = request.args.get('id')
        session = Session()

        link = session.query(Link).filter_by(id=linkID).first()
        if link is None:
            abort(404)

        linksJS = link.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/links/admin_panel_view_link.html', link=linksJS), 200, headers)

@api.route('/<linkID>/delete')
class DeleteLink(Resource):
    @login_required
    def get(self, linkID):
        session = Session()

        link = session.query(Link).filter_by(id=linkID).first()
        if link is None:
            abort(404)
        session.delete(link)

        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Links_list_links'))


@api.route('/create')
class CreateLink(Resource):
    @login_required
    def post(self):
        linkID = request.args.get('id', None)

        title = ''
        description = ''

        if 'title' in request.form:
            title = request.form['title']
        if 'description' in request.form:
            description = request.form['description']
        url = request.form['url']
        print('here')
        public = False
        if request.form.get('public') != None:
            public = True

        session = Session()

        link = session.query(Link).filter_by(id=linkID).first()
        if link is None:
            link = Link()
        else:
            link.title = title
            link.description = description

        if link.url != url:
            # Do content generation
            link.url = url

            # Fetch website html content
            urlsession = requests.Session()
            retry = Retry(connect=3, backoff_factor=2.0)
            adapter = HTTPAdapter(max_retries=retry)
            urlsession.mount('http://', adapter)
            urlsession.mount('https://', adapter)
            html = urlsession.get(link.url).text

            # Extract title, description, and preview image from meta-tags
            extracted = extraction.Extractor().extract(html, source_url=url)
            
            title = extracted.title or ''
            descrip = extracted.description or ''
            imgurl = extracted.image or ''

            # Fetch image data data and resize for s3
            img_data = requests.get(imgurl).content
            if img_data is None:
                return url
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size

            filename = secure_filename(alphaNumericID())

            imgSize = (1000, 1000)
            originalImage = resizeIOImage(img_data, (width, height))
            resizedImage = resizeIOImage(img_data, imgSize)

            # Upload to s3
            uploadImage(originalImage, "%soriginal" % filename)
            uploadImage(resizedImage, filename)

            original_url = "{}{}original.jpeg".format(S3_LOCATION, filename)
            large_url = "{}{}.jpeg".format(S3_LOCATION, filename)

            # Save website content
            link.title = title
            link.description = descrip
            link.source_url = original_url
            link.large_url = large_url


        link.public = public

        session.add(link)
        session.commit()
        linkID = link.id
        session.close()

        return redirect(url_for('Links_view', id=linkID))

    @login_required
    def get(self):
        linkID = request.args.get('id')
        session = Session()

        link = session.query(Link).filter_by(id=linkID).first()
        if link is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/links/admin_panel_create_link.html', link=Link().blankJSON()), 200, headers)

        linkJS = link.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/links/admin_panel_create_link.html', link=linkJS), 200, headers)


# Image Upload Helpers

def uploadImage(image, name):
    s3 = boto3.client("s3", aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)
    try:
        s3.put_object(Body=image, Bucket=S3_BUCKET, Key='%s.jpeg' % name, ContentType='application/image', ACL='public-read')# ExtraArgs={ 'ContentType': 'application/image', 'ACL': 'public-read' }
    except:
        abort(400, 'Upload Error')

def resizeIOImage(file, size):
    img = Image.open(BytesIO(file))
    if img.mode in ('RGBA', 'LA'):
        background = Image.new(img.mode[:-1], img.size, '#FFF')
        background.paste(img, img.split()[-1])
        img = background

    data = img.thumbnail(size, PIL.Image.ANTIALIAS)
    temp = BytesIO()
    img.save(temp, format="JPEG")
    return temp.getvalue()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def alphaNumericID():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))