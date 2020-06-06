import base64
import datetime
import string
import random
import json
import calendar

from flask import current_app as app
from flask import Flask, g, jsonify
from flask_security import UserMixin, RoleMixin
from flask import redirect, render_template, url_for

from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy import Boolean, DateTime, Column, Integer, Float, String, ForeignKey

from passlib.hash import pbkdf2_sha256
from itsdangerous import Serializer, JSONWebSignatureSerializer, BadSignature, BadData

from ..database.base import Base
from ..database.database import Session

from .user import User

class ActivityTrack(Base):
    __tablename__ = 'activity_track'
    id = Column(Integer(), primary_key=True)
    text = Column(String(1000))
    object_id = Column(String(255))
    object_type = Column(String(1000))
   
    user_id = Column(String(255))
    draft = Column(Integer())

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    site = Column(String(255))


    def publicJSON(self, site):
        return {
        'id': self.id,
        'text': self.text,
        'created': self.last_updated_formatted(),
        'object_id': self.object_id,
        'object_type': self.object_type,
        'draft': self.draft,
        'user': self.getUser(),
        'url': self.getURL(site)
        }

    def last_updated_formatted(self):
        try:
            import timeago
            return timeago.format(self.created, datetime.datetime.utcnow())
        except:
            print('here')
            return "Missing package requirement: timeago"


    def getUser(self):
        session = Session()
        user = session.query(User).filter_by(id=self.user_id).first()
        if user is None:
            return {}
        js = user.publicJSON()
        session.close()
        return js

    def getURL(self, site):
        if self.object_type == 'post':
            return url_for('Posts_view', id=self.object_id, site=site)
        if self.object_type == 'section':
            return url_for('Sections_view_section', id=self.object_id, site=site)
        if self.object_type == 'category':
            return url_for('Categories_view_category', id=self.object_id, site=site)
        if self.object_type == 'literature':
            return url_for('Literatures_view', id=self.object_id, site=site)
        if self.object_type == 'link':
            return url_for('Links_view', id=self.object_id, site=site)

        return ''

        
