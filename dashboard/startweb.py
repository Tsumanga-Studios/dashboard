#!/usr/bin/env python3
"""
 Entry point for Reporting Dashboard
 run as a script, provide --port=NNNN to run the server,
 or "unpack" to unpack static files.
"""

import logging
import os
import sys
import subprocess
import importlib

from tornado import web, locale, ioloop
from tornado.options import define, options, parse_command_line

import tsumanga.utils
from tsumanga.aws import deploy
import tsumanga.ioloop

import dashboard.pages, dashboard.ui_modules

# global command-line options
define("port", default=None, type=int) # port to serve the site on
define("static", default="/var/deploy/www/static") # location of static files
define("config", default=None) # server name for deployment configuration
define("imports", default=None) # other modules to import

# get location of this module in filesystem
HERE = os.path.split(__file__)[0]

def urls_from_module(module):
    """ get list of (url, handler) from an imported module """
    urls = []
    try:
        urls = module.urls()
    except Exception as e:
        logging.error("No urls from {0}: {1}".format(module.__name__, e))
    return urls

class SafeStaticHandler(web.StaticFileHandler):
    def decode_argument(self,value,name=None):
        try:
            return super().decode_argument(value,name)
        except UnicodeDecodeError:
            return ""
    def finish(self, chunk=None):
        """ avoid pointless errors in log about closed streams """
        try:
            super().finish(chunk)
        except IOError as e:
            logging.warning("IOError trying to finish {0}".format(self.request.uri))

def start_server():
    """ start the web server """
    logging.info("starting on port {0}".format(options.port))
    if options.static == "here":
        static_path = os.path.join(HERE, "static")
    else:
        static_path = options.static
    template_path = os.path.join(HERE, "templates")
    logging.info("templates are in {0}".format(template_path))
    # make site configuration available in the Application settings
    config = deploy.get_server_config(options.config)
    modules = [dashboard.pages]
    if options.imports:
        extra_module_names = options.imports.split(',')
        for name in extra_module_names:
            try:
                modules.append(importlib.import_module(name))
            except ImportError:
                logging.warning("can't import {0}".format(name))
                pass
    urls = []
    for module in modules:
        urls += urls_from_module(module)
    app = web.Application(
        urls,
        template_path=template_path,
        static_path=static_path,
        static_handler_class=SafeStaticHandler,
        cookie_secret=b'htmlasagne',
        config=config,
        ui_modules=dashboard.ui_modules,
        gzip=True)

    # make IOLoop quieter about unimportant exceptions
    tsumanga.ioloop.quiet_patch()

    # run on chosen port
    app.listen(options.port, xheaders=True)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        return # no annoying traceback while testing

def unpack_files():
    """ put static files where webserver will find them """
    logging.info("unpacking static files")
    static_dest = options.static
    static_src = os.path.join(HERE, "static/")
    rsync = subprocess.Popen(["rsync", "-a", "--delete",
                              static_src, static_dest],
                             stderr=subprocess.PIPE)
    _, stderr = rsync.communicate()
    logging.info(str(stderr, "utf-8"))

def main():
    """ unpack static files or run web server """
    args = parse_command_line()
    logname = __file__.replace("/",".")
    if "unpack" in args:
        tsumanga.utils.set_up_logging(logname + ".log")
        unpack_files()
    elif options.port:
        if options.config is None:
            options.config = deploy.get_server_name()
        start_server()

if __name__ == '__main__':
    main()

