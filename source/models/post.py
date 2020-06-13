import base64
import datetime
import string
import random
import json
import calendar
import re
import urllib.parse as urlparse

from flask import current_app as app
from flask import Flask, g, jsonify
from flask_security import UserMixin, RoleMixin

from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy import Boolean, DateTime, Column, Integer, Float, String, ForeignKey, Text

from passlib.hash import pbkdf2_sha256
from itsdangerous import Serializer, JSONWebSignatureSerializer, BadSignature, BadData

from ..database.base import Base
from ..database.database import Session

def uniquePostID():
    possibleID = alphaNumericID()
    session = Session()
    while session.query(Post).filter(id == possibleID).limit(1).first() is not None:
        possibleID = alphaNumericID()
    session.close()
    return possibleID

def alphaNumericID():
    return 'p' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

class Post(Base):
    __tablename__ = 'posts'
    id = Column(String(255), default=uniquePostID, primary_key=True)
    title = Column(String(1000))
    content = Column(Text())
    author = Column(String(255))
    public = Column(Boolean, default=False)
    locale = Column(String(7), default='US')
    keywords = Column(String(255), default='US')
    site = Column(String(255))

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        keywords_txt = self.keywords
        if self.keywords is None:
            keywords_txt = ''

        return {
        'id': self.id,
        'title': self.title,
        'content': self.content,
        'public': self.public,
        'keywords': keywords_txt,
        'last_updated': self.last_updated_formatted()
        }

    def siteJSON(self):
        js = self.publicJSON()
        js['content'] = self.process_content()
        return js

    def blankJSON(self):
        return {
        'title': '',
        'content': '',
        'keywords': '',
        'public': False,
        'last_updated': ''
        }

    def last_updated_formatted(self):
        try:
            import timeago
            return timeago.format(self.last_updated, datetime.datetime.utcnow())
        except:
            print('here')
            return "Missing package requirement: timeago"



    def process_content(self):
        edited_content = self.content
        try:
            # Editing Videos
            matches = re.findall(r'(?:<oembed[^>]*)(?:(?:\/>)|(?:>.*?<\/oembed>))', edited_content)
            for match in matches:
                src = re.findall(r'(?<=url=").*?(?=[\*"])', match)[0]
                video = re.findall(r'((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)', src)[0][-1]
                print(video)
                '''

                url_data = urlparse.urlparse(src)
                query = urlparse.parse_qs(url_data.query)
                video = ''


                if 'youtube' in src:
                    video = query["v"][0]
                if 'youtu.be' in src:
                    comps = src.split('/')
                    video = comps[-1]
                    if '?' in video:
                        video = video.split('?')[0]
                '''
                src = 'https://www.youtube.com/embed/%s' % video
                iframe_start = """<iframe width="100%" height="315" src=\""""
                iframe_end = """" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""
                edited_content = edited_content.replace(match, iframe_start + src + iframe_end)

            # Editing Images to Add Lightbox
            matches = re.findall(r'(?:<figure class="image[^>]*)(?:(?:\/>)|(?:>.*?<\/figure>))', edited_content)
            for match in matches:
                figure_class = src = re.findall(r'(?:class=")(image[^"]*)', match)[0]
                src = re.findall(r'(?<=src=").*?(?=[\*"])', match)[0]
                lightbox_img = '<figure class="{0}"><a href="{1}" data-toggle="lightbox"><img src="{1}" class="img-fluid"></a></figure>'
                lightbox_img = lightbox_img.format(figure_class, src)
                edited_content = edited_content.replace(match, lightbox_img)

            return edited_content
        except:
            return self.content
