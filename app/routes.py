import json
import uuid
import datetime

from flask import Blueprint, request, redirect, render_template, flash, jsonify
from marshmallow import ValidationError
from http import HTTPStatus
from .serializers import app_config_schema, csat_schema, config_schema
from .models import App, RatingType, Config, Csat
from .extensions import db
from sqlalchemy.exc import SQLAlchemyError
from .libs.multichannel import Multichannel
from .utils.decorator import superadmin_token_required

api = Blueprint("api", __name__, url_prefix="/api/v1")
webhook = Blueprint("webhook", __name__, url_prefix="/webhook")
web = Blueprint("web", __name__)


@api.route('/app_config/create', methods=['POST'])
@superadmin_token_required
def create_app_config():
    """Create new app and customer satisfaction config."""

    json_input = request.get_json(force=True)
    try:
        data = app_config_schema.load(json_input)
    except ValidationError as err:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'validation error',
            'errors': err.messages
        }, HTTPStatus.BAD_REQUEST

    if App.get_by_code(app_code=data['app_code']):
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'appid already registered'
        }, HTTPStatus.BAD_REQUEST

    rating_type = RatingType.STAR if data['rating_type'] == 'star' else RatingType.NUMBER if data['rating_type'] == 'number' else RatingType.CUSTOM # noqa
    official_web = data['official_web'] if 'official_web' in data else None
    extras = json.dumps(data['extras']) if 'extras' in data else None

    # insert data app and csat configuration
    try:
        app = App(
            app_code=data['app_code'],
            app_name=data['app_name'],
            admin_email=data['admin_email'],
            admin_token=data['admin_token'])

        db.session.add(app)
        db.session.flush()

        config = Config(
            official_web=official_web,
            csat_msg=data['csat_msg'],
            rating_type=rating_type,
            rating_total=data['rating_total'],
            extras=extras,
            app_id=app.id,
            csat_page=data['csat_page'])

        db.session.add(config)
        db.session.commit()
    except SQLAlchemyError as err:
        db.session.rollback()
        raise err

    # set url mark as resolved webhook url
    protocol = 'https://' if request.is_secure else 'http://'
    host = request.host.split(':', 1)[0]
    base = '{}{}'.format(protocol, host)
    webhook_url = '{base}/webhook/csat/{app_code}'.format(
        base=base,
        app_code=app.app_code)

    multichannel = Multichannel(
        app_code=app.app_code,
        admin_email=app.admin_email,
        admin_token=app.admin_token)

    multichannel.set_mark_as_resolved_webhook(
        webhook_url=webhook_url,
        is_enable=True)

    return {
        'status': HTTPStatus.OK,
        'message': 'csat has been configured successfully',
        'results': {
            'webhook_url': webhook_url,
            'is_enabled': True
        }
    }

@api.route('/csat/<csat_code>/check', methods=['POST'])
def check(csat_code):
    csat = Csat.get_by_csat_code(csat_code=csat_code)
    if not csat:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'csat code is invalid'
        }, HTTPStatus.BAD_REQUEST

    return jsonify({ 'data': { 'csat': csat_schema.dump(csat), 'config': config_schema.dump(csat.app.config) } })

@api.route('/csat/<csat_code>/create', methods=['POST'])
def submit_survey(csat_code):
    csat = Csat.get_by_csat_code(csat_code=csat_code)
    if not csat:
        return {
            'status': HTTPStatus.NOT_FOUND,
            'message': 'csat code is invalid'
        }, HTTPStatus.NOT_FOUND
    json_data = request.get_json(force=True)
    if not json_data["rating"]:
        err_msg = "Harap berikan penilaian dan ulasan Anda untuk membantu kami memberikan pelayanan yang terbaik"
        return {
            'status': HTTPStatus.UNPROCESSABLE_ENTITY,
            'message': err_msg
        }, HTTPStatus.UNPROCESSABLE_ENTITY

    csat.rating = json_data["rating"]
    csat.feedback = json_data["feedback"]
    csat.submitted_at = datetime.datetime.now()
    csat.update()

    return {
        'status': HTTPStatus.CREATED,
        'message': 'survey created successfully'
    }, HTTPStatus.CREATED


@webhook.route('/csat/<app_code>', methods=['POST'])
def wh_mark_as_resolved(app_code):
    """Handle request comming from multichannel mark as resolved webhook."""
    json_data = request.get_json(force=True)
    app = App.get_by_code(app_code=app_code)
    if not app:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'appid not found'
        }, 400

    config = Config.get_by_app_id(app_id=app.id)
    csat_msg = config.csat_msg
    csat_code = uuid.uuid4().hex

    if config.rating_type == RatingType.CUSTOM and len(config.csat_page) > 0:
        csat_url = config.csat_page.format(csat_code=csat_code)
    else:
        csat_url = '{base}csat/{csat_code}'.format(
            base=request.url_root,
            csat_code=csat_code)

    # inject {link} variable in csat msg
    msg = csat_msg.replace('{link}', csat_url)

    # sent customer satisfaction message to the customer
    room_id = json_data["service"]["room_id"]
    multichannel = Multichannel(
        app_code=app.app_code,
        admin_email=app.admin_email,
        admin_token=app.admin_token)

    multichannel.send_bot_message(room_id=room_id, message=msg)

    # filter source
    common_ch = {"wa", "qiscus", "telegram", "line", "fb"}
    qismo_source = json_data["service"]["source"]
    if qismo_source not in common_ch:
        qismo_source = "custom_channel"
        r = multichannel.get_all_channel()
        channels = r.json()["data"]
        if channels.get("custom_channels"):
            custom_channel = next((item for item in channels["custom_channels"] if item["identifier_key"] == json_data["service"]["source"]), None)
            if custom_channel:
                qismo_source = custom_channel["name"]

    # store satisfaction data to the database
    csat = Csat(
        csat_code=csat_code,
        user_id=json_data["customer"]["user_id"],
        agent_email=json_data["resolved_by"]["email"],
        source=qismo_source,
        app_id=app.id)

    csat.save()

    return {
        'status': HTTPStatus.OK,
        'message': 'csat was successfully sent to customer'
    }


@web.route('/csat/<csat_code>')
def csat_form(csat_code):
    """Customer satisfaction page to input rating and feedback data,
    from the link that was sent when the chat room was resolved."""
    csat = Csat.get_by_csat_code(csat_code=csat_code)
    if not csat:
        return redirect('https://qiscus.com')

    if csat.submitted_at is not None:
        if csat.app.config.official_web:
            return redirect(csat.app.config.official_web)
        else:
            return redirect('https://qiscus.com')

    return render_template(
        'csat.html',
        csat=csat, extras=_set_default_extras(csat.app.config.extras))


@web.route('/csat', methods=['POST'])
def csat_submit():
    """Customer satisfaction post form hanler."""

    csat_code = request.form.get("csat_code")
    rating = request.form.get("rating")
    feedback = request.form.get("feedback")
    error_msg = "Harap berikan penilaian dan ulasan Anda untuk membantu kami memberikan pelayanan yang terbaik" # noqa

    csat = Csat.get_by_csat_code(csat_code=csat_code)

    if not csat or csat.submitted_at is not None:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'invalid csat code or satisfaction form is submitted'
        }, HTTPStatus.BAD_REQUEST

    if rating == "":
        flash(error_msg)
        return redirect('/csat/{csat_code}'.format(csat_code=csat_code))

    # feedback field validation -> rating_min_fb (extras)
    if csat.app.config.extras:
        extras = json.loads(csat.app.config.extras)

        if type(rating) == int and 'rating_min_fb' in extras:
            if int(rating) <= extras['rating_min_fb'] and feedback.strip() == "": # noqa
                flash(error_msg)
                return redirect(
                    '/csat/{csat_code}'.format(csat_code=csat_code))

    csat.rating = rating
    csat.feedback = None if feedback.strip() == "" else feedback.strip()
    csat.submitted_at = datetime.datetime.now()
    csat.update()

    return render_template(
        'closing.html',
        csat=csat,
        extras=_set_default_extras(csat.app.config.extras))


def _set_default_extras(extras):
    ce = json.loads(extras) if extras else json.loads('{}')
    extras = {}
    extras['background'] = ce['background'] if 'background' in ce else ''
    extras['background_transparancy'] = ce['background_transparancy'] if 'background_transparancy' in ce else 0 # noqa
    extras['font_color'] = ce['font_color'] if 'font_color' in ce else '#000000' # noqa
    extras['logo'] = ce['logo'] if 'logo' in ce else ''
    extras['color'] = ce['color'] if 'color' in ce else '#005791'
    if 'rating_min_fb' in ce:
        extras['rating_min_fb'] = ce['rating_min_fb']

    return extras
