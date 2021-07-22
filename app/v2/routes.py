import datetime
import json
import os

import jwt
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from ..serializers import attach_app_schema, config_app_schema
from http import HTTPStatus
from ..libs.multichannel import Multichannel
from ..models import App, RatingType, Config
from sqlalchemy.exc import SQLAlchemyError
from ..extensions import db
from ..utils.decorator import authenticated_app, marketplace_token
from botocore.exceptions import ClientError
from ..extensions import s3_session
from ..utils.helpers import create_s3_url

v2 = Blueprint('v2', __name__, url_prefix="/api/v2")


@v2.route('/app/attach', methods=["POST"])
@marketplace_token
def attach_app():
    json_input = request.get_json(force=True)
    try:
        inputs = attach_app_schema.load(json_input)
    except ValidationError as err:
        return {
            'status': HTTPStatus.UNPROCESSABLE_ENTITY,
            'message': 'validation error',
            'errors': err.messages
        }, HTTPStatus.UNPROCESSABLE_ENTITY

    if App.get_by_code(app_code=inputs['app_code']):
        return {
            'status': HTTPStatus.UNPROCESSABLE_ENTITY,
            'message': 'app code already registered',
        }, HTTPStatus.UNPROCESSABLE_ENTITY

    try:
        app = App(
            app_code=inputs['app_code'],
            app_name=inputs['app_name'],
            admin_email=inputs['admin_email'],
            admin_token=inputs['admin_token']
        )

        db.session.add(app)
        db.session.commit()
    except SQLAlchemyError as err:
        db.session.rollback()
        raise err

    return {
        'status': HTTPStatus.OK,
        'message': 'Multichannel registered successfully',
    }, HTTPStatus.OK


@v2.route('/app', methods=["GET"])
@authenticated_app
def get_app(app):
    protocol = 'https://' if request.is_secure else 'http://'
    host = request.host.split(':', 1)[0]
    token = jwt.encode({ 'app_code': app.app_code }, key=os.getenv('CSAT_ADD_ON_SIGNATURE_KEY'), algorithm='HS256')
    data = {
        'official_web': app.config.official_web,
        'csat_msg': app.config.csat_msg,
        'rating_total': app.config.rating_total,
        'extras': app.config.extras,
        'csat_page': app.config.csat_page,
        'rating_type': app.config.rating_type.name,
        'preview_url': '{}{}/{}/preview'.format(protocol, host, token)
    }

    extras = json.loads(app.config.extras)
    if 'media' in extras:
        data['media_url'] = {}
        if 'logo' in extras['media']:
            data['media_url']['logo'] = create_s3_url(s3_session, f"add_on-csat-{app.app_code}_logo.{extras['media']['logo']['extension']}")
        if 'background' in extras['media']:
            data['media_url']['background'] = create_s3_url(s3_session, f"add_on-csat-{app.app_code}_background.{extras['media']['background']['extension']}")

    return jsonify({'data': data})


@v2.route('/app/create-config', methods=["POST"])
@authenticated_app
def create_app_config(app):
    if app.config is not None:
        return update_app_config(app)

    json_input = request.get_json(force=True)
    try:
        inputs = config_app_schema.load(json_input)
    except ValidationError as err:
        return {
            'status': HTTPStatus.UNPROCESSABLE_ENTITY,
            'message': 'validation error',
            'errors': err.messages
        }, HTTPStatus.UNPROCESSABLE_ENTITY

    protocol = 'https://' if request.is_secure else 'http://'
    host = request.host.split(':', 1)[0]
    base = '{}{}'.format(protocol, host)
    webhook_url = '{base}/webhook/csat/{app_code}'.format(
        base=base,
        app_code=app.app_code)

    set_resolve_webhook(app, webhook_url)

    if inputs['rating_type'] == 'emoji' and 'emoji_type' in inputs:
        inputs['extras']['emoji_type'] = inputs['emoji_type']
    rating_type = RatingType.STAR if inputs['rating_type'] == 'star' else RatingType.NUMBER if inputs['rating_type'] == 'number' else RatingType.CUSTOM if inputs['rating_type'] == 'custom' else RatingType.EMOJI  # noqa
    official_web = inputs['official_web'] if 'official_web' in inputs else None
    extras = json.dumps(inputs['extras']) if 'extras' in inputs else None
    rating_total = inputs['rating_total']
    if rating_type == RatingType.NUMBER and rating_total > 10:
        rating_total = 10
    elif rating_type == RatingType.STAR and rating_total > 5:
        rating_total = 5
    elif rating_type == RatingType.EMOJI:
        rating_total = 2

    try:
        config = Config(
            official_web=official_web,
            csat_msg=inputs['csat_msg'],
            rating_type=rating_type,
            rating_total=rating_total,
            extras=extras,
            app_id=app.id,
            csat_page=inputs['csat_page'])

        db.session.add(config)
        db.session.commit()

    except SQLAlchemyError as err:
        db.session.rollback()
        raise err

    return {
        'status': HTTPStatus.OK,
        'message': 'csat has been configured successfully',
    }, HTTPStatus.OK


def update_app_config(app):
    json_input = request.get_json(force=True)
    try:
        inputs = config_app_schema.load(json_input)
        existing_extras = json.loads(app.config.extras)

        if 'media' in existing_extras:
            inputs["extras"]["media"] = existing_extras["media"]
    except ValidationError as err:
        return {
           'status': HTTPStatus.UNPROCESSABLE_ENTITY,
           'message': 'validation error',
           'errors': err.messages
       }, HTTPStatus.UNPROCESSABLE_ENTITY

    if app.config.rating_type == RatingType.EMOJI and 'emoji_type' in inputs:
        inputs['extras']['emoji_type'] = inputs['emoji_type']

    rating_type = RatingType.STAR if inputs['rating_type'] == 'star' else RatingType.NUMBER if inputs['rating_type'] == 'number' else RatingType.CUSTOM if inputs['rating_type'] == 'custom' else RatingType.EMOJI  # noqa
    official_web = inputs['official_web'] if 'official_web' in inputs else None
    extras = json.dumps(inputs['extras']) if 'extras' in inputs else None
    rating_total = inputs['rating_total']
    if rating_type == RatingType.NUMBER and rating_total > 10:
        rating_total = 10
    elif rating_type == RatingType.STAR and rating_total > 5:
        rating_total = 5
    elif rating_type == RatingType.EMOJI:
        rating_total = 2

    app.config.rating_total = rating_total
    app.config.extras = extras
    app.config.official_web = official_web

    app.update()

    return {
       'status': HTTPStatus.OK,
       'message': 'csat has been updated successfully',
    }, HTTPStatus.OK


@v2.route('/app/upload-background', methods=['PUT'])
@authenticated_app
def upload_background(app):
    request_file = request.files['file']

    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(os.environ.get("S3_BUCKET"))

    try:
        splitted = request_file.filename.split(".")
        extension = request_file.filename.split(".")[len(splitted) - 1]
        bucket.Object(f"add_on-csat-{app.app_code}_background.{extension}").put(Body=request_file)
    except ClientError:
        return {
            'message': 'upload error',
            'status': HTTPStatus.UNPROCESSABLE_ENTITY
        }, HTTPStatus.UNPROCESSABLE_ENTITY

    config_extras = json.loads(app.config.extras)
    if 'media' not in config_extras:
        config_extras["media"] = {}
    config_extras["media"]["background"] = {
        "filename": request_file.filename,
        "mimetype": request_file.content_type,
        "size": len(request_file.read()),
        "uploaded_at": (datetime.datetime.now()).strftime("%d-%m-%Y %H:%M:%S"),
        "extension": extension,
        "key": f"add_on-csat-{app.app_code}_background.{extension}"
    }

    app.config.extras = json.dumps(config_extras)
    app.update()

    return {
        'message': 'background image has been uploaded successfully',
        'status': HTTPStatus.OK
    }, HTTPStatus.OK


@v2.route('/app/upload-logo', methods=['PUT'])
@authenticated_app
def upload_logo(app):
    request_file = request.files['file']

    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(os.environ.get("S3_BUCKET"))

    try:
        splitted = request_file.filename.split(".")
        extension = request_file.filename.split(".")[len(splitted) - 1]
        bucket.Object(f"add_on-csat-{app.app_code}_logo.{extension}").put(Body=request_file)
    except ClientError:
        return {
           'message': 'upload error',
           'status': HTTPStatus.UNPROCESSABLE_ENTITY
       }, HTTPStatus.UNPROCESSABLE_ENTITY

    config_extras = json.loads(app.config.extras)
    if 'media' not in config_extras:
        config_extras["media"] = {}
    config_extras["media"]["logo"] = {
        "filename": request_file.filename,
        "mimetype": request_file.content_type,
        "size": len(request_file.read()),
        "uploaded_at": (datetime.datetime.now()).strftime("%d-%m-%Y %H:%M:%S"),
        "extension": extension,
        "key": f"add_on-csat-{app.app_code}_logo.{extension}"
    }

    app.config.extras = json.dumps(config_extras)
    app.update()

    return {
       'message': 'logo image has been uploaded successfully',
       'status': HTTPStatus.OK
   }, HTTPStatus.OK


@v2.route('/app/media/delete', methods=['DELETE'])
@authenticated_app
def delete_media(app):
    file_key = request.json["key"]

    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(os.environ.get("S3_BUCKET"))

    try:
        bucket.Object(file_key).delete()

        config_extras = json.loads(app.config.extras)
        if 'background' in file_key:
            del config_extras['media']['background']
        if 'logo' in file_key:
            del config_extras['media']['logo']

        app.config.extras = json.dumps(config_extras)
        app.update()
    except ClientError:
        return {
            'message': 'error, unable to delete media',
            'status': HTTPStatus.UNPROCESSABLE_ENTITY
        }, HTTPStatus.UNPROCESSABLE_ENTITY

    return {
        'message': 'media has been removed successfully',
        'status': HTTPStatus.NO_CONTENT
    }, HTTPStatus.NO_CONTENT


def set_resolve_webhook(app, webhook_url):
    multichannel = Multichannel(
        app_code=app.app_code,
        admin_email=app.admin_email,
        admin_token=app.admin_token)

    multichannel.set_mark_as_resolved_webhook(
        webhook_url=webhook_url,
        is_enable=True)
