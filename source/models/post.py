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
    content = Column(String(10000))
    author = Column(String(255))
    public = Column(Boolean, default=False)
    locale = Column(String(7), default='US')

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'title': self.title,
        'content': self.content,
        'public': self.public,
        'last_updated': str(self.last_updated)
        }

    def blankJSON(self):
        return {
        'title': '',
        'content': '',
        'public': False,
        'last_updated': ''
        }