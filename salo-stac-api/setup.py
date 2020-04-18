# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "openapi_server"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion>=2.0.2",
    "swagger-ui-bundle>=0.0.2",
    "python_dateutil>=2.6.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="The SpatioTemporal Asset Catalog API + Extensions",
    author_email="",
    url="",
    keywords=["OpenAPI", "The SpatioTemporal Asset Catalog API + Extensions"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['openapi/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['openapi_server=openapi_server.__main__:main']},
    long_description="""\
    This is an OpenAPI definition of the core SpatioTemporal Asset Catalog API specification. Any service that implements this endpoint to allow search of spatiotemporal assets can be considered a STAC API. The endpoint is also available as an OpenAPI fragment that can be integrated with other OpenAPI definitions, and is designed to slot seamlessly into a OGC API - Features definition.
    """
)

