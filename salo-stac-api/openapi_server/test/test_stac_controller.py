# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.item_collection import ItemCollection  # noqa: E501
from openapi_server.models.search_body import SearchBody  # noqa: E501
from openapi_server.test import BaseTestCase


class TestSTACController(BaseTestCase):
    """STACController integration test stubs"""

    def test_get_search_stac(self):
        """Test case for get_search_stac

        Search STAC items with simple filtering.
        """
        query_string = [('bbox', 3.4),
                        ('datetime', 'datetime_example'),
                        ('limit', 10),
                        ('ids', 'ids_example'),
                        ('collections', 'collections_example'),
                        ('query', 'query_example'),
                        ('sortby', +id,-properties.eo:cloud_cover),
                        ('fields', id,type,-geometry,bbox,properties,-links,-assets)]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/search',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_post_search_stac(self):
        """Test case for post_search_stac

        Search STAC items with full-featured filtering.
        """
        search_body = {}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/search',
            method='POST',
            headers=headers,
            data=json.dumps(search_body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
