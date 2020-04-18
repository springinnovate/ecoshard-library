"""Implementation of STAC API for Salo."""
import flask

APP = flask.Flask(__name__)

if __name__ == '__main__':
    # wait for API calls
    APP.config.update(SERVER_NAME=f'{args.external_ip}:{MANAGER_PORT}')
    APP.run(host='0.0.0.0', port=MANAGER_PORT)

    pass