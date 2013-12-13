"""
  Web Services for Distimo-based reports
"""

import logging
import hmac
import hashlib
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
        query["format"] = "scsv" # semicolon-separated values
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
            array = [line.split(";") for line in data.split("\n") if line]
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
            array = [line.split(";") for line in data.split("\n") if line]
    return array

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
        apps = defaultdict(list)
        if data_array:
            for row in data_array[1:]:
                appname = row[1].strip('"')
                if appname.startswith("Winx Sirenix Power"):
                    appname = "Winx Sirenix Power" # samsung store messes up name
                apps[appname].append(row[0])
        self.json_response(apps)

def urls():
    return [
        (r'/app/dash/appids', ApplicationIDReport)
        ]
