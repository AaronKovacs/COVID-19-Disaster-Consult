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

from itsdangerous import URLSafeTimedSerializer

from wtforms import Form, BooleanField, StringField, PasswordField, validators

api = APINamespace('Posts')

ALLOWED_EXTENSIONS = set(['png', 'jpeg', 'jpg', 'image'])

@api.route('/list')
class ListPosts(Resource):
    @login_required
    def get(self):
        session = Session()

        postsJS = []
        posts = session.query(Post).order_by(desc(Post.created), Post.id).all()
        for post in posts:
            postsJS.append(post.publicJSON())

        session.close()

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_posts.html', posts=postsJS), 200, headers)

@api.route('/view')
class View(Resource):
    @login_required
    def get(self):
        postID = request.args.get('id')
        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            abort(404)

        post_contents = session.query(PostContent).filter_by(post=postID).all()
        contentsJS = []
        for content in post_contents:
            contentsJS.append(content.publicJSON())

        post_images = session.query(PostImage).filter_by(post=postID).all()
        imagesJS = []
        for content in post_images:
            imagesJS.append(content.publicJSON())

        postJS = post.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_view_post.html', post=postJS, links=contentsJS, images=imagesJS), 200, headers)

@api.route('/<postID>/delete')
class DeletePost(Resource):
    @login_required
    def get(self, postID):
        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            abort(404)
        session.delete(post)

        post_contents = session.query(PostContent).filter_by(post=postID).all()
        for content in post_contents:
            session.delete(content)

        post_images = session.query(PostImage).filter_by(post=postID).all()
        for content in post_images:
            session.delete(content)

        post_links = session.query(SectionPost).filter_by(post=postID).all()
        for content in post_links:
            session.delete(content)


        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Posts_list_posts'))


@api.route('/<postID>/<imageID>/image/delete')
class DeleteImage(Resource):
    @login_required
    def get(self, postID, imageID):
        session = Session()

        post_image = session.query(PostImage).filter_by(id=imageID).first()
        if post_image is not None:
            session.delete(post_image)

        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Posts_view', id=postID))

@api.route('/<postID>/<urlID>/url/delete')
class DeleteURL(Resource):
    @login_required
    def get(self, postID, urlID):
        session = Session()

        content = session.query(PostContent).filter_by(id=urlID).first()
        if content is not None:
            session.delete(content)

        session.commit()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for('Posts_view', id=postID))

@api.route('/create')
class CreatePost(Resource):
    @login_required
    def post(self):
        postID = request.args.get('id', None)

        print(request.form)

        title = request.form['title']
        content = request.form['content']
        public = False
        if request.form.get('public') != None:
            public = True

        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            post = Post()

        post.title = title
        post.content = content
        post.public = public

        session.add(post)
        session.commit()
        postID = post.id
        session.close()

        return redirect(url_for('Posts_view', id=postID))

    @login_required
    def get(self):
        postID = request.args.get('id')
        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/posts/admin_panel_create_post.html', post=Post().blankJSON()), 200, headers)

        postJS = post.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_create_post.html', post=postJS), 200, headers)


@api.route('/<postID>/url/add')
class AddURL(Resource):
    @login_required
    def post(self, postID):
        contentID = request.args.get('id')

        title = request.form['title']
        url = request.form['url']

        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            session.close()
            abort(404)

        content = session.query(PostContent).filter_by(id=contentID).first()
        if content is None:
            content = PostContent()
        

        content.post = postID
        content.text = title
        content.url = url
        content.content_type = "URL"

        session.add(content)
        session.commit()
        session.close()

        return redirect(url_for('Posts_view', id=postID))

    @login_required
    def get(self, postID):
        contentID = request.args.get('id')
        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            session.close()
            abort(404)

        content = session.query(PostContent).filter_by(id=contentID).first()
        if content is None:
            session.close()

            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('admin/posts/admin_panel_post_add_content.html', content=PostContent().blankJSON()), 200, headers)

        contentJS = content.publicJSON()
        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_post_add_content.html', content=contentJS), 200, headers)


@api.route('/<postID>/upload/image')
class UploadImage(Resource):
    @login_required
    def post(self, postID):
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

            postImage = PostImage(post=postID, text=title, source_url=original_url, large_url=url)
            session.add(postImage)
            session.commit()

            session.close()

            return redirect(url_for('Posts_view', id=postID))

    @login_required
    def get(self, postID):
        session = Session()

        post = session.query(Post).filter_by(id=postID).first()
        if post is None:
            abort(404)

        session.close()
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('admin/posts/admin_panel_post_upload_image.html', id=postID), 200, headers)

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