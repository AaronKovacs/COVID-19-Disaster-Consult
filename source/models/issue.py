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
from sqlalchemy import Boolean, DateTime, Column, Integer, Float, String, ForeignKey, Text, Boolean

from passlib.hash import pbkdf2_sha256
from itsdangerous import Serializer, JSONWebSignatureSerializer, BadSignature, BadData

from ..database.base import Base
from ..database.database import Session

class Issue(Base):
    __tablename__ = 'issue'
    id = Column(Integer(), primary_key=True)

    site = Column(String(255))
    title = Column(String(255))
    subtitle = Column(String(255))
    archived = Column(Boolean())

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'title': self.title,
        'subtitle': self.subtitle,
        'site': self.site, 
        'last_updated': str(self.last_updated),
        'archived': self.archived
        }

    def blankJSON(self):
        return {
        'id': '',
        'title': '',
        }
