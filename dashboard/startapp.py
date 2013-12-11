#!/usr/bin/env python3
"""

  Entry point for dashboard web services

  Run as a script, provide --port=NNNN to run the server,
  optionally --imports=XXX,YYY,ZZZ to include url handlers from modules XXX,YYY and ZZZ
"""

import logging
import os
import sys
import importlib

from tornado import ioloop, web

from tornado.options import define, options, parse_command_line

from tsumanga.aws import deploy
import tsumanga.ioloop

import dashboard.reports

# global command-line options
define("port", default=None, type=int) # port to serve the site on
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

def start_server():
    """ start the web server """
    logging.info("starting on port {0}".format(options.port))
    # make site configuration available in the Application settings
    config = deploy.get_server_config(options.config)
    modules = [dashboard.reports]
    if options.imports:
        extra_module_names = options.imports.split(',')
        for name in extra_module_names:
            try:
                mod = importlib.import_module(name)
                modules.append(mod)
                dashboard.reports.Version.register(name, mod.version)
            except (ImportError, AttributeError) as e:
                logging.warning("Unable to import '{}': {}".format(name, e))
    # when running stand-alone, provide /app/version
    urls = [(r"/app/version", dashboard.reports.Version)]
    for module in modules:
        urls += urls_from_module(module)
    app = web.Application(urls, config=config)
    # make IOLoop quieter about unimportant exceptions
    tsumanga.ioloop.quiet_patch()
    app.listen(options.port)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        return # no annoying traceback while testing

def main():
    """ unpack static files or run web server """
    parse_command_line()
    if options.config is None:
        options.config = deploy.get_server_name()
    start_server()

if __name__ == '__main__':
    main()
    

