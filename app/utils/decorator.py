import os
from functools import wraps
from flask import request
from http import HTTPStatus
from config import SUPER_ADMIN_TOKEN
import jwt
from ..models import App


def superadmin_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != SUPER_ADMIN_TOKEN:
            return {
                "status": HTTPStatus.UNAUTHORIZED,
                "message": "Unauthorized"
            }

        return f(*args, **kwargs)
    return decorated


def authenticated_app(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        try:
            decoded = jwt.decode(token, key=os.getenv('CSAT_ADD_ON_SIGNATURE_KEY'), algorithms='HS256')
            app_code = decoded.get('app_code')
            app = App.get_by_code(app_code)

            if app is None:
                return {
                    'message': 'Unauthorized'
                }, HTTPStatus.UNAUTHORIZED
        except:
            return {
                'message': 'Invalid token!'
            }, HTTPStatus.UNAUTHORIZED

        return f(app, *args, **kwargs)

    return decorated


def marketplace_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        try:
            decoded = jwt.decode(token, key=os.getenv('CSAT_ADD_ON_SIGNATURE_KEY'), algorithms='HS256')
            app_code = decoded.get('app_code')
            if app_code != request.json["app_code"]:
                return {
                    'message': 'Invalid token!'
                }, HTTPStatus.UNAUTHORIZED
        except:
            return {
                'message': 'Invalid token!'
            }, HTTPStatus.UNAUTHORIZED

        return f(*args, **kwargs)

    return decorated
