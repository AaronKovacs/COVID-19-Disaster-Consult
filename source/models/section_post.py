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

class SectionPost(Base):
    __tablename__ = 'section_post'
    id = Column(Integer(), primary_key=True)
    section = Column(String(255))
    post = Column(String(255))
    order = Column(Integer(), default=100)
    created = Column(DateTime(), default=datetime.datetime.utcnow)
    last_updated = Column(DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    site = Column(String(255))