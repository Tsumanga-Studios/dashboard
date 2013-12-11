import os
from distutils.core import setup

# also update version in __init__.py
version = '0.0.0'

if __name__ == '__main__':
    setup(
        name="dashboard",
        version=version,
        keywords=["web"],
        long_description=open(os.path.join(os.path.dirname(__file__),"README.md"), "r").read(),
        description="Tsumanga Studios Reporting Dashboard",
        author="Peter Harris",
        author_email="peter@tsumanga.com",
        url="http://github.com/Tsumanga-Studios/dashboard",
        packages=['dashboard'],
        package_data={"dashboard":["templates/*.html",
                                   "static/favicon.ico",
                                   "static/img/*",
                                   "static/js/*",
                                   "static/css/*"]},
        package_data={},
        install_requires=[],
        requires=[],
    )
