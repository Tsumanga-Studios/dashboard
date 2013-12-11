"""
  Simple pages of the Dashboard
"""

from tornado import web

import dashboard

class VersionPage(web.RequestHandler):
    def get(self):
        self.write(dashboard.version)

class DummyPage(web.RequestHandler):
    def get(self, chartType):
        self.render("chart.html", chartType=chartType)

def urls():
    return [
        (r"/dashboard/version", VersionPage),
        (r"/dashboard/dummy/([a-zA-Z]+)", DummyPage),
        ]
