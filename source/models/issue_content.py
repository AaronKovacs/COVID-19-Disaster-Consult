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
