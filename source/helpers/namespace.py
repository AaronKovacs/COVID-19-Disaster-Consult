from flask_restplus import Resource, Api, abort, Namespace

class APINamespace(Namespace):
    @property
    def path(self):
        return (self._path or ('')).rstrip('/')