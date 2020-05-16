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
from ..models.feedback import Feedback
from ..models.draft import Draft
from ..models.activity_track import ActivityTrack

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Drafts')#Api(blueprint)

@api.route('/draft/<draftID>')
class ViewDraft(Resource):
    @login_required
    def get(self, draftID):
        session = Session()

        draftJS = None
        draft = session.query(Draft).filter_by(id=draftID).first()

        if draft is None:
            abort(404)

        draftJS = draft.publicJSON()

        activityJS = None
        activity = session.query(ActivityTrack).filter_by(draft=draftID).first()

        if activity is None:
            abort(404)

        activityJS = activity.publicJSON()

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_view_draft.html', draft=draftJS, activity=activityJS), 200, headers)
