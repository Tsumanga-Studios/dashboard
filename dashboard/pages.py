"""
  Simple pages of the Dashboard
"""

from tornado import web

import dashboard

class VersionPage(web.RequestHandler):
    def get(self):
        self.write(dashboard.version)


def urls():
    return [(r"/dashboard/version", VersionPage)]
