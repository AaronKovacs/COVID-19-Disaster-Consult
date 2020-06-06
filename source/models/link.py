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
from sqlalchemy import Boolean, DateTime, Column, Integer, Float, String, ForeignKey

from passlib.hash import pbkdf2_sha256
from itsdangerous import Serializer, JSONWebSignatureSerializer, BadSignature, BadData

from ..database.base import Base
from ..database.database import Session

def uniqueLinkID():
    possibleID = alphaNumericID()
    session = Session()
    while session.query(Link).filter(id == possibleID).limit(1).first() is not None:
        possibleID = alphaNumericID()
    session.close()
    return possibleID

def alphaNumericID():
    return 'p' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

class Link(Base):
    __tablename__ = 'news_links'
    id = Column(String(255), default=uniqueLinkID, primary_key=True)
    title = Column(String(1000))
    description = Column(String(1000))
    url = Column(String(1000))
    source_url = Column(String(1000))
    large_url = Column(String(1000))

    author = Column(String(255))
    public = Column(Boolean, default=False)
    locale = Column(String(7), default='US')
    site = Column(String(255))

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'title': self.title,
        'description': self.description,
        'url': self.url,
        'source_url': self.source_url,
        'large_url': self.large_url,
        'author': self.author,
        'public': self.public,
        'last_updated': str(self.last_updated)
        }

    def blankJSON(self):
        return {
        'id': '',
        'title': '',
        'description': '',
        'source_url': self.source_url,
        'large_url': self.large_url,
        'url': '',
        'author': '',
        'public': False,
        'last_updated': ''
        }