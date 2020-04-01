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
from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey
from sqlalchemy import or_
from sqlalchemy import DateTime
from sqlalchemy import desc
from sqlalchemy import and_
from sqlalchemy.orm import deferred

from passlib.hash import pbkdf2_sha256
from itsdangerous import Serializer, JSONWebSignatureSerializer, BadSignature, BadData

from ..database.base import Base 
from ..database.database import Session

def uniqueUserID():
    possibleID = alphaNumericID()
    session = Session()
    while session.query(User).filter(id == possibleID).limit(1).first() is not None:
        possibleID = alphaNumericID()
    session.close()
    return possibleID

def alphaNumericID():
    return 'u' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

class User(Base, UserMixin):
    __tablename__ = 'user'
    id = Column(String(255), default=uniqueUserID, primary_key=True)
    email = Column(String(255), unique=True)
    username = Column(String(255), unique=True)
    password = Column(String(255))
    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), onupdate=datetime.datetime.utcnow)
    realname = Column(String(255))
    description = Column(String(255))
    privilege = Column(Integer(), default=0)
    active = Column(Boolean())

    def is_active(self):
        # Here you should write whatever the code is
        # that checks the database if your user is active
        return self.active

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def hash_password(self, unhashedPassword):
        self.password = pbkdf2_sha256.hash(unhashedPassword)

    def verify_password(self, unhashedPassword):
        return pbkdf2_sha256.verify(unhashedPassword, self.password)

    def generate_auth_token(self):
        s = JSONWebSignatureSerializer(app.config['SECRET_KEY'])
        return s.dumps({ 'username': self.username })
   
    @staticmethod
    def verify_auth_token(token):
        s = JSONWebSignatureSerializer(app.config['SECRET_KEY'])

        data = None
        try:
            data = s.loads(base64.b64decode(token))
        except:
            pass

        if data is None:
            try:
                data = s.loads(token)
            except:
                return None


        session = Session()
        record = session.query(UsernameRecord).filter_by(name=data['username']).first()
        if record is None:
            return None
        user = session.query(User).filter_by(id=record.user).first()
        if not user:
            return None #User doesn't exist
        session.expunge(user)
        session.close()
        return user