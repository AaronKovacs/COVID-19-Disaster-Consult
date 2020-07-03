import base64
import datetime
import string
import random
import json
import calendar

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

class SiteInfo(Base):
    __tablename__ = 'site_info'
    id = Column(Integer(), primary_key=True)

    site = Column(String(255))

    # Unused on mainsite, just for organization
    title = Column(String(255))

    # Either 'Raw HTML':raw or 'HTML Text':text
    data_type = Column(String(255))

    # Actual Content
    data = Column(Text())

    # ID of content for use on site
    content_type = Column(String(255))

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'title': self.title,
        'site': self.site,
        'data': self.data,
        'data_type': self.data_type,
        'content_type': self.content_type
        }

    def blankJSON(self):
        return {
        'id': '',
        'title': '',
        'site': '',
        'data': '',
        'data_type': '',
        'content_type': ''
        }
