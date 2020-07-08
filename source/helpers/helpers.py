import json
import datetime
import uuid
import os
import threading
import requests
import random
import string

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from flask_login import current_user

from ..database.database import Session


from flask import Flask, request, render_template, g, jsonify, Blueprint
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from sqlalchemy import or_
from sqlalchemy import DateTime

from flask_restplus import Resource, Api, abort, Namespace

from flask import render_template, make_response

from ..models.activity_track import ActivityTrack
from ..models.draft import Draft
from ..models.site_info import SiteInfo

def get_site_info(info_keys, site, session):
    data = {}
    for key in info_keys:
        result = session.query(SiteInfo).filter_by(site=site, content_type=key).first()
        if result is None:
            data[key] = ''
        else:
            data[key] = result.data
    return data


def track_activity(text, object_id, object_type, draft=None, site='covid-19'):
    session = Session()
    session.add(ActivityTrack(text=text, object_id=object_id, object_type=object_type, user_id=current_user.id, draft=draft, site=site))
    session.commit()
    session.close()

def save_draft(old_json, new_json, object_id, object_type):
    session = Session()
    draft = Draft(object_id=object_id, object_type=object_type, old_content=json.dumps(old_json), new_content=json.dumps(new_json))
    session.add(draft)
    session.commit()
    session.refresh(draft)
    draft_id = draft.id
    session.close()
    return draft_id

def success():
    return jsonify({ 'status_code': 200})

class BError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

def alphaNumericID():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

def dateNow():
    return datetime.datetime.utcnow

def list_json(rows):
    if rows is None:
        abort(400, 'Error: Data not found.')
    else:
        rowJS = []
        for row in rows:
            rowJS.append(row.publicJSON())
        return rowJS

def post_to_slack(msg):
    wekbook_url = 'https://hooks.slack.com/services/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'

    data = {
        'text': msg,
        'username': 'Website Bot',
        'icon_emoji': ':robot_face:'
    }

    response = requests.post(wekbook_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
