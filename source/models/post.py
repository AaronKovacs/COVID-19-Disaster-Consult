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

from . import draft as draft_c
from .section_post import SectionPost
from .section import Section

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

    def sections(self, session):
        links = session.query(SectionPost).filter_by(post=self.id).all()
        sections = []
        for link in links:
            sec = session.query(Section).filter_by(id=link.section).first()
            if sec is not None:
                sections.append(sec.publicJSON())
        return sections

    def status(self, session):
        draft = session.query(draft_c.Draft).filter_by(object_type='post', object_id=self.id).order_by(desc(draft_c.Draft.created), draft_c.Draft.id).first()
        if draft is None:
            return 'Unknown'
        if draft.rejected == False and draft.approved == False:
            return 'Pending Review'
        if draft.rejected:
            return 'Draft Rejected'
        if draft.approved and self.public:
            return 'Public & Approved'
        if draft.approved and self.public == False:
            return 'Private & Approved'

        return 'Unknown'

    def hasDraft(self, session):
        draft = session.query(draft_c.Draft).filter_by(object_type='post', object_id=self.id, approved=False).order_by(desc(draft_c.Draft.created), draft_c.Draft.id).first()
        if draft is None:
            return None
        if json.loads(draft.new_content) != self.publicJSON():
            return draft
        return None

    def latestJSON(self, session):
        js = self.publicJSON()
        js['content'] = self.process_content(self.content)
        js['last_updated'] = self.last_updated_formatted()
        return js

    def siteJSON(self, session):
        draft = session.query(draft_c.Draft).filter_by(object_type='post', object_id=self.id, approved=True).order_by(desc(draft_c.Draft.created), draft_c.Draft.id).first()
        if draft is None:
            return self.latestJSON(session)
        js = json.loads(draft.new_content)
        js['content'] = self.process_content(js['content'])
        js['last_updated'] = self.last_updated_formatted()
        return js

    def siteDraftID(self, session):
        draft = session.query(draft_c.Draft).filter_by(object_type='post', object_id=self.id, approved=True).order_by(desc(draft_c.Draft.created), draft_c.Draft.id).first()
        if draft is None:
            return None

        js = json.loads(draft.new_content)
        if js['public'] == True:
            return draft.id

        return None

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



    def process_content(self, text):
        edited_content = text
        try:
            # Editing Videos
            matches = re.findall(r'(?:<oembed[^>]*)(?:(?:\/>)|(?:>.*?<\/oembed>))', edited_content)
            for match in matches:
                src = re.findall(r'(?<=url=").*?(?=[\*"])', match)[0]
                video = re.findall(r'((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)', src)[0][-1]

                src = 'https://www.youtube.com/embed/%s' % video
                iframe_start = """<iframe class="noprint" width="100%" height="315" src=\""""
                iframe_end = """" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""
                edited_content = edited_content.replace(match, iframe_start + src + iframe_end)

            # Editing Images to Add Lightbox
            matches = re.findall(r'(?:<figure class="image[^>]*)(?:(?:\/>)|(?:>.*?<\/figure>))', edited_content)
            for match in matches:
                figure_class = src = re.findall(r'(?:class=")(image[^"]*)', match)[0]
                src = re.findall(r'(?<=src=").*?(?=[\*"])', match)[0]
                caption_match = re.findall(r'<figcaption>(.*?)<\/figcaption>', match)

                caption_str = ""
                if caption_match:
                    caption_str = '<figcaption class="img-caption figure-caption">{}</figcaption>'.format(caption_match[0])

                lightbox_img = '<figure class="{0} text-center"><a href="{1}" data-toggle="lightbox"><img src="{1}" class="img-fluid hoverable"></a>{2}</figure>'
                lightbox_img = lightbox_img.format(figure_class, src, caption_str)
                edited_content = edited_content.replace(match, lightbox_img)

            # Editing hyperlink target to _blank
            matches = re.findall(r'<a (.*?)>', edited_content)
            for match in matches:

                # Prevent changing internal links
                if 'http' not in match:
                    continue

                # Prevent changing data toggles
                if 'data-toggle=' in match:
                    continue

                new_link = '{} target = "_blank"'.format(match)
                edited_content = edited_content.replace(match, new_link)

            return edited_content
        except:
            return self.content
