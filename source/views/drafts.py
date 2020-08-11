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

from flask_login import current_user

from urllib.request import Request, urlopen
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from flask import Flask, request, render_template, g, jsonify, Blueprint, current_app, make_response, send_from_directory
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, HTTPAuth
from flask_restplus import Resource, Api, abort, Namespace
from flask import redirect, render_template, url_for
from flask_mail import Mail, Message
from flask_login import login_required, login_user, logout_user 
from flask_paginate import Pagination, get_page_args

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

@api.route('/list')
class ListDrafts(Resource):
    @login_required
    def get(self, site):
        session = Session()

        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')

        draftsJS = []
        drafts = session.query(Draft).filter_by(approved=False, rejected=False).order_by(desc(Draft.created), Draft.id).limit(per_page).offset(offset)

        post_ids = []
        for draft in drafts:
            if draft.object_id in post_ids:
                continue
            post_ids.append(draft.object_id)
            js = draft.publicJSON()
            js['user'] = draft.user(session)
            js['routes'] = draft.routeText(session)
            js['site'] = draft.site(session)
            draftsJS.append(js)

        session.close()

        pagination = Pagination(page=page, per_page=per_page, total=session.query(Draft).filter_by(approved=False, rejected=False).count(), css_framework='bootstrap4')

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_drafts.html', drafts=draftsJS, site=site, pagination=pagination), 200, headers)


@api.route('/draft/<draftID>')
class ViewDraft(Resource):
    @login_required
    def get(self, draftID, site):
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

        activityJS = activity.publicJSON(site)

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_view_draft.html', draft=draftJS, activity=activityJS, site=site), 200, headers)

@api.route('/draft/<draftID>/approve')
class ApproveDraft(Resource):
    @login_required
    def post(self, draftID, site):
        session = Session()

        comment = request.form['content']

        decision = ''
        if 'approvebutton' in request.form:
            decision = 'approved'
        if 'rejectbutton' in request.form:
            decision = 'rejected'

        draft = session.query(Draft).filter_by(id=draftID).first()
        
        if draft is None:
            abort(404) 
        
        draftJS = draft.publicJSON()

        activity = session.query(ActivityTrack).filter_by(draft=draftID).first()

        if activity is None:
            abort(404)

        activityJS = activity.publicJSON(site)


        if decision == 'approved':
            draft.approved = True
            draft.rejected = False

            older_drafts = session.query(Draft).filter_by(object_id=draft.object_id).filter(Draft.created < draft.created).all()
            for d in older_drafts:
                dJS = d.publicJSON()
                a = session.query(ActivityTrack).filter_by(draft=dJS['id']).first()
                aJS = a.publicJSON(site)
                # Send other users who made unapproved drafts updates as well
                if a and not d.approved and aJS['user']['id'] != activityJS['user']['id']:   
                    slack_msg = "Hello, there are new updated content added to your draft!\n*Post Title*: {}\n*Final Draft Decision*: {}\n*Draft Comments*:```{}```\n*Post Link*: {}"
                    slack_msg = slack_msg.format(dJS['new_content']['title'], decision.title(), comment,request.host + aJS["url"])
                    send_slack_message_to_user(aJS['user']['id'], slack_msg)

                d.approved = True
        else:
            draft.rejected = True
            draft.approved = False

        draft.comment = '%s \nReviewed by %s' % (comment, current_user.realname)
        session.commit()



        slack_msg = "Hello, there has been an update to a draft you submitted!\n*Post Title*: {}\n*Draft Decision*: {}\n*Draft Comments*:```{}```\n*Post Link*: {}"
        slack_msg = slack_msg.format(draftJS['new_content']['title'], decision.title(), comment,request.host + activityJS["url"])
        send_slack_message_to_user(activityJS['user']['id'], slack_msg)

        session.close()

        return redirect(url_for('Drafts_view_draft', draftID=draftID, site=site))
