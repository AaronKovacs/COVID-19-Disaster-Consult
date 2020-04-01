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

class PostImage(Base):
    __tablename__ = 'post_image'
    id = Column(Integer(), primary_key=True)
    post = Column(String(255))
    text = Column(String(255))
    source_url = Column(String(1000))
    large_url = Column(String(1000))
    
    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'text': self.text,
        'source_url': self.source_url,
        'large_url': self.large_url,
        'last_updated': str(self.last_updated)
        }

    def blankJSON(self):
        return {
        'id': '',
        'text': '',
        'source_url': '',
        'large_url': '',
        'last_updated': ''
        }