"""
  Web Services for Distimo-based reports
"""

import logging
import hmac
import hashlib
import csv
from datetime import datetime
from collections import defaultdict

from tornado import httpclient, web
import tornado.options

from tsumanga.db import memcache
from tsumanga.webservice import WebServiceHandler, WebServiceError
from tsumanga.aws import deploy

DISTIMO_KEYS = ()

def log_response(response):
    """ dummy response callback """
    logging.info("Response %d from distimo after %dms", response.code, int(response.request_time * 1000))

def init():
    """ set up distimo keys """
    global DISTIMO_KEYS
    if DISTIMO_KEYS:
        return
    try:
        server = tornado.options.options.config
    except AttributeError:
        server = "local"
    config = deploy.get_server_config(server)
    distimo_keys = config.getlist("distimo_keys", "")
    if len(distimo_keys) != 4:
        logging.warning("distimo_keys in config should be private, public, username, base64auth ")
        raise WebServiceError(500, mesg="distimo not configured")
    DISTIMO_KEYS = tuple(distimo_keys)

def utc_time():
    """ seconds since epoch in UTC """
    return (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

def make_query_string(query_dict):
    """ make &-separated key-sorted query string """
    return "&".join("{0[0]}={0[1]}".format(p) for p in sorted(query_dict.items()))

def distimo_url(path, query):
    """ construct a URL for distimo REST API """
    if not DISTIMO_KEYS:
        init()
    private, public, user, base64auth = DISTIMO_KEYS
    if "format" not in query:
        query["format"] = "csv"
    query_string = make_query_string(query)
    query_time = int(utc_time())
    query_hash = hmac.new(private.encode('ascii'), 
                          (query_string + str(query_time)).encode('ascii'),
                          hashlib.sha1).hexdigest()
    url = ("https://analytics.distimo.com/api/v3/{0}?{1}&apikey={2}&hash={3}&t={4}"
           .format(path, query_string, public, query_hash, query_time))
    return url
    
def async_request(path, callback=None, cache_time=3600, **query):
    """ Make a request to distimo and return data as a list of lists """
    url = distimo_url(path, query)
    cachekey = path + "?" + make_query_string(query)
    if len(cachekey) > 250:
        cachekey = str(hash(cachekey))

    def parse_data(data):
        """ parse data and pass it back to the callback """
        array = []
        if data:
            array = list(csv.reader(line for line in data.split('\n') if line.strip()))
        if callback:
            callback(array)
            
    def got_cached(data):
        """ handle data from cache or cache miss """
        if data is None:
            get_data()
        else:
            parse_data(data)
        
    def get_data():
        """ get data from web service """
        req = httpclient.HTTPRequest(
            url,
            headers=dict(Authorization="Basic " + DISTIMO_KEYS[3]),
            method="GET",
            body=None)
        client = httpclient.AsyncHTTPClient()
        client.fetch(req, got_data)
        
    def got_data(response):
        if response.code == 200:
            data = response.body.decode('utf-8')
            memcache.set(cachekey, data, time=cache_time, callback=lambda x:parse_data(data))
        else:
            log_response(response)
            callback([])
    # first try to get cached data
    memcache.get(cachekey, got_cached)
    

def sync_request(path, **query):
    """ for testing - synchronous request using python stdlib instead of tornado """
    from urllib.request import Request, urlopen
    url = distimo_url(path, query)
    req = Request(url, method="GET", headers=dict(Authorization="Basic " + DISTIMO_KEYS[3]))
    array = []
    with urlopen(req) as rsp:
        data = rsp.read().decode('utf-8')
        if data:
            array = list(csv.reader(line for line in data.split("\n") if line.strip()))
    return array

def app_id_dicts_from_arrays(data_array):
    """ process rows of filters/assets/reviews
    returns {app_name:[app_id]}, {app_id:app_name} """
    app_to_id = defaultdict(list)
    id_to_app = {}
    if data_array:
        for row in data_array[1:]:
            appname = row[1].strip('"')
            if "(" in appname:
                before, paren, after = appname.partition("(")
                appname = before.strip()
            app_to_id[appname].append(row[0])
            id_to_app[row[0]] = appname
    return app_to_id, id_to_app

class ApplicationIDReport(WebServiceHandler):
    """
    Report that gets Application IDs from Distimo,
    so things can be meaningfully labelled in other reports.

    Returns an object with app names as keys, lists of app IDs as values
    """
    @web.asynchronous
    def get(self):
        """ get the application IDs """
        async_request("filters/assets/reviews", callback=self.got_asset_ids)

    def got_asset_ids(self, data_array):
        app_to_id, _ = app_id_dicts_from_arrays(data_array)
        self.json_response(app_to_id)

class DownloadsReport(WebServiceHandler):
    """
    Report that gets total downloads from Distimo,
    aggregating same app over all app stores.

    JSON response
    {array:[["Application","Downloads"],[data]...]}
    """
    @web.asynchronous
    def get(self):
        async_request("filters/assets/downloads", callback=self.got_asset_ids)

    def got_asset_ids(self, data_array):
        _, self.id_to_app = app_id_dicts_from_arrays(data_array)
        async_request("downloads", callback=self.got_downloads,
                      breakdown="application",
                      **{"from":"all"}) # from is a reserved word

    def got_downloads(self, data_array):
        """ construct response """
        totals = defaultdict(int)
        if data_array:
            row0 = data_array[0]
            try:
                appcol = row0.index("Application")
                valcol = row0.index("Value")
                for row in data_array[1:]:
                    appname = self.id_to_app.get(row[appcol], "Unknown")
                    totals[appname] += int(row[valcol])
            except ValueError:
                logging.error("Distimo API changed? downloads headings: {0}".format(row0))
        out = [["Application", "Downloads"]]
        for app, downloads in totals.items():
            out.append([app, downloads])
        self.json_response(dict(array=out))

def urls():
    return [
        (r'/app/dash/appids', ApplicationIDReport),
        (r'/app/dash/downloads', DownloadsReport),
        ]
