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
from ..models.issue import Issue
from ..models.issue_content import IssueContent

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Issues')

@api.route('/list')
class ListIssue(Resource):
    @login_required
    def get(self, site):
        session = Session()

        js = []
        infos = session.query(Issue).filter_by(site=site).order_by(desc(Issue.last_updated), Issue.id)

        for info in infos:     
            js.append(info.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/issues/admin_panel_issues.html', issues=js, site=site), 200, headers)


@api.route('/<contentID>/delete')
class DeleteIssueContent(Resource):
    @login_required
    def get(self, contentID, site):
        session = Session()

        info = session.query(IssueContent).filter_by(site=site, id=contentID).first()
        if info is None:
            abort(404)

        issue = info.issue
        session.delete(info)

        session.commit()
        session.close()

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Issues_view', site=site, id=issue))


@api.route('/view')
class View(Resource):
    @login_required
    def get(self, site):
        infoID = request.args.get('id')
        session = Session()

        info = session.query(Issue).filter_by(site=site).filter_by(id=infoID).first()
        if info is None:
            abort(404)

        js = info.publicJSON()

        contents = session.query(IssueContent).filter_by(site=site, issue=infoID).order_by(IssueContent.order, IssueContent.id).all()
        contentsJS = []
        for content in contents:
            contentsJS.append(content.publicJSON())

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/issues/admin_panel_view_issue.html', issue=js, contents=contentsJS, site=site), 200, headers)

@api.route('/create')
class CreateIssue(Resource):
    @login_required
    def post(self, site):
        issueID = request.args.get('id', None)
        title = request.form['title']
        subtitle = request.form['subtitle']
        archived = False
        if request.form.get('public') != None:
            archived = True

        session = Session()


        issue = session.query(Issue).filter_by(site=site).filter_by(id=issueID).first()
        if issue is None:
            issue = Issue(site=site)
         

        issue.title = title
        issue.subtitle = subtitle
        issue.archived = archived

        session.add(issue)
        session.commit()

        issueID = issue.id

        session.close()

        return redirect(url_for('Issues_view', id=issueID, site=site))

    @login_required
    def get(self, site):
        infoID = request.args.get('id')
        session = Session()

        info = session.query(Issue).filter_by(site=site).filter_by(id=infoID).first()
        if info is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/issues/admin_panel_view_issue.html', issue=Issue().blankJSON(), site=site), 200, headers)


        contents = session.query(IssueContent).filter_by(site=site, issue=infoID).order_by(IssueContent.order, IssueContent.id).all()
        contentsJS = []
        for content in contents:
            contentsJS.append(content.publicJSON())

        infoJS = info.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/issues/admin_panel_view_issue.html', issue=infoJS, contents=contentsJS, site=site), 200, headers)

@api.route('/add')
class AddSection(Resource):
    @login_required
    def post(self, site):
        issueID = request.args.get('issueID', None)
        contentID = request.args.get('contentID', None)

        title = request.form['title']
        data = request.form['data']
        order = request.form['order']

        session = Session()


        info = session.query(IssueContent).filter_by(site=site).filter_by(issue=issueID, id=contentID).first()
        if info is None:
            info = IssueContent(site=site, issue=issueID)
         

        info.title = title
        info.data = data
        info.order = order
        session.add(info)
        session.commit()

        infoID = info.id

        session.close()

        return redirect(url_for('Issues_view', id=issueID, site=site))
