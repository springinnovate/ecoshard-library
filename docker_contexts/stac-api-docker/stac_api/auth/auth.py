from functools import wraps
import re
import logging

from flask import Blueprint, current_app, jsonify, request, g

from . import models, queries, services, utils

auth_bp = Blueprint("auth", __name__)


def jwt_required(alternate_parameter=None):
    """ Decorator to require a valid JWT token to access an endpoint.

    Adds g.user and g.jwt on success.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if alternate_parameter is not None and alternate_parameter in request.args:
                return view(*args, **kwargs)

            if "Authorization" not in request.headers:
                utils.log("no authorization header", logging.WARN)
                return {}, 401
            if not request.headers["Authorization"].startswith("Bearer "):
                utils.log("authorization header not a bearer type", logging.WARN)
                return {}, 401

            matches = re.match(r"^Bearer (\S+)$", request.headers["Authorization"])
            if not matches:
                utils.log("invalid bearer token format", logging.WARN)
                return {}, 401

            g.jwt = utils.decode_jwt(matches.group(1))
            if not g.jwt:
                utils.log("unable to decode JWT", logging.WARN)
                return {}, 401

            g.user = queries.find_user_by_id(g.jwt["id"])
            if not g.user:
                utils.log("no such user", logging.WARN)
                return {}, 401

            if not utils.verify_jwt(g.user, matches.group(1)):
                utils.log("invalid JWT token", logging.WARN)
                return {}, 401

            return view(*args, **kwargs)

        return wrapper

    return decorator


def verify_content_type_and_params(required_keys, optional_keys):
    """ Decorator enforcing content type and body keys in an endpoint. """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if request.headers.get("Content-Type", None) != "application/json":
                utils.log("invalid content type", logging.WARN)
                return {}, 400

            request_keys = set(request.json.keys())
            required_set = set(required_keys)
            optional_set = set(optional_keys)
            if not required_set <= request_keys:
                utils.log(
                    f"create: invalid payload keys {list(request.json.keys())}",
                    logging.WARN,
                )
                return {}, 400
            if len(request_keys - required_set.union(optional_set)) > 0:
                utils.log("unknown key passed to request", logging.WARN)
                return {}, 400

            return view(*args, **kwargs)

        return wrapper

    return decorator


@auth_bp.route("/create", methods=["POST"])
@verify_content_type_and_params(
    ["email", "password", "first_name", "last_name"], ["organization"]
)
def create_user():
    """Create a user.
    ---

    requestBody:
      description: "An email, password, and name of user."
      required: true
      content:
        application/json:
          schema:
            type: "object"
            required:
              - email
              - password
              - first_name
              - last_name
            properties:
              email:
                type: "string"
                format: email
              password:
                type: "string"
              first_name:
                type: "string"
              last_name:
                type: "string"
              organization:
                type: "string"
    responses:
      "200":
        description: "Created"
        content:
          application/json:
            schema:
              type: object
              properties:
                uuid:
                  type: string
                email:
                  type: string
                  format: email
                token:
                  type: string
                  format: JWT
      "400":
        description: "Bad request"
      "401":
        description: "Invalid input"
    """
    email = request.json["email"]
    password = request.json["password"]
    first_name = request.json["first_name"]
    last_name = request.json["last_name"]
    organization = None
    if "organization" in request.json.keys():
        organization = request.json["organization"]
    if queries.find_user_by_email(email):
        utils.log("create: user exists", logging.WARN)
        return {}, 400

    try:
        user = services.create_user(
            email, password, first_name, last_name, organization
        )
        models.db.session.commit()
        g.user = user

        utils.log("user created")

        return jsonify(
            uuid=user.uuid,
            email=user.email,
            token=utils.make_jwt(user).decode("utf-8"),
        )
    except ValueError as value_error:
        utils.log(f"could not create user: {value_error}", logging.WARN)
        return {}, 400


@auth_bp.route("/auth", methods=["POST"])
@verify_content_type_and_params(["email", "password"], [])
def auth_user():
    """Authenticate a user.
    ---

    requestBody:
      description: "An email and password."
      required: true
      content:
        application/json:
          schema:
            type: "object"
            required:
              - email
              - password
            properties:
              email:
                type: "string"
                format: email
              password:
                type: "string"
    responses:
      "200":
        description: "Created"
        content:
          application/json:
            schema:
              type: object
              properties:
                uuid:
                  type: string
                email:
                  type: string
                  format: email
                token:
                  type: string
                  format: JWT
      "400":
        description: "Bad request"
      "401":
        description: "Invalid input"
    """
    email = request.json["email"]
    password = request.json["password"]
    user = queries.find_user_by_email(email)
    if user is None:
        utils.log("user does not exist", logging.WARN)
        return {}, 401

    if not utils.verify_hash(password, user.password_hash, user.password_salt):
        utils.log("verify hash failed", logging.WARN)
        return {}, 401

    utils.log("authorized user")
    return jsonify(
        uuid=user.uuid, email=user.email, token=utils.make_jwt(user).decode("utf-8"),
    )


@auth_bp.route("/auth/refresh", methods=["POST"])
@jwt_required()
def refresh():
    """ Refresh a JWT token.
    ---

    securitySchemes:
      bearerAuth:
        type: http
        scheme: bearer
        bearerFormat: JWT
    security:
      - bearerAuth: []
    responses:
      "200":
        description: "Created"
        content:
          application/json:
            schema:
              type: object
              properties:
                token:
                  type: string
                  format: JWT
      "400":
        description: "Bad request"
      "401":
        description: "Invalid input"
    """
    if request.headers.get("Content-Type", None) != "application/json":
        utils.log("invalid content type", logging.WARN)
        return {}, 400

    utils.log("token refreshed")
    return jsonify(
        token=utils.make_jwt(g.user, utils.to_datetime(g.jwt["max-exp"])).decode(
            "utf-8"
        )
    )


@auth_bp.route("/auth/reset", methods=["POST"])
@verify_content_type_and_params(["email"], [])
def reset():
    """ Send user a password reset email.
    ---

    requestBody:
      description: "An email."
      required: true
      content:
        application/json:
          schema:
            type: "object"
            required:
              - email
            properties:
              email:
                type: "string"
                format: email
    responses:
      "204":
        description: "Created"
      "400":
        description: "Bad request"
    """
    email = request.json["email"]
    user = queries.find_user_by_email(email)
    if not user:
        utils.log("reset: user does not exist", logging.WARN)
        return {}, 400

    if not services.request_password_reset(user):
        utils.log("reset: unable to send request_password_reset", logging.WARN)
        return {}, 400

    utils.log("reset_token sent")
    return {}, 204


@auth_bp.route("/auth/update-password", methods=["PUT"])
@verify_content_type_and_params(["email", "reset_token", "password"], [])
def update_password():
    """ Update a user's password.
    ---

    requestBody:
      description: "An email, new password, and reset_token."
      required: true
      content:
        application/json:
          schema:
            type: "object"
            required:
              - email
              - password
              - reset_token
            properties:
              email:
                type: "string"
                format: email
              password:
                type: "string"
              reset_token:
                type: "string"
    responses:
      "200":
        description: "Updated"
        content:
          application/json:
            schema:
              type: object
              properties:
                uuid:
                  type: string
                email:
                  type: string
                  format: email
                token:
                  type: string
                  format: JWT
      "400":
        description: "Bad request"
    """
    email = request.json["email"]
    password = request.json["password"]
    reset_token = request.json["reset_token"]
    user = queries.find_user_by_email(email)
    if not user:
        utils.log("update_password: user does not exist", logging.WARN)
        return {}, 400

    try:
        services.update_password(user, password, reset_token)
        utils.log("update_password: updated password")
        return jsonify(
            uuid=user.uuid,
            email=user.email,
            token=utils.make_jwt(user).decode("utf-8"),
        )
    except ValueError as value_error:
        utils.log(value_error, logging.ERROR)
        return {}, 400


@auth_bp.errorhandler(500)
def handle_error(e):
    utils.log(f"unspecified error: {e}")
    return {}, 500
