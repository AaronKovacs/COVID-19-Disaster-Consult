import base64
import datetime
import string
import random
import json
import calendar

from flask import current_app as app
from flask import Flask, g, jsonify
from flask_security import UserMixin, RoleMixin
from flask_restplus import abort

from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey, Text
from sqlalchemy import or_
from sqlalchemy import DateTime
from sqlalchemy import desc
from sqlalchemy import and_
from sqlalchemy.orm import deferred

from passlib.hash import pbkdf2_sha256
from itsdangerous import Serializer, JSONWebSignatureSerializer, BadSignature, BadData

from ..database.base import Base 
from ..database.database import Session

class UserProfile(Base):
    __tablename__ = 'user_profile'
    id = Column(Integer(), primary_key=True)
    user = Column(String(255))

    title = Column(String(255), default='')
    content = Column(Text(), default='')
    profile_image = Column(String(255), default='')
    website = Column(String(255), default='')
    order = Column(Integer(), default=100)
    section = Column(String(255), default='')

    slack_id = Column(String(255), default='')
    disasters = Column(String(255), default='')

    last_updated = Column(DateTime(), onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'user': self.user,
        'title': self.title,
        'content': self.content,
        'profile_image': self.profile_image,
        'website': self.website,
        'order': self.order,
        'disasters': self.disasters,
        'slack_id': self.slack_id,
        'section': self.section
        }