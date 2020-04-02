import datetime
from flask import Blueprint, request, current_app, jsonify, make_response, g
from functools import wraps
import jwt
import os
from photoseleven.db import get_db
from photoseleven.error import only_json_content, response_fail, response_success
import re
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


class AuthErrors:
    ERR_AUTH_NO_USERNAME = 'ERR_AUTH_NO_USERNAME'
    ERR_AUTH_NO_PASSWORD = 'ERR_AUTH_NO_PASSWORD'
    ERR_AUTH_NO_NEW_PASSWORD = 'ERR_AUTH_NO_NEW_PASSWORD'
    ERR_AUTH_WRONG_PASSWORD = 'ERR_AUTH_WRONG_PASSWORD'
    ERR_AUTH_USER_EXISTS = 'ERR_AUTH_USER_EXISTS'
    ERR_AUTH_USER_NOT_EXIST = 'ERR_AUTH_USER_NOT_EXIST'
    ERR_AUTH_SAME_NEW_PASS = 'ERR_AUTH_SAME_NEW_PASS'
    ERR_AUTH_NO_AUTH_HEADER = 'ERR_AUTH_NO_AUTH_HEADER'
    ERR_AUTH_TOKEN_EXPIRED = 'ERR_AUTH_TOKEN_EXPIRED'
    ERR_AUTH_TOKEN_INVALID = 'ERR_AUTH_TOKEN_INVALID'


@bp.route('/users', methods=('POST', 'PUT', 'DELETE'))
@only_json_content
def users_manipulation(data):
    """To manipulate registered users in the database.
    POST  : register new user
    PUT   : update user password
    DELETE: delete registered user"""
    if not data['username']:
        return response_fail(AuthErrors.ERR_AUTH_NO_USERNAME, 401)

    if not data['password']:
        return response_fail(AuthErrors.ERR_AUTH_NO_PASSWORD, 401)

    db = get_db()

    # Processing POST
    if request.method == 'POST':
        if db.users.find_one({'username': data['username']}) is not None:
            return response_fail(AuthErrors.ERR_AUTH_USER_EXISTS, 401)

        db.users.insert_one({'username': data['username'], 'password': generate_password_hash(data['password'])})
        return response_success(201)

    # Processing PUT
    if request.method == 'PUT':
        if not data['new_password']:
            return response_fail(AuthErrors.ERR_AUTH_NO_NEW_PASSWORD, 412)

        user = db.users.find_one({'username': data['username']})
        if user is None:
            return response_fail(AuthErrors.ERR_AUTH_USER_NOT_EXIST, 401)

        if not check_password_hash(user['password'], data['password']):
            return response_fail(AuthErrors.ERR_AUTH_WRONG_PASSWORD, 401)

        if check_password_hash(user['password'], data['new_password']):
            return response_fail(AuthErrors.ERR_AUTH_SAME_NEW_PASS, 412)

        res = db.users.update_one({'_id': user['_id']},
                                  {'$set': {'password': generate_password_hash(data['new_password'])}},
                                  upsert=False)
        assert res.modified_count == 1

        return response_success(200)

    # Processing DELETE
    else:
        user = db.users.find_one({'username': data['username']})
        if user is None:
            return response_fail(AuthErrors.ERR_AUTH_USER_NOT_EXIST, 401)

        if not check_password_hash(user['password'], data['password']):
            return response_fail(AuthErrors.ERR_AUTH_WRONG_PASSWORD, 401)

        res = db.users.delete_one({'_id': user['_id']})
        assert res.deleted_count == 1

        return response_success(200)


@bp.route('/login', methods=['POST'])
@only_json_content
def login(data):
    """To login the user and get back a token"""
    if not data['username']:
        return response_fail(AuthErrors.ERR_AUTH_NO_USERNAME, 401)

    if not data['password']:
        return response_fail(AuthErrors.ERR_AUTH_NO_PASSWORD, 401)

    db = get_db()
    user = db.users.find_one({'username': data['username']})
    if user is None:
        return response_fail(AuthErrors.ERR_AUTH_USER_NOT_EXIST, 401)

    if not check_password_hash(user['password'], data['password']):
        return response_fail(AuthErrors.ERR_AUTH_WRONG_PASSWORD, 401)

    token = jwt.encode({'username': user['username'],
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(
                            days=current_app.config['TOKEN_EXPIRATION_DAYS'])},
                       current_app.config['SECRET_KEY'],
                       algorithm='HS256')

    return make_response(jsonify({'success': True, 'token': token.decode('UTF-8')}), 200)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        bearer_jwt = request.headers.get('Authorization')
        if bearer_jwt is None:
            return response_fail(AuthErrors.ERR_AUTH_NO_AUTH_HEADER, 401)

        match = re.fullmatch(r'Bearer ([a-zA-Z0-9-_.]+\.[a-zA-Z0-9-_.]+\.[a-zA-Z0-9-_.]+)', bearer_jwt)
        if match is not None:
            token = match[1]
        else:
            return response_fail(AuthErrors.ERR_AUTH_NO_AUTH_HEADER, 401)

        assert token is not None

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms='HS256')
        except jwt.ExpiredSignatureError:
            return response_fail(AuthErrors.ERR_AUTH_TOKEN_EXPIRED, 401)
        except jwt.InvalidTokenError:
            return response_fail(AuthErrors.ERR_AUTH_TOKEN_INVALID, 401)

        assert data is not None

        if not data.get('username', None):
            return response_fail(AuthErrors.ERR_AUTH_NO_USERNAME, 401)

        user = get_db().users.find_one({'username': data['username']})
        if user is None:
            return response_fail(AuthErrors.ERR_AUTH_USER_NOT_EXIST, 401)

        g.user = user
        return view(*args, **kwargs)

    return wrapped


@bp.route('/login_ping', methods=['GET'])
@login_required
def login_ping():
    return make_response(jsonify({'username': g.user['username']}), 200)
