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
from ..helpers.helpers import BError, get_site_info, post_to_slack, send_slack_message_to_user, get_slack_users, render_page
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
from ..models.site import Site
from ..models.site_url import SiteURL
from ..models.site_info import SiteInfo
from ..models.user_profile import UserProfile
from ..models.issue import Issue
from ..models.issue_content import IssueContent

from itsdangerous import URLSafeTimedSerializer

# from flask_wtf import Form, RecaptchaField
from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Pages')#Api(blueprint)

@api.route('/home')
class Home(Resource):
    def get(self, site):
        issue_id = request.args.get('issueID', None)
        # Create connection to database
        session = Session()
        sites = session.query(Site).filter_by(public=True)
        private_sites = session.query(Site).filter_by(public=False)


        table_of_contents = []
        all_categories = session.query(Category).filter_by(site=site, public=True).all()
        for cat in all_categories:
            use_sections = []

            category_sections = session.query(CategorySection).filter_by(site=site).filter_by(category=cat.id).order_by(CategorySection.order, CategorySection.id).all()
            for link in category_sections:
                section = session.query(Section).filter_by(site=site, public=True).filter_by(id=link.section).first()
                if section is not None:
                    use_sections.append({ 'name': section.title, 'id': section.id })

            table_of_contents.append({ 'name': cat.title, 'id': cat.id, 'sections': use_sections })


        dict_urls = {}
        urls = session.query(SiteURL).filter_by(site=site).order_by(desc(SiteURL.order), SiteURL.id).all()
        for url in urls:
            if url.section not in dict_urls:
                dict_urls[url.section] = []
            dict_urls[url.section].append(url.publicJSON())

        info = get_site_info(['home_page_content'], site, session)

        profilesJS = []
        for profile in session.query(UserProfile).filter(UserProfile.disasters.contains(site)).order_by(UserProfile.order, UserProfile.id).all():
            profilesJS.append(profile.publicJSON())

        issueJS = {}
        issuesJS = []
        issues = session.query(Issue).filter_by(site=site, archived=False).order_by(desc(Issue.last_updated), Issue.id)
        for issue in issues:     
            issuesJS.append(issue.publicJSON())

        issueContentJS = []
        if len(issuesJS) > 0:
            issue_id = request.args.get('issueID', issuesJS[0]['id'])
            issueContents = session.query(IssueContent).filter_by(issue=issue_id).order_by(IssueContent.order, IssueContent.id).all()
            issueJS = session.query(Issue).filter_by(site=site, id=issue_id).one().publicJSON()

            for issueContent in issueContents:     
                issueContentJS.append(issueContent.publicJSON())

        # Close database connection
        session.close()

        # Render HTML template with Jinja
        return render_page('pages/home.html', 
                            site=site, 
                            includeSite=True, 
                            table_contents=table_of_contents, 
                            useful_links=dict_urls, 
                            main_content=info, 
                            team=profilesJS, 
                            sites=sites, 
                            private_sites=private_sites, 
                            issues=issuesJS, 
                            issue=issueJS,
                            issue_content=issueContentJS, 
                            issue_id=issue_id)
      

@api.route('/news')
class ViewAllNews(Resource):
    def get(self, site):
        session = Session()

        linksJS = []
        links = session.query(Link).filter_by(site=site).order_by(desc(Link.created), Link.id).all()
        for link in links:
            if link.public:
                linksJS.append(link.publicJSON())

        session.close()

        return render_page('pages/view_all_links.html', site=site, includeSite=False, links=linksJS)

@api.route('/literature')
class ViewAllLiterature(Resource):
    def get(self, site):
        session = Session()

        literatureJS = []
        literatures = session.query(Literature).filter_by(site=site).order_by(desc(Literature.created), Literature.id).all()
        for link in literatures:
            if link.public:
                literatureJS.append(link.publicJSON())

        session.close()

        return render_page('pages/view_all_literature.html', site=site, includeSite=False, literatures=literatureJS)


@api.route('/other')
class Other(Resource):
    def get(self, site):

        session = Session()

        section = session.query(Section).filter_by(site=site).filter_by(special_type='other').first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(site=site).filter_by(site=site).filter_by(section=section.id).order_by(desc(SectionPost.order), SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(id=link.post).first()
            if post is not None:
                if post.public:
                    postsJS.append(post.siteJSON(session))

        session.close()

        return render_page('pages/other_information.html', site=site, includeSite=False, section=sectionJS, posts=postsJS)


@api.route('/categories')
class Categories(Resource):
    def get(self, site):
        session = Session()

        catJS = []
        for cat in session.query(Category).filter_by(special_type='resource').filter_by(site=site).order_by(Category.order, Category.id).all():
            catJS.append(cat.publicJSON())

        session.close()

        return render_page('pages/provider_select.html', site=site, includeSite=False, categories=catJS)

@api.route('/categories/<categoryID>')
class ViewCategory(Resource):
    def get(self, categoryID, site):
        session = Session()

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        categoryJS = category.publicJSON()

        catJS = []
        for cat in session.query(Category).filter_by(special_type='resource').filter_by(site=site).order_by(Category.order, Category.id).all():
            catJS.append(cat.publicJSON())

        category_sections = session.query(CategorySection).filter_by(site=site).filter_by(category=categoryID).order_by(CategorySection.order, CategorySection.id).all()
        sectionsJS = []
        for link in category_sections:
            section = session.query(Section).filter_by(site=site).filter_by(id=link.section).first()
            if section is not None:
                if section.public:
                    sectionsJS.append(section.publicJSON())

        session.close()
        headers = {'Content-Type': 'text/html'}
        return render_page('pages/provider_select.html', site=site, includeSite=False, categories=catJS, sections=sectionsJS, category=categoryJS)

@api.route('/section/<sectionID>')
class ViewSection(Resource):
    def get(self, sectionID, site):
        categoryID = request.args.get('categoryID', None)
        postID = request.args.get('postID', None)

        session = Session()

        sites = session.query(Site).filter_by(public=True)
        private_sites = session.query(Site).filter_by(public=False)

        category = session.query(Category).filter_by(site=site).filter_by(id=categoryID).first()
        categoryJS = None
        if category is not None:
            categoryJS = category.publicJSON()


        table_of_contents = []
        all_categories = session.query(Category).filter_by(site=site).all()
        for cat in all_categories:
            use_sections = []

            category_sections = session.query(CategorySection).filter_by(site=site).filter_by(category=cat.id).order_by(CategorySection.order, CategorySection.id).all()
            for link in category_sections:
                section = session.query(Section).filter_by(site=site).filter_by(id=link.section).first()
                if section is not None:
                    if section.public:
                        use_sections.append({ 'name': section.title, 'id': section.id })

            table_of_contents.append({ 'name': cat.title, 'id': cat.id, 'sections': use_sections })

        # move_index = None
        # for i in table_of_contents:
        #     if i['id'] == categoryID:
        #         move_index = table_of_contents.index(i)

        # if move_index is not None:
        #     table_of_contents.insert(0, table_of_contents.pop(move_index))


        section = session.query(Section).filter_by(site=site).filter_by(id=sectionID).first()
        sectionJS = section.publicJSON()

        section_posts = session.query(SectionPost).filter_by(site=site).filter_by(section=sectionID).order_by(SectionPost.order, SectionPost.id).all()
        postsJS = []
        for link in section_posts:
            post = session.query(Post).filter_by(site=site).filter_by(id=link.post).first()
            if post is not None:
                if post.public:
                    js = post.siteJSON(session)
                    if js != {}:
                        postsJS.append(js)

        session.close()

        return render_page('pages/section.html', site=site, includeSite=True, section=sectionJS, posts=postsJS, category=categoryJS, table_contents=table_of_contents, postID=postID, sites=sites, private_sites=private_sites)

@api.route('/literature/<literatureID>')
class ViewLiterature(Resource):
    def get(self, literatureID, site):
        session = Session()

        lit = session.query(Literature).filter_by(site=site).filter_by(id=literatureID).first()
        if lit is None:
            abort(404)

        litLinks = session.query(LiteratureLink).filter_by(site=site).filter_by(literature=literatureID).all()
        linksJS = []
        for content in litLinks:
            linksJS.append(content.publicJSON())

        litJS = lit.publicJSON()

        session.close()

        return render_page('pages/view_literature.html', site=site, includeSite=False, literature=litJS, links=linksJS)



@api.route('/contact')
class Contact(Resource):
    def get(self, site):
        return render_page('pages/contact.html', site=site, includeSite=False)

@api.route('/privacy')
class Privacy(Resource):
    def get(self, site):
        return render_page('pages/privacy.html', site=site, includeSite=False)

@api.route('/medical')
class Medical(Resource):
    def get(self, site):
        return render_page('pages/medical.html', site=site, includeSite=False)

@api.route('/tos')
class TOS(Resource):
    def get(self, site):
        return render_page('pages/tos.html', site=site, includeSite=False)

@api.route('/cookies')
class Cookies(Resource):
    def get(self, site):
        return render_page('pages/cookies.html', site=site, includeSite=False)
    
@api.route('/sponsor')
class Sponsor(Resource):
    def get(self, site):
        return render_page('pages/sponsor.html', site=site, includeSite=False)

@api.route('/aboutus')
class Aboutus(Resource):
    def get(self, site):
        session = Session()

        sites = session.query(Site).filter_by(public=True)

        profilesJS = []
        for profile in session.query(UserProfile).order_by(UserProfile.order, UserProfile.id).all():
            profilesJS.append(profile.publicJSON())

        session.close()

        return render_page('pages/about_us.html', site=site, includeSite=False, user_profiles=profilesJS, sites=sites)


@api.route('/feedback')
class SubmitFeedback(Resource):
    def post(self, site):
        email = request.form.get('email', '')
        feedback = request.form['feedback']
        ftype = request.args.get('ftype')

        session = Session()
        session.add(Feedback(email=email, text=feedback, ftype=ftype))

        session.commit()
        session.close()

        slack_msg = "*Email*: `{}`\n*Type*: `{}`\n*Content:* ```{}```".format(email, ftype, feedback)
        post_to_slack(slack_msg)

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Pages_submit_feedback', site=site))#make_response(render_template('pages/success_feedback.html'), 200, headers)

    def get(self, site):
        return render_page('pages/success_feedback.html', site=site, includeSite=False)    


# Mark file expose
@api.route('/loaderio-be2727d05bae7704d76a1b78f85fa5bb.txt')
class LoaderIO(Resource):
    def get(self, site):
        return send_from_directory('./source/static', filename='loaderio-be2727d05bae7704d76a1b78f85fa5bb.txt')
