"""Tracer code for setting up sqlalchemy."""
import argparse
import os

import requests

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('api_url', type=str, help='base URL to API host')
    args = parser.parse_args()

    login_data = {
        "email": "user@example.com",
        "password": "123456aoeu7890",
        "last_name": "last",
        "organization": "AnyCo",
        "first_name": "first"
    }
    r = requests.post(
        os.path.join(args.api_host, 'users', 'create', login_data))
    print(r)
    login_data = {
        "email": "user@example.com",
        "password": "123456aoeu7890",
    }
    r = requests.post(
        os.path.join(args.api_host, 'users', 'auth', login_data))
    print(r)
