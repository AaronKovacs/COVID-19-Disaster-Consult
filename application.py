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
from flask_paginate import Pagination, get_page_args

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

from source.configuration.config import PASSWORD_SECRET_KEY, ENV_NAME

from source.views.posts import api as posts
from source.views.sections import api as sections
from source.views.categories import api as categories
from source.views.links import api as links
from source.views.literatures import api as literatures
from source.views.pages import api as pages
from source.views.api import api as mobileapi
from source.views.drafts import api as drafts
from source.views.users import api as users

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
from source.models.feedback import Feedback
from source.models.draft import Draft
from source.models.site import Site
from source.models.user_profile import UserProfile

# Create all tables
Base.metadata.create_all(bind=engine)

# Create app
application = Flask(__name__, template_folder='./source/templates', static_folder='./source/static')

if ssl_lify_en and ENV_NAME() == 'prod':
    print("Using SSL")
    sslify = SSLify(application)

login_manager = LoginManager()
login_manager.init_app(application)

application.config['DEBUG'] = True
application.config['SECRET_KEY'] = PASSWORD_SECRET_KEY
application.config['TEMPLATES_AUTO_RELOAD'] = True
application.config['JSONIFY_PRETTYPRINT_REGULAR'] = False


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
    if final_js_str != '' and final_js_str != None:
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
            if case['Slug'] == 'united-states' and case['TotalDeaths'] == 0:
                return
            country_dict.append({"Country": case['Country'], "Slug": case['Slug'], "TotalConfirmed": case['TotalConfirmed'], "TotalDeaths": case['TotalDeaths'], "TotalRecovered": case['TotalRecovered']})

        final_dict['Countries'] = country_dict
        final_js_str = json.dumps(final_dict)
    except:
        print('Failed Fetching Graph Summary Data')
        return

    session = Session()
    us_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
    if us_graph == None:
        us_graph = GraphCache(country='us', data_type='summary')
        session.add(us_graph)
    if final_js_str != '' and final_js_str != None:
        us_graph.json = final_js_str
    session.commit()
    session.close()
    
if scheduler_enabled:
    session = Session()
    #us_graph = session.query(GraphCache).filter_by(country='us', data_type='country').first()
    #if us_graph is None:
    #    cache_graph()

    summary_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
    if summary_graph is None:
        cache_summary()
    session.close()
    sched = BackgroundScheduler(daemon=True)
    #sched.add_job(cache_graph,'interval',minutes=60)
    sched.add_job(cache_summary,'interval',minutes=10)

    sched.start()

@application.route("/")
def redirect_homoe():
    session = Session()

    sites = session.query(Site).filter_by(public=True).count()
    session.close()
    page = 'Pages_home'
    if sites > 1:
        page = 'select_screen'

    if ENV_NAME() == 'prod':
        return redirect(url_for(page, _scheme='https', _external=True, site='covid-19'))
    else:
        return redirect(url_for(page, site='covid-19'))

@application.route("/select")
def select_screen():
    session = Session()

    sites = session.query(Site).filter_by(public=True).order_by(Site.order, Site.id).all()

    if len(sites) == 1:
        if ENV_NAME() == 'prod':
            return redirect(url_for('Pages_home', _scheme='https', _external=True, site='covid-19'))
        else:
            return redirect(url_for('Pages_home', site='covid-19'))
        
    sitesJS = []
    for site in sites:
        sitesJS.append(site.publicJSON())

 
    session.close()
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('pages/select-disaster.html', sites=sites, site='covid-19'), 200, headers)

    '''
    if ENV_NAME() == 'prod':
        return redirect(url_for('Pages_home', _scheme='https', _external=True, site='covid-19'))
    else:
        return redirect(url_for('Pages_home', site='covid-19'))
    '''


@application.errorhandler(404) 
def not_found(e): 
    sites = session.query(Site).filter_by(public=True)
    return render_template("error/404.html", sites=sites) 


api = Api(application, title='COVID-19 Disaster Consult', version='1.0', doc=False)
api.add_namespace(pages, path='/<site>')
api.add_namespace(posts, path='/<site>/posts')
api.add_namespace(sections, path='/<site>/sections')
api.add_namespace(categories, path='/<site>/categories')
api.add_namespace(links, path='/<site>/links')
api.add_namespace(literatures, path='/<site>/literatures')
api.add_namespace(drafts, path='/<site>/drafts')
api.add_namespace(users, path='/<site>/users')

api.add_namespace(mobileapi, path='/<site>/api/v1')

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
def admin_redirect():
    if ENV_NAME() == 'prod':
        return redirect(url_for('admin_select', _scheme='https', _external=True, site='covid-19'))
    else:
        return redirect(url_for('admin_select', site='covid-19'))

@application.route('/<site>/admin')
@login_required
def admin(site):
    session = Session()
    us_graph = session.query(GraphCache).filter_by(country='us', data_type='country').first()
    us_graphjs = us_graph.last_updated
    summary_graph = session.query(GraphCache).filter_by(country='us', data_type='summary').first()
    summary_graphjs = summary_graph.last_updated


    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
        
    actsJS = []
    acts = session.query(ActivityTrack).filter_by(site=site).order_by(desc(ActivityTrack.created), ActivityTrack.id).limit(per_page).offset(offset)
    for act in acts:
        actsJS.append(act.publicJSON(site))


    pagination = Pagination(page=page, per_page=per_page, total=session.query(ActivityTrack).filter_by(site=site).count(), css_framework='bootstrap4')

    session.close()


    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('admin/admin_panel_home.html', usgraph=us_graphjs, summary=summary_graphjs, activities=actsJS, pagination=pagination, site=site), 200, headers)


@application.route('/admin/select')
@login_required
def admin_select():
    session = Session()

    sites = session.query(Site).order_by(Site.order, Site.id).all()
        
    sitesJS = []
    for site in sites:
        sitesJS.append(site.publicJSON())

 
    session.close()


    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('admin/admin_panel_disaster_type.html', sites=sitesJS), 200, headers)


@api.route('/api/v1/sites')
class SitesGet(Resource):
    def get(self):
    
        session = Session()

        sitesJS = []
        sites = session.query(Site).filter_by(public=True).all()

        for site in sites:
            js = site.publicJSON()
            js['has_literature'] = site.hasLiterature(session)
            sitesJS.append(js)

        session.close()

        return jsonify({'sites': sitesJS})

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
'''
@application.before_request
def before_request():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)
'''
def render(template):
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template(template), 200, headers)


if __name__ == '__main__':
    application.jinja_env.auto_reload = True
    application.config['TEMPLATES_AUTO_RELOAD'] = True
    application.run(debug=False, host='0.0.0.0')
    application.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

