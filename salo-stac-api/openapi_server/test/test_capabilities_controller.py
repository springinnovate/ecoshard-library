# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.collection import Collection  # noqa: E501
from openapi_server.models.collections import Collections  # noqa: E501
from openapi_server.models.conf_classes import ConfClasses  # noqa: E501
from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.landing_page import LandingPage  # noqa: E501
from openapi_server.test import BaseTestCase


class TestCapabilitiesController(BaseTestCase):
    """CapabilitiesController integration test stubs"""

    def test_describe_collection(self):
        """Test case for describe_collection

        describe the feature collection with id `collectionId`
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}'.format(collection_id='collection_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_collections(self):
        """Test case for get_collections

        the feature collections in the dataset
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_conformance_declaration(self):
        """Test case for get_conformance_declaration

        information about specifications that this API conforms to
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/conformance',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_landing_page(self):
        """Test case for get_landing_page

        landing page
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
