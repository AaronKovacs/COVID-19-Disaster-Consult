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
from ..models.site_info import SiteInfo

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Info')

@api.route('/list')
class ListInfo(Resource):
    @login_required
    def get(self, site):
        session = Session()

        js = []
        infos = session.query(SiteInfo).filter_by(site=site).order_by(desc(SiteInfo.last_updated), SiteInfo.id)

        for info in infos:     
            js.append(info.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/info/admin_panel_infos.html', infos=js, site=site), 200, headers)


@api.route('/<infoID>/delete')
class DeleteInfo(Resource):
    @login_required
    def get(self, infoID, site):
        session = Session()

        info = session.query(SiteInfo).filter_by(site=site, id=infoID).first()
        if info is None:
            abort(404)
        session.delete(info)

        session.commit()
        session.close()

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Info_list_info', site=site))


@api.route('/view')
class View(Resource):
    @login_required
    def get(self, site):
        infoID = request.args.get('id')
        session = Session()

        info = session.query(SiteInfo).filter_by(site=site).filter_by(id=infoID).first()
        if info is None:
            abort(404)

        js = info.publicJSON()

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/info/admin_panel_view_info.html', info=js, site=site), 200, headers)

@api.route('/create')
class CreateInfo(Resource):
    @login_required
    def post(self, site):
        infoID = request.args.get('id', None)

        title = request.form['title']

        data_type = request.args.get('data_type', 'text')#request.form['data_type']

        data = ''
        if data_type == 'raw':
            data = request.form['data_raw']
        else:
            data = request.form['data_text']

        content_type = request.form['content_type']


        session = Session()


        info = session.query(SiteInfo).filter_by(site=site).filter_by(id=infoID).first()
        if info is None:
            info = SiteInfo(site=site)
         

        info.title = title
        info.data = data
        info.data_type = data_type
        info.content_type = content_type

        session.add(info)
        session.commit()

        infoID = info.id

        session.close()

        return redirect(url_for('Info_view', id=infoID, site=site))

    @login_required
    def get(self, site):
        infoID = request.args.get('id')
        data_type = request.args.get('data_type')
        session = Session()

        info = session.query(SiteInfo).filter_by(site=site).filter_by(id=infoID).first()
        if info is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/info/admin_panel_create_info.html', info=SiteInfo().blankJSON(), data_type=data_type, site=site), 200, headers)

        infoJS = info.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/info/admin_panel_create_info.html', info=infoJS, data_type=data_type, site=site), 200, headers)

