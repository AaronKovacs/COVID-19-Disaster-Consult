import datetime
import uuid
import os
import json
import requests

from flask import Flask, request, render_template, g, jsonify, Blueprint, redirect, url_for, make_response, Response
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from flask_restplus import Resource, Api, abort, fields
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS,cross_origin

ssl_lify_en = True
try:
    from flask_sslify import SSLify
except:
    ssl_lify_en = False

from sqlalchemy import or_
from sqlalchemy import DateTime
from sqlalchemy import desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta

scheduler_enabled = True
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except:
    scheduler_enabled = False

from flask_login import LoginManager, login_required, login_user, logout_user 

from source.helpers.helpers import BError

from source.configuration.config import PASSWORD_SECRET_KEY

from source.views.posts import api as posts
from source.views.sections import api as sections
from source.views.categories import api as categories
from source.views.links import api as links
from source.views.literatures import api as literatures
from source.views.pages import api as pages
from source.views.api import api as mobileapi

from source.views.authentication import api as authentication

from source.database.database import Session, engine
from source.database.base import Base

from source.models.user import User
from source.models.post import Post
from source.models.section import Section
from source.models.category import Category
from source.models.category_section import CategorySection
from source.models.post_content import PostContent
from source.models.section_post import SectionPost
from source.models.post_image import PostImage
from source.models.link import Link
from source.models.literature import Literature
from source.models.literature_link import LiteratureLink
from source.models.graph_cache import GraphCache
from source.models.activity_track import ActivityTrack

# Create all tables
Base.metadata.create_all(bind=engine)

# Create app
application = Flask(__name__, template_folder='./source/templates', static_folder='./source/static')

if ssl_lify_en:
    sslify = SSLify(application)

login_manager = LoginManager()
login_manager.init_app(application)

application.config['DEBUG'] = True
application.config['SECRET_KEY'] = PASSWORD_SECRET_KEY
application.config['TEMPLATES_AUTO_RELOAD'] = True

def cache_graph():
    print('Fetching Fresh US Graph Data')
    final_js_str = ''
    try:
        url = 'https://api.covid19api.com/country/us/status/confirmed'
        resp = requests.get(url)
        js = resp.json()

        day_dict = {}
        for case in js:
            if case['Cases'] > 0 and case['Status'] == 'confirmed':
                date = case['Date'].split('T')[0]
                fixed_date = '%sT00:00:00Z' % date

                if fixed_date not in day_dict:
                    day_dict[fixed_date] = 0
                day_dict[fixed_date] += case['Cases']

        day_js = []
        for key in day_dict.keys():
            small_js = { 'Date': key, 'Cases': day_dict[key], 'Status': 'confirmed' }
            day_js.append(small_js)
        final_js_str = json.dumps(day_js)
    except:
        print('Failed Fetching US Graph Data')

    session = Session()
    us_graph = session.query(GraphCache).filter_by(country='us', data_type='country').first()
    if us_graph == None:
        us_graph = GraphCache(country='us', data_type='country')
        session.add(us_graph)
    us_graph.json = final_js_str
    session.commit()
    session.close()

def cache_summary():
    print('Fetching Fresh Graph Summary Data')
    final_js_str = ''
    try:
        final_dict = {}
        url = 'https://api.covid19api.com/summary'
        resp = requests.get(url)
        js = resp.json()

        final_dict['Global'] = js['Global']

        country_dict = []
        for case in js["Countries"]:
            country_dict.append({"Country": case['Country'], "Slug": case['Slug'], "TotalConfirmed": case['TotalConfirmed'], "TotalDeaths": case['TotalDeaths'], "TotalRecovered": case['TotalRecovered']})

        final_dict['Countries'] = country_dict
        final_js_str = json.dumps(final_dict)
    except:
        print('Failed Fetching Graph Summary Data')

    session = Session()
    us_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
    if us_graph == None:
        us_graph = GraphCache(country='us', data_type='summary')
        session.add(us_graph)
    us_graph.json = final_js_str
    session.commit()
    session.close()
    
if scheduler_enabled:
    session = Session()
    us_graph = session.query(GraphCache).filter_by(country='us', data_type='country').first()
    if us_graph is None:
        cache_graph()

    summary_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
    if summary_graph is None:
        cache_summary()
    session.close()
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(cache_graph,'interval',minutes=60)
    sched.add_job(cache_summary,'interval',minutes=50)

    sched.start()

@application.route("/")
def redirect_home():
    return redirect(url_for('Pages_home'))


api = Api(application, title='COVID-19 Disaster Consult', version='1.0', doc=False)
api.add_namespace(pages, path='')
api.add_namespace(posts, path='/posts')
api.add_namespace(sections, path='/sections')
api.add_namespace(categories, path='/categories')
api.add_namespace(links, path='/links')
api.add_namespace(literatures, path='/literatures')
api.add_namespace(mobileapi, path='/api/v1')

api.add_namespace(authentication, path='/auth')



@login_manager.user_loader
def load_user(user_id):
    session = Session()
    user = session.query(User).filter_by(id=user_id).first()
    if user is None:
        session.close()
        return None
    session.expunge(user)
    session.close()
    return user


@application.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('Authentication_login'))

@application.route('/register/success')
def registerSuccess():
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('successful_register.html'), 200, headers)


@application.route('/admin')
@login_required
def admin():
    session = Session()
    us_graph = session.query(GraphCache).filter_by(country='us', data_type='country').first()
    us_graphjs = us_graph.last_updated
    summary_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
    summary_graphjs = summary_graph.last_updated


    actsJS = []
    acts = session.query(ActivityTrack).order_by(desc(ActivityTrack.created), ActivityTrack.id).limit(20)
    for act in acts:
        actsJS.append(act.publicJSON())

    session.close()



    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('admin/admin_panel_home.html', usgraph=us_graphjs, summary=summary_graphjs, activities=actsJS), 200, headers)

# Error Pages
@application.errorhandler(401)
def login_failed(e):
    return redirect(url_for('Authentication_login'))

@application.errorhandler(403)
def unauthorized_access(e):
    return Response('<p>Login failed. Unauthorized access. Please contact an administrator to get login privileges.</p>')

@application.errorhandler(410)
def register_failed(e):
    return Response('<p>Register failed</p>')


def render(template):
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template(template), 200, headers)


if __name__ == '__main__':
    application.jinja_env.auto_reload = True
    application.config['TEMPLATES_AUTO_RELOAD'] = True
    application.run(debug=True, host='0.0.0.0')

