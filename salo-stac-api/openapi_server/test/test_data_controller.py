# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.feature_collection_geo_json import FeatureCollectionGeoJSON  # noqa: E501
from openapi_server.models.item import Item  # noqa: E501
from openapi_server.test import BaseTestCase


class TestDataController(BaseTestCase):
    """DataController integration test stubs"""

    def test_get_feature(self):
        """Test case for get_feature

        fetch a single feature
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/items/{feature_id}'.format(collection_id='collection_id_example', feature_id='feature_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_features(self):
        """Test case for get_features

        fetch features
        """
        query_string = [('limit', 10),
                        ('bbox', 3.4),
                        ('datetime', 'datetime_example')]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/items'.format(collection_id='collection_id_example'),
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
