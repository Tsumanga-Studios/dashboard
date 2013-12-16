"""
  Simple pages of the Dashboard
"""

import os

from tornado import web, auth
from tornado.options import options

import dashboard

class VersionPage(web.RequestHandler):
    def get(self):
        self.write(dashboard.version)

class DummyPage(web.RequestHandler):
    def get(self, chartType):
        self.render("chart.html", chartType=chartType)

class HereTemp:
    def get_template_path(self):
        here = os.path.split(__file__)[0]
        return os.path.join(here, "templates")

class TsumangaOnly(auth.GoogleMixin):
    @web.asynchronous
    def get(self):
        name = self.get_secure_cookie('tsumanga-user')
        if name is not None:
            return self.authorised_get(name.decode('utf-8'))
        if self.get_argument("openid.mode", None):
           self.get_authenticated_user(self.async_callback(self._on_auth))
           return
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise web.HTTPError(599)
        email = user.get("email","")
        if not email.endswith("@tsumanga.com"):
            raise web.HTTPError(403)
        name = user["name"]
        self.set_secure_cookie('tsumanga-user', name)
        self.authorised_get(name)

class DownloadsPage(HereTemp, TsumangaOnly, web.RequestHandler):
    def authorised_get(self, name):
        chartType = self.get_argument("view", "BarChart")
        self.render("downloads.html", chartType = chartType)


def urls():
    return [
        (r"/dashboard/version", VersionPage),
        (r"/dashboard/dummy/([a-zA-Z]+)", DummyPage),
        (r"/dashboard/downloads", DownloadsPage),
        ]
