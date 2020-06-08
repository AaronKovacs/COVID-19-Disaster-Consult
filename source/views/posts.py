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
import re

from urllib.parse import urlparse
import urllib.parse

from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask import send_from_directory
from flask import jsonify
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
from flask_paginate import Pagination, get_page_args

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

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Posts')

ALLOWED_EXTENSIONS = set(['png', 'jpeg', 'jpg', 'image'])

@api.route('/list')
class ListPosts(Resource):
    @login_required
    def get(self, site):
        session = Session()

        postsJS = []
        posts = session.query(Post).filter_by(site=site).order_by(desc(Post.last_updated), Post.id).all()
        for post in posts:
            js = post.publicJSON()
            #js['last_updated'] = format(post.last_updated, datetime.datetime.now())
            
            postsJS.append(js)

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_posts.html', posts=postsJS, site=site), 200, headers)

@api.route('/view')
class View(Resource):
    @login_required
    def get(self, site):
        postID = request.args.get('id')
        session = Session()

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            abort(404)

        post_contents = session.query(PostContent).filter_by(site=site).filter_by(post=postID).all()
        contentsJS = []
        for content in post_contents:
            contentsJS.append(content.publicJSON())

        post_images = session.query(PostImage).filter_by(site=site).filter_by(post=postID).all()
        imagesJS = []
        for content in post_images:
            imagesJS.append(content.publicJSON())

        postJS = post.siteJSON()

        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
        

        actsJS = []
        acts = session.query(ActivityTrack).filter_by(site=site).filter_by(object_type='post', object_id=postID).order_by(desc(ActivityTrack.created), ActivityTrack.id).limit(per_page).offset(offset)
        for act in acts:
            actsJS.append(act.publicJSON(site))


        pagination = Pagination(page=page, per_page=per_page, total=session.query(ActivityTrack).filter_by(site=site).filter_by(object_type='post', object_id=postID).count(), css_framework='bootstrap4')

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_view_post.html', post=postJS, links=contentsJS, images=imagesJS, activities=actsJS, pagination=pagination, page=page,
                           per_page=per_page, site=site), 200, headers)

@api.route('/<postID>/delete')
class DeletePost(Resource):
    @login_required
    def get(self, postID, site):
        session = Session()

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            abort(404)
        session.delete(post)

        post_contents = session.query(PostContent).filter_by(site=site).filter_by(post=postID).all()
        for content in post_contents:
            session.delete(content)

        post_images = session.query(PostImage).filter_by(site=site).filter_by(post=postID).all()
        for content in post_images:
            session.delete(content)

        post_links = session.query(SectionPost).filter_by(site=site).filter_by(post=postID).all()
        for content in post_links:
            session.delete(content)


        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        track_activity('Deleted post', postID, 'post', site)

        return redirect(url_for('Posts_list_posts', site=site))


@api.route('/<postID>/<imageID>/image/delete')
class DeleteImage(Resource):
    @login_required
    def get(self, postID, imageID, site):
        session = Session()

        post_image = session.query(PostImage).filter_by(site=site).filter_by(id=imageID).first()
        if post_image is not None:
            session.delete(post_image)

        session.commit()
        session.close()

        track_activity('Added image from post', postID, 'post', site)

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Posts_view', id=postID, site=site))

@api.route('/<postID>/<urlID>/url/delete')
class DeleteURL(Resource):
    @login_required
    def get(self, postID, urlID, site):
        session = Session()

        content = session.query(PostContent).filter_by(site=site).filter_by(id=urlID).first()
        if content is not None:
            session.delete(content)

        session.commit()
        session.close()

        track_activity('Deleted url from post', postID, 'post', site)

        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Posts_view', id=postID, site=site))

@api.route('/create')
class CreatePost(Resource):
    @login_required
    def post(self, site):
        postID = request.args.get('id', None)

        title = request.form['title']
        content = request.form['content']
        keywords = request.form['keywords']
        public = False
        if request.form.get('public') != None:
            public = True

        session = Session()

        original_json = {}

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            post = Post(site=site)

        original_json = post.publicJSON()
         

        post.title = title
        post.content = content
        post.public = public
        post.keywords = keywords


        session.add(post)
        session.commit()
        postID = post.id

        draft_id = None
        final_json = post.publicJSON()
        if original_json != final_json:
            draft_id = save_draft(original_json, final_json, postID, 'post')

        session.close()

        if original_json != final_json:
            if original_json['title'] == '':
                track_activity('Created post \'%s\'' % post.title, postID, 'post', draft_id, site)
            else:
                track_activity('Saved post updates to \'%s\'' % post.title, postID, 'post', draft_id, site)

        return redirect(url_for('Posts_view', id=postID, site=site))

    @login_required
    def get(self, site):
        postID = request.args.get('id')
        session = Session()

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/posts/admin_panel_create_post.html', post=Post().blankJSON(), site=site), 200, headers)

        postJS = post.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_create_post.html', post=postJS, site=site), 200, headers)


@api.route('/<postID>/url/add')
class AddURL(Resource):
    @login_required
    def post(self, postID, site):
        contentID = request.args.get('id')

        title = request.form['title']
        url = request.form['url']

        session = Session()

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            session.close()
            abort(404)

        content = session.query(PostContent).filter_by(site=site).filter_by(id=contentID).first()
        if content is None:
            content = PostContent(site=site)
        

        content.post = postID
        content.text = title
        content.url = url
        content.content_type = "URL"

        session.add(content)
        session.commit()
        session.close()

        track_activity('Added url to post', postID, 'post', site)
        return redirect(url_for('Posts_view', id=postID, site=site))

    @login_required
    def get(self, postID, site):
        contentID = request.args.get('id')
        session = Session()

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            session.close()
            abort(404)

        content = session.query(PostContent).filter_by(site=site).filter_by(id=contentID).first()
        if content is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/posts/admin_panel_post_add_content.html', content=PostContent().blankJSON(), site=site), 200, headers)

        contentJS = content.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_post_add_content.html', content=contentJS, site=site), 200, headers)

@api.route('/upload/image')
class UploadJustImage(Resource):
    @login_required
    def post(self, site):
        callback = request.args.get("CKEditorFuncNum")
        error = ''
        file = ''
        if 'upload' in request.files:
            file = request.files['upload']
        if file.filename == '':
            return
        if file and allowed_file(file.filename):
            filename = secure_filename(alphaNumericID())


            imgSize = (1000, 1000)
            img_data = file.read()

            og_img = Image.open(io.BytesIO(img_data)).convert('RGB')
            width, height = og_img.size

            #Resize image
            originalImage = resizeIOImage(img_data, (width, height))
            resizedImage = resizeIOImage(img_data, imgSize)

            #Upload image to S3 bucket
            uploadImage(originalImage, "%soriginal" % filename)
            uploadImage(resizedImage, filename)

            original_url = "{}{}original.jpeg".format(S3_LOCATION, filename)
            url = "{}{}.jpeg".format(S3_LOCATION, filename)
            print(url)
            res = """<script type="text/javascript"> 
             window.parent.CKEDITOR.tools.callFunction(%s, '%s', '%s');
             </script>""" % (callback, url, error)
            response = make_response(res)
            response.headers["Content-Type"] = "text/html"
            return jsonify({ 'url': url, 'error': '', 'uploaded': 1, 'fileName': filename })

@api.route('/<postID>/upload/image')
class UploadImage(Resource):
    @login_required
    def post(self, postID, site):
        title = request.form['title'] or ''

        file = ''
        if 'image' in request.files:
            file = request.files['image']
        if file.filename == '':
            abort(400, 'Filename required.')
        if file and allowed_file(file.filename):
            filename = secure_filename(alphaNumericID())


            imgSize = (1000, 1000)
            img_data = file.read()

            og_img = Image.open(io.BytesIO(img_data)).convert('RGB')
            width, height = og_img.size

            #Resize image
            originalImage = resizeIOImage(img_data, (width, height))
            resizedImage = resizeIOImage(img_data, imgSize)

            #Upload image to S3 bucket
            uploadImage(originalImage, "%soriginal" % filename)
            uploadImage(resizedImage, filename)

            original_url = "{}{}original.jpeg".format(S3_LOCATION, filename)
            url = "{}{}.jpeg".format(S3_LOCATION, filename)

            session = Session()

            postImage = PostImage(post=postID, text=title, source_url=original_url, large_url=url, site=site)
            session.add(postImage)
            session.commit()

            session.close()
            track_activity('Added image to post', postID, 'post', site)
            return redirect(url_for('Posts_view', id=postID, site=site))

    @login_required
    def get(self, postID, site):
        session = Session()

        post = session.query(Post).filter_by(site=site).filter_by(id=postID).first()
        if post is None:
            abort(404)

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_post_upload_image.html', id=postID, site=site), 200, headers)

# Image Upload Helpers

def uploadImage(image, name):
    s3 = boto3.client("s3", aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)
    try:
        s3.put_object(Body=image, Bucket=S3_BUCKET, Key='%s.jpeg' % name, ContentType='application/image', ACL='public-read')# ExtraArgs={ 'ContentType': 'application/image', 'ACL': 'public-read' }
    except:
        abort(400, 'Upload Error')

def resizeIOImage(file, size):
    img = Image.open(BytesIO(file)).convert('RGB')
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
