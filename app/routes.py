from .libs.multichannel_room import MultichannelRoom
import json
import uuid
import datetime

from flask import Blueprint, request, redirect, render_template, flash, jsonify, abort
from marshmallow import ValidationError
from http import HTTPStatus
from .serializers import app_config_schema, csat_schema, config_schema
from .models import App, RatingType, Config, Csat
from .extensions import db, s3_session
from sqlalchemy.exc import SQLAlchemyError
from .libs.multichannel import Multichannel
from .utils.decorator import superadmin_token_required
from .utils.enums import EmojiRating
from .utils.helpers import create_s3_url
import jwt
import os

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

    rating_type = RatingType.STAR if data['rating_type'] == 'star' else RatingType.NUMBER if data['rating_type'] == 'number' else RatingType.CUSTOM  # noqa
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
            csat_page=data.get('csat_page'))

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

    return jsonify({'data': {'csat': csat_schema.dump(csat), 'config': config_schema.dump(csat.app.config)}})


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
    resolved_payload = request.get_json(force=True)
    room_id = resolved_payload['service']['room_id']

    """Handle request comming from multichannel mark as resolved webhook."""
    json_data = request.get_json(force=True)
    app = App.get_by_code(app_code=app_code)
    if not app:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'appid not found'
        }, 400

    config = Config.get_by_app_id(app_id=app.id)

    # check ignore source
    extras = config.extras
    extras_dict = json.loads(extras)

    room_mulchan = MultichannelRoom(
        app_code=app_code, app_secret=extras_dict['app_secret'], room_id=room_id)
    send_csat = True

    if 'resolved_by_agent_only' in extras_dict and extras_dict['resolved_by_agent_only'] is not False:
        send_csat = room_mulchan.send_csat_enabled()

    if send_csat:
        if extras_dict.get("ignore_source"):
            ignore_source_dict = json.loads(extras_dict["ignore_source"])
            source = json_data["service"]["source"]
            if source in ignore_source_dict:
                return {
                    'status': HTTPStatus.OK,
                    'message': 'ignore source, csat not sent'
                }

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
                custom_channel = next(
                    (item for item in channels["custom_channels"] if item["identifier_key"] == json_data["service"]["source"]), None)
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

    return {}, HTTPStatus.NO_CONTENT


@web.route('/csat/<csat_code>')
def csat_form(csat_code):
    """Customer satisfaction page to input rating and feedback data,
    from the link that was sent when the chat room was resolved."""
    csat = Csat.get_by_csat_code(csat_code=csat_code)
    if not csat:
        return redirect('https://qiscus.com')

    if csat.submitted_at is not None:
        extras = json.loads(csat.app.config.extras)
        if 'closing_page_after_csat_submitted' in extras and extras['closing_page_after_csat_submitted']:
            return render_template(
                'closing.html',
                csat=csat,
                app=csat.app,
                extras=_set_default_extras(csat.app.config.extras, csat.app), emoji_enums=EmojiRating
            )
        if csat.app.config.official_web:
            return redirect(csat.app.config.official_web)
        else:
            return redirect('https://qiscus.com')

    return render_template(
        'csat.html',
        csat=csat,
        app=csat.app,
        extras=_set_default_extras(csat.app.config.extras, csat.app), emoji_enums=EmojiRating
    )


@web.route('/csat', methods=['POST'])
def csat_submit():
    """Customer satisfaction post form handler."""

    csat_code = request.form.get("csat_code")
    rating = request.form.get("rating")
    feedback = request.form.get("feedback")
    error_msg = "Harap berikan penilaian dan ulasan Anda untuk membantu kami memberikan pelayanan yang terbaik"  # noqa

    csat = Csat.get_by_csat_code(csat_code=csat_code)

    if not csat or csat.submitted_at is not None:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'message': 'invalid csat code or satisfaction form is submitted'
        }, HTTPStatus.BAD_REQUEST

    if rating == "":
        flash(error_msg)
        return redirect('/csat/{csat_code}'.format(csat_code=csat_code))

    if csat.app.config.rating_type == RatingType.EMOJI:
        if rating != EmojiRating.PUAS.value and rating != EmojiRating.TIDAK_PUAS.value:
            error_msg = "Rating yang diberikan harus berupa Puas atau Tidak Puas"
            flash(error_msg)
            return redirect('/csat/{csat_code}'.format(csat_code=csat_code))

    # feedback field validation -> rating_min_fb (extras)
    if csat.app.config.extras:
        extras = json.loads(csat.app.config.extras)

        if rating.isdigit() and 'rating_min_fb' in extras:
            if int(rating) <= extras['rating_min_fb'] and feedback.strip() == "":  # noqa
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
        app=csat.app,
        extras=_set_default_extras(csat.app.config.extras, csat.app))


def _set_default_extras(extras, app):
    ce = json.loads(extras) if extras else json.loads('{}')
    extras = {}

    # csat page media (background n logo)
    extras['logo'] = os.getenv('DEFAULT_LOGO_URL')
    extras['background'] = os.getenv(
        'DEFAULT_BACKGROUND_URL')
    if 'media' in ce:
        extras['background'] = create_s3_url(s3_session, f"add_on-csat-{app.app_code}_background.{ce['media']['background']['extension']}")\
            if 'background' in ce['media'] else ce['background'] if 'background' in ce else os.getenv(
            'DEFAULT_BACKGROUND_URL')
        extras['logo'] = create_s3_url(s3_session, f"add_on-csat-{app.app_code}_logo.{ce['media']['logo']['extension']}")\
            if 'logo' in ce['media'] else ce['logo'] if 'logo' in ce else os.getenv('DEFAULT_LOGO_URL')

    extras['background_transparancy'] = ce['background_transparancy'] if 'background_transparancy' in ce else 0.3 if extras['background'] == os.getenv(
        'DEFAULT_BACKGROUND_URL') else 0  # noqa
    extras['font_color'] = ce['font_color'] if 'font_color' in ce else '#000000'  # noqa
    extras['color'] = ce['color'] if 'color' in ce else '#005791'
    extras['enable_redirect'] = True if 'enable_redirect' not in ce else ce['enable_redirect']
    extras['emoji_type'] = ce['emoji_type'] if app.config.rating_type == RatingType.EMOJI else ''
    if 'rating_min_fb' in ce:
        extras['rating_min_fb'] = ce['rating_min_fb']

    if 'greetings' in ce:
        extras['greetings'] = ce['greetings']

    if 'additional_comment_instruction' in ce:
        extras['additional_comment_instruction'] = ce['additional_comment_instruction']

    if 'custom_comment_wording' in ce:
        extras['custom_comment_wording'] = ce['custom_comment_wording']

    if 'closing' in ce:
        extras['closing'] = ce['closing']

    if 'closing_button_text' in ce:
        extras['closing_button_text'] = ce['closing_button_text']

    if 'submit_button_text' in ce:
        extras['submit_button_text'] = ce['submit_button_text']

    extras['disable_rating_instruction'] = 'disable_rating_instruction' in ce
    extras['hide_app_name_title'] = False if 'hide_app_name_title' not in ce else ce['hide_app_name_title']

    return extras


@web.route('/<token>/preview')
def preview_page(token):
    try:
        decoded = jwt.decode(token, key=os.getenv(
            'CSAT_ADD_ON_SIGNATURE_KEY'), algorithms='HS256')
        app_code = decoded.get('app_code')
        app = App.get_by_code(app_code)

        if app is None:
            abort(403, description="Forbidden")

    except:
        abort(403, description="Forbidden")

    return render_template(
        'preview.html',
        app=app, token=token, extras=_set_default_extras(app.config.extras, app), emoji_enums=EmojiRating)


@web.route('/<token>/submit_preview', methods=['POST'])
def submit_preview(token):
    try:
        decoded = jwt.decode(token, key=os.getenv(
            'CSAT_ADD_ON_SIGNATURE_KEY'), algorithms='HS256')
        app_code = decoded.get('app_code')
        app = App.get_by_code(app_code)

        if app is None:
            abort(403, description="Forbidden")

    except:
        abort(403, description="Forbidden")

    return render_template(
        'closing.html',
        app=app, extras=_set_default_extras(app.config.extras, app), emoji_enums=EmojiRating)
