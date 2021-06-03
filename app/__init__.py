"""
App init module.
"""

import time

from flask import Flask, g, request, render_template
from http import HTTPStatus
from werkzeug.exceptions import HTTPException
from .extensions import *
from .utils.logging import http_request_log
from werkzeug.middleware.proxy_fix import ProxyFix

from flask_cors import CORS

from flask_migrate import Migrate
migrate = Migrate(compare_type=True)


def create_app():
    """
    An application factory, as explained here:
    http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
    app.config.from_object('config')

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # create tables as per models
    with app.app_context():
        db.create_all()

    # register blueprints
    from .routes import api as api_bp
    from .routes import webhook as webhook_bp
    from .routes import web as web_bp
    from .v2.routes import v2 as v2_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(v2_bp)

    # before request func
    @app.before_request
    def before_request_func():
        g.start = time.time()

    # after request func
    @app.after_request
    def after_request_func(response):
        if hasattr(g, 'start'):
            http_request_log(flask_g=g, req=request, res=response)

        return response

    # error handler func
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(str(e))

        error_data = {}
        error_data["status"] = HTTPStatus.INTERNAL_SERVER_ERROR
        error_data["message"] = 'internal server error'

        if isinstance(e, HTTPException):
            error_data["status"] = e.code
            error_data["message"] = e.description

        return error_data, error_data["status"]

    # index route
    @app.route("/")
    def index():
        # return {
        #     "status": HTTPStatus.OK,
        #     "message": "qismo csat service up and running!"
        # }

        return render_template("index.html")

    return app
