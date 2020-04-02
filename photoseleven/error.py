"""Module to define application error codes."""
from flask import request, jsonify, make_response, current_app
from functools import wraps


class RESTfulErrors:
    ERR_REST_CONTENT_TYPE = 'ERR_REST_CONTENT_TYPE'
    ERR_REST_METHOD_NOT_SUPPORTED = 'ERR_REST_METHOD_NOT_SUPPORTED'


def only_json_content(view):
    """Decorator to help filter only application/json requests."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get('Content-Type', None) != 'application/json' and \
                request.headers.get('Content-Type', None) != 'application/json; charset=utf-8':
            return response_fail(RESTfulErrors.ERR_REST_CONTENT_TYPE, 415)
        else:
            data = request.get_json()
            return view(data, *args, **kwargs)

    return wrapper


def only_multimedia_content(view):
    """Decorator to help filter only multimedia requests."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get('Content-Type', None) not in current_app.config['ALLOWED_MEDIA_HEADERS']:
            return response_fail(RESTfulErrors.ERR_REST_CONTENT_TYPE, 415)
        else:
            return view(*args, **kwargs)

    return wrapper


def response_fail(err_code: str, http_status_code: int = 400):
    return make_response(jsonify({'success': False, 'err_code': err_code}), http_status_code)


def response_success(http_status_code: int = 200):
    return make_response(jsonify({'success': True}), http_status_code)
