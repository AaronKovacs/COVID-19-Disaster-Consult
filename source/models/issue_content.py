import base64
import datetime
import string
import random
import json
import calendar
import re

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

class IssueContent(Base):
    __tablename__ = 'issue_content'
    id = Column(Integer(), primary_key=True)

    site = Column(String(255))
    issue = Column(String(255))
    order = Column(Integer(), default=100)

    title = Column(String(255))
    data = Column(Text())

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'issue': self.issue,
        'title': self.title,
        'site': self.site,
        'order': self.order,
        'data': self.data
        }

    def blankJSON(self):
        return {
        'id': '',
        'issue': '',
        'title': '',
        'site': '',
        'order': '',
        'data': ''
        }


    def formattedJSON(self):
        js = self.publicJSON()
        js['data'] = self.process_data(self.data)
        return js

    def process_data(self, text):
        edited_data = text
        # try:
        # Editing Videos
        matches = re.findall(r'(?:<oembed[^>]*)(?:(?:\/>)|(?:>.*?<\/oembed>))', edited_data)
        for match in matches:
            src = re.findall(r'(?<=url=").*?(?=[\*"])', match)[0]
            video = re.findall(r'((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)', src)[0][-1]

            src = 'https://www.youtube.com/embed/%s' % video
            iframe_start = """<iframe class="noprint" width="100%" height="315" src=\""""
            iframe_end = """" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""
            edited_data = edited_data.replace(match, iframe_start + src + iframe_end)

        # Editing Images to Add Lightbox
        matches = re.findall(r'(?:<figure class="image[^>]*)(?:(?:\/>)|(?:>.*?<\/figure>))', edited_data)
        for match in matches:
            figure_class = src = re.findall(r'(?:class=")(image[^"]*)', match)[0]
            src = re.findall(r'(?<=src=").*?(?=[\*"])', match)[0]
            caption_match = re.findall(r'<figcaption>(.*?)<\/figcaption>', match)

            caption_str = ""
            if caption_match:
                caption_str = '<figcaption class="img-caption figure-caption">{}</figcaption>'.format(caption_match[0])

            lightbox_img = '<figure class="{0} text-center"><a href="{1}" data-toggle="lightbox"><img src="{1}" class="img-fluid hoverable"></a>{2}</figure>'
            lightbox_img = lightbox_img.format(figure_class, src, caption_str)
            edited_data = edited_data.replace(match, lightbox_img)

        # Editing hyperlink target to _blank
        matches = re.findall(r'<a (.*?)>', edited_data)
        for match in matches:

            # Prevent changing internal links
            if 'http' not in match:
                continue

            # Prevent changing data toggles
            if 'data-toggle=' in match:
                continue

            new_link = '{} target = "_blank"'.format(match)
            edited_data = edited_data.replace(match, new_link)

        return edited_data
        # except:
        #     print("\n\n\n\n:(\n\n\n\n\n")
        #     return self.data
