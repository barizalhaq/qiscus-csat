import json
from ..utils.request import make_request


class Multichannel:
    def __init__(self, app_code, admin_email, admin_token):
        self.app_code = app_code
        self.admin_email = admin_email
        self.admin_token = admin_token

    def __repr__(self):
        return '<Multichannel: app_code={app_code} admin_email{admin_email} admin_token={admin_token}>'.format( # noqa
            app_code=self.app_code,
            admin_email=self.admin_email,
            admin_token=self.admin_token)

    def headers(self):
        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['Authorization'] = self.admin_token
        return headers

    def send_bot_message(self, room_id, message):
        url = 'https://qismo.qiscus.com/{app_code}/bot'.format(
            app_code=self.app_code)

        payload = {}
        payload['sender_email'] = self.admin_email
        payload['room_id'] = room_id
        payload['message'] = message

        r = make_request(
            method='post',
            url=url,
            headers=self.headers(),
            data=json.dumps(payload))

        return r

    def set_mark_as_resolved_webhook(self, webhook_url, is_enable):
        url = 'https://qismo.qiscus.com/api/v1/app/webhook/mark_as_resolved'

        payload = {}
        payload['webhook_url'] = webhook_url
        payload['is_webhook_enabled'] = is_enable

        r = make_request(
            method='post',
            url=url,
            headers=self.headers(),
            data=json.dumps(payload))

        return r
