"""
  Web services for simple reports

"""

import tsumanga
from tsumanga.webservice import WebServiceHandler

import dashboard
from dashboard import version
from dashboard import distimo

class Version(WebServiceHandler):
    _versions = dict(version=dashboard.version, infrastructure=tsumanga.version)
    @staticmethod
    def register(modname, version):
        Version._versions[modname] = version
    def get(self):
        self.json_response(self._versions)

def urls():
    return [
        (r"/app/dash/version", Version),
        ] + distimo.urls()
