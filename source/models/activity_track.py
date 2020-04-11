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

from .user import User

class ActivityTrack(Base):
    __tablename__ = 'activity_track'
    id = Column(Integer(), primary_key=True)
    text = Column(String(1000))
    object_id = Column(String(255))
    object_type = Column(String(1000))
   
    user_id = Column(String(255))

    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def publicJSON(self):
        return {
        'id': self.id,
        'text': self.text,
        'created': self.created,
        'object_id': self.object_id,
        'object_type': self.object_type,
        'user': self.getUser()
        }

    def getUser(self):
        session = Session()
        user = session.query(User).filter_by(id=self.user_id).first()
        if user is None:
            return {}
        js = user.publicJSON()
        session.close()
        return js
