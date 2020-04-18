# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.catalog_definition import CatalogDefinition  # noqa: E501
from openapi_server.models.collections import Collections  # noqa: E501
from openapi_server.test import BaseTestCase


class TestVersionExtensionController(BaseTestCase):
    """VersionExtensionController integration test stubs"""

    def test_collections_collection_id_items_feature_id_versions_get(self):
        """Test case for collections_collection_id_items_feature_id_versions_get

        returns a list of links for a versioned item
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/items/{feature_id}/versions'.format(collection_id='collection_id_example', feature_id='feature_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_collections_collection_id_items_feature_id_versions_version_id_get(self):
        """Test case for collections_collection_id_items_feature_id_versions_version_id_get

        returns the requested version of an item
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/items/{feature_id}/versions/{version_id}'.format(collection_id='collection_id_example', feature_id='feature_id_example', version_id='version_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_collections_collection_id_versions_get(self):
        """Test case for collections_collection_id_versions_get

        returns a list of links for a versioned collection
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/versions'.format(collection_id='collection_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_collections_collection_id_versions_version_id_get(self):
        """Test case for collections_collection_id_versions_version_id_get

        returns the requested version of a collection
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/versions/{version_id}'.format(collection_id='collection_id_example', version_id='version_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
