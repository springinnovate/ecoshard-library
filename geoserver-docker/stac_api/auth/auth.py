from functools import wraps
import re

from flask import Blueprint, current_app, jsonify, request, g

from . import models, queries, services, utils

auth_bp = Blueprint("auth", __name__)


def jwt_required(view):
    """ Decorator to require a valid JWT token to access an endpoint.

    Adds g.jwt_user and g.jwt on success.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        if "Authorization" not in request.headers:
            current_app.logger.info("no authorization header")
            return {}, 401
        if not request.headers["Authorization"].startswith("Bearer "):
            current_app.logger.info("authorization header not a bearer type")
            return {}, 401

        matches = re.match(r"^Bearer (\S+)$", request.headers["Authorization"])
        if not matches:
            current_app.logger.info("invalid bearer token format")
            return {}, 401

        g.jwt = utils.decode_jwt(matches.group(1))
        if not g.jwt:
            current_app.logger.info("unable to decode JWT")
            return {}, 401

        g.jwt_user = queries.find_user_by_id(g.jwt["id"])
        if not g.jwt_user:
            current_app.logger.info("no such user")
            return {}, 401

        if not utils.verify_jwt(g.jwt_user, matches.group(1)):
            current_app.logger.info("invalid JWT token")
            return {}, 401

        return view(*args, **kwargs)

    return wrapper


def verify_content_type_and_params(required_keys, optional_keys):
    """ Decorator enforcing content type and body keys in an endpoint. """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if request.headers.get("Content-Type", None) != "application/json":
                current_app.logger.info("invalid content type")
                return {}, 400

            request_keys = set(request.json.keys())
            required_set = set(required_keys)
            optional_set = set(optional_keys)
            if not required_set <= request_keys:
                current_app.logger.info(
                    f"create: invalid payload keys {list(request.json.keys())}"
                )
                return {}, 400
            if len(request_keys - required_set.union(optional_set)) > 0:
                current_app.logger.info("unknown key passed to request")
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
                id:
                  type: integer
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
        current_app.logger.info("create: user exists")
        return {}, 400

    try:
        user = services.create_user(
            email, password, first_name, last_name, organization
        )
        models.db.session.commit()

        return jsonify(
            id=user.id, email=user.email, token=utils.make_jwt(user).decode("utf-8"),
        )
    except ValueError as value_error:
        current_app.logger.info(f"create: {value_error}")
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
                id:
                  type: integer
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
        current_app.logger.info("auth: user does not exist")
        return {}, 401

    if not utils.verify_hash(password, user.password_hash, user.password_salt):
        current_app.logger.info("auth: verify hash failed")
        return {}, 401

    return jsonify(
        id=user.id, email=user.email, token=utils.make_jwt(user).decode("utf-8"),
    )


@auth_bp.route("/auth/refresh", methods=["POST"])
@jwt_required
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
        current_app.logger.info("invalid content type")
        return {}, 400

    return jsonify(
        token=utils.make_jwt(g.jwt_user, utils.to_datetime(g.jwt["max-exp"])).decode(
            "utf-8"
        )
    )
