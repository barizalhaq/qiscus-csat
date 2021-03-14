from functools import wraps
from flask import request
from http import HTTPStatus
from config import SUPER_ADMIN_TOKEN


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
