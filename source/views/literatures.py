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

from urllib.parse import urlparse
import urllib.parse

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
from ..models.literature import Literature
from ..models.literature_link import LiteratureLink

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Literatures')

ALLOWED_EXTENSIONS = set(['png', 'jpeg', 'jpg', 'image'])

@api.route('/list')
class ListLiteratures(Resource):
    @login_required
    def get(self):
        session = Session()

        litJS = []
        lits = session.query(Literature).order_by(desc(Literature.created), Literature.id).all()
        for lit in lits:
            litJS.append(lit.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/literature/admin_panel_literatures.html', literatures=litJS), 200, headers)

@api.route('/view')
class View(Resource):
    @login_required
    def get(self):
        literatureID = request.args.get('id')
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
        return make_response(render_template('admin/literature/admin_panel_view_literature.html', literature=litJS, links=linksJS), 200, headers)

@api.route('/<literatureID>/delete')
class DeleteLiterature(Resource):
    @login_required
    def get(self, literatureID):
        session = Session()

        lit = session.query(Literature).filter_by(id=literatureID).first()
        if lit is None:
            abort(404)
        session.delete(lit)

        litLinks = session.query(LiteratureLink).filter_by(literature=literatureID).all()
        for content in litLinks:
            session.delete(content)

        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Literatures_list_literatures'))


@api.route('/<literatureID>/<urlID>/url/delete')
class DeleteURL(Resource):
    @login_required
    def get(self, literatureID, urlID):
        session = Session()

        content = session.query(LiteratureLink).filter_by(id=urlID).first()
        if content is not None:
            session.delete(content)

        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Literatures_view', id=literatureID))

@api.route('/<literatureID>/url/add')
class AddURL(Resource):
    @login_required
    def post(self, literatureID):
        contentID = request.args.get('id')

        title = request.form['title']
        url = request.form['url']

        session = Session()

        lit = session.query(Literature).filter_by(id=literatureID).first()
        if lit is None:
            session.close()
            abort(404)

        content = session.query(LiteratureLink).filter_by(id=contentID).first()
        if content is None:
            content = LiteratureLink()
        

        content.literature = literatureID
        content.text = title
        content.url = url

        session.add(content)
        session.commit()
        session.close()

        return redirect(url_for('Literatures_view', id=literatureID))

    @login_required
    def get(self, literatureID):
        contentID = request.args.get('id')
        session = Session()

        lit = session.query(Literature).filter_by(id=literatureID).first()
        if lit is None:
            session.close()
            abort(404)

        content = session.query(LiteratureLink).filter_by(id=contentID).first()
        if content is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/literature/admin_panel_literature_add_link.html', content=LiteratureLink().blankJSON()), 200, headers)

        contentJS = content.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/literature/admin_panel_literature_add_link.html', content=contentJS), 200, headers)




@api.route('/create')
class CreateLiterature(Resource):
    @login_required
    def post(self):
        litID = request.args.get('id', None)


        title = request.form['title']
        description = request.form['description']

        public = False
        if request.form.get('public') != None:
            public = True

        session = Session()

        literature = session.query(Literature).filter_by(id=litID).first()
        if literature is None:
            literature = Literature()

        literature.title = title
        literature.description = description
        literature.public = public

        session.add(literature)
        session.commit()
        litID = literature.id
        session.close()

        return redirect(url_for('Literatures_view', id=litID))

    @login_required
    def get(self):
        litID = request.args.get('id')
        session = Session()

        lit = session.query(Literature).filter_by(id=litID).first()
        if lit is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/literature/admin_panel_create_literature.html', literature=Literature().blankJSON()), 200, headers)

        literatureJS = lit.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/literature/admin_panel_create_literature.html', literature=literatureJS), 200, headers)


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