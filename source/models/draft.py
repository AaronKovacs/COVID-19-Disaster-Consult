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

from .activity_track import ActivityTrack
from .user import User
from .section_post import SectionPost
from .section import Section
from .category_section import CategorySection
from .category import Category
from . import post as post_c

class Draft(Base):
    __tablename__ = 'drafts'
    id = Column(Integer(), primary_key=True)
    object_type = Column(String(255))
    object_id = Column(String(255))

    old_content = Column(Text())
    new_content = Column(Text())

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    approved = Column(Boolean(), default=False)
    rejected = Column(Boolean(), default=False)

    comment = Column(Text())

    def publicJSON(self):
        return {
        'id': self.id,
        'old_content': json.loads(self.old_content),
        'new_content': json.loads(self.new_content),
        'object_type': self.object_type,
        'object_id': self.object_id,
        'created': self.last_updated_formatted(),
        'approved': self.approved,
        'rejected': self.rejected,
        'comment': self.comment,
        'last_updated': self.last_updated_formatted()
        }

    def site(self, session):
        post = session.query(post_c.Post).filter_by(id=self.object_id).first()
        if post is None:
            return ''
        return post.site

    def last_updated_formatted(self):
        try:
            import timeago
            return timeago.format(self.last_updated, datetime.datetime.utcnow())
        except:
            print('here')
            return "Missing package requirement: timeago"

    def user(self, session):
        track = session.query(ActivityTrack).filter_by(draft=self.id).first()
        if track is None:
            return None

        user = session.query(User).filter_by(id=track.user_id).first()
        return user

    def last_updated_formatted(self):
        try:
            import timeago
            return timeago.format(self.created, datetime.datetime.utcnow())
        except:
            print('here')
            return "Missing package requirement: timeago"

    def routeText(self, session):
        links = session.query(SectionPost).filter_by(post=self.object_id).all()
        sections = []

        routes = []

        for link in links:
            sec = session.query(Section).filter_by(id=link.section).first()
            if sec is not None:
                categories = session.query(CategorySection).filter_by(section=sec.id).all()
                if categories is not None:
                    for cat in categories:
                        category = session.query(Category).filter_by(id=cat.category).first()
                        if category is not None:
                            routes.append('[%s] %s -> %s' % (category.site, category.title, sec.title))
                        else:
                            routes.append('[%s] %s' % (sec.site, sec.title))
                else:
                    routes.append('[%s] %s' % (sec.site, sec.title))
        


        return sorted(set(routes))
