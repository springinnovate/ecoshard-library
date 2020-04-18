# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.item import Item  # noqa: E501
from openapi_server.models.one_ofitemitem_collection import OneOfitemitemCollection  # noqa: E501
from openapi_server.models.partial_item import PartialItem  # noqa: E501
from openapi_server.models.unknownbasetype import UNKNOWN_BASE_TYPE  # noqa: E501
from openapi_server.test import BaseTestCase


class TestTransactionExtensionController(BaseTestCase):
    """TransactionExtensionController integration test stubs"""

    def test_delete_feature(self):
        """Test case for delete_feature

        delete an existing feature by Id
        """
        headers = { 
            'Accept': 'application/json',
            'if_match': 'if_match_example',
        }
        response = self.client.open(
            '/collections/{collection_id}/items/{feature_id}'.format(collection_id='collection_id_example', feature_id='feature_id_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_patch_feature(self):
        """Test case for patch_feature

        update an existing feature by Id with a partial item definition
        """
        partial_item = {}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'if_match': 'if_match_example',
        }
        response = self.client.open(
            '/collections/{collection_id}/items/{feature_id}'.format(collection_id='collection_id_example', feature_id='feature_id_example'),
            method='PATCH',
            headers=headers,
            data=json.dumps(partial_item),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_post_feature(self):
        """Test case for post_feature

        add a new feature to a collection
        """
        unknown_base_type = {}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/collections/{collection_id}/items'.format(collection_id='collection_id_example'),
            method='POST',
            headers=headers,
            data=json.dumps(unknown_base_type),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_put_feature(self):
        """Test case for put_feature

        update an existing feature by Id with a complete item definition
        """
        item = {}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'if_match': 'if_match_example',
        }
        response = self.client.open(
            '/collections/{collection_id}/items/{feature_id}'.format(collection_id='collection_id_example', feature_id='feature_id_example'),
            method='PUT',
            headers=headers,
            data=json.dumps(item),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
