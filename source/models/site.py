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

from .literature import Literature
from .link import Link

def uniqueSiteID():
    possibleID = alphaNumericID()
    session = Session()
    while session.query(Site).filter(id == possibleID).limit(1).first() is not None:
        possibleID = alphaNumericID()
    session.close()
    return possibleID

def alphaNumericID():
    return 's' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

class Site(Base):
    __tablename__ = 'site'
    id = Column(String(255), default=uniqueSiteID, primary_key=True)
    slug = Column(String(30))
    title = Column(String(255))
    description = Column(String(1000))
    primary_color = Column(String(6))
    secondary_color = Column(String(6))
    public = Column(Boolean, default=False)
    order = Column(Integer(), default=100)

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'title': self.title,
        'slug': self.slug,
        'description': self.description,
        'public': self.public,
        'primary_color': self.primary_color,
        'secondary_color': self.secondary_color,
        'order': self.order,
        'last_updated': str(self.last_updated)
        }

    def hasLiterature(self, session):
        return False
        #return session.query(Literature).filter_by(site=self.slug).first() != None

    def hasNews(self, session):
        return False
        #return session.query(Link).filter_by(site=self.slug).first() != None