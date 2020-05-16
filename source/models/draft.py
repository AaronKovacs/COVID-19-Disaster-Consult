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

class Draft(Base):
    __tablename__ = 'drafts'
    id = Column(Integer(), primary_key=True)
    object_type = Column(String(255))
    object_id = Column(String(255))

    old_content = Column(Text())
    new_content = Column(Text())

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'old_content': json.loads(self.old_content),
        'new_content': json.loads(self.new_content),
        'object_type': self.object_type,
        'object_id': self.object_id,
        'created': self.last_updated_formatted()
        }

    def last_updated_formatted(self):
        try:
            import timeago
            return timeago.format(self.created, datetime.datetime.utcnow())
        except:
            print('here')
            return "Missing package requirement: timeago"