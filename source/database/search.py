import json
import logging

from flask import Flask, g, jsonify, current_app

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import event
import sqlalchemy.pool as Pool
from sqlalchemy import event
from sqlalchemy import case

from ..database.database import Session


from ..configuration.config import ELASTIC_SEARCH, ENV_NAME
from .base import Base
from .query import BaseQuery

from elasticsearch import Elasticsearch

class SearchableMixin(object):

    @classmethod
    def search(cls, site, session, expression, page, per_page):
        env_name = ENV_NAME()
        print(expression)
        ids, total = query_index_simple('%s_%s' % (env_name, cls.__tablename__), site, expression, page, per_page)
        if total == 0:
            return None, 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return session.query(cls).filter(cls.id.in_(ids)).order_by(case(when, value=cls.id)), total

    @classmethod
    def search_popularity(cls, session, expression, page, per_page):
        ids, total = query_index_most_popular('%s_%s' % (ENV_NAME(), cls.__tablename__), expression, page, per_page)
        if total == 0:
            return None, 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return session.query(cls).filter(cls.id.in_(ids)).order_by(case(when, value=cls.id)), total

    @classmethod
    def search_partial(cls, session, expression, page, per_page):
        ids, total = query_partial('%s_%s' % (ENV_NAME(), cls.__tablename__), expression, page, per_page)
        if total == 0:
            return None, 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        if len(when) == 0:
            return None, 0

        return session.query(cls).filter(cls.id.in_(ids)).order_by(case(when, value=cls.id)), total

    @classmethod
    def reindex(cls, session):
        es = Elasticsearch(ELASTIC_SEARCH)
        objs = session.query(cls).all()
        print('Started indexing %s - %s objects' % (cls.search_tablename(cls.__tablename__), len(objs)))
        for obj in objs:
            if obj.should_index(session):
                print('Indexing %s/%s - id: %s' % (objs.index(obj) + 1, len(objs), obj.id))
                add_to_index_async(cls.search_tablename(cls.__tablename__), obj, es, session)
            else:
                print('Not Indexing %s/%s - id: %s' % (objs.index(obj) + 1, len(objs), obj.id))
        print('Finished indexing ' + cls.search_tablename(cls.__tablename__))


    def update_search_index(self, session):
        try:
            if self.should_index(session):
                add_to_index('%s_%s' % (ENV_NAME(), self.__tablename__), self, session)
        except:
            print("Failed to update search index")

    def search_tablename(table):
        return '%s_%s' % (ENV_NAME(), table)

    def rank(self, session):
        return 0

def search_clean(text):
    cleaned_string = ''
    available_chars = 'abcdefghijklmnopqrstuvwxyz1234567890 #'

    if text is None or text == '':
        return text

    for character in text.lower():
        if character in available_chars:
            cleaned_string += character

    return cleaned_string

def add_to_index_async(index, model, es, session):
    payload = {}
    for field in model.__searchable__:
        if field == 'tagged_description':
            payload[field] = search_clean(model.tagged_description(session))
        else:
            payload[field] = search_clean(getattr(model, field))
    #payload['rank'] = model.rank(session)
    print(index)
    print(payload)
    print(model.id)
    es.index(index=index, id=model.id, body=payload)

def add_to_index(index, model, session):
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        if field == 'tagged_description':
            payload[field] = search_clean(model.tagged_description(session))
        else:
            payload[field] = search_clean(getattr(model, field))
    payload['rank'] = model.rank(session)

    current_app.elasticsearch.index(index=index, id=model.id, body=payload)


def remove_from_index(index, model):
    if not current_app.elasticsearch:
        print('Current app elasticsearch is null')
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_partial(index, query, page, per_page):
    print('hereindex2')
    if not current_app.elasticsearch:
        print('Current app elasticsearch is null')
        return [], 0
    #

    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'multi_match': {'query': search_clean(query), 'fields': ['*'], 'type' : 'phrase_prefix'}}, "sort": [{"rank": {"order": "desc"}}],
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [hit['_id'] for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']

def query_index(index, site, query, page, per_page):
    if not current_app.elasticsearch:
        print('Current app elasticsearch is null')
        return [], 0
    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'filtered': {'query': {'multi_match': {'query': search_clean(query), 'fields': ['*'], 'type' : 'phrase_prefix'}},"filter": {"term": {"site": site}}}},"sort": [{"rank": {"order": "desc"}}],'from': (page - 1) * per_page, 'size': per_page}
)
    ids = [hit['_id'] for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']

def query_index_simple(index, site, query, page, per_page):
    if not current_app.elasticsearch:
        print('Current app elasticsearch is null')
        return [], 0
    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'multi_match': {'query': search_clean(query), 'fields': ['*'], 'type' : 'phrase_prefix'}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [hit['_id'] for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']


def query_index_most_popular(index, query, page, per_page):
    print('hereinde3')
    if not current_app.elasticsearch:
        print('Current app elasticsearch is null')
        return [], 0
    search = current_app.elasticsearch.search(
        index=index,
        body={"query" : { "match_all" : { } }, "sort": [{"rank": {"order": "desc"}}],
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [hit['_id'] for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']