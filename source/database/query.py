from sqlalchemy.orm import Query
from flask_restplus import abort
from ..helpers.helpers import *

class BaseQuery(Query):

  def first_or_404(self, description=None):
        rv = self.first()
        if rv is None:
            abort(400, 'Could not find item.')
        return rv

  def all_or_404(self, description=None):
        rv = self.all()
        if rv is None:
            abort(400, 'Could not find items.')
        return rv