import json
from app.utils.request import make_request


class MultichannelRoom():
    def __init__(self, app_code, app_secret, room_id):
        self.app_code = app_code
        self.app_secret = app_secret
        self.room_id = room_id

    def __repr__(self):
        return '<MultichannelRoom: app_code={app_code} app_secret{app_secret} room_id={room_id}>'.format(  # noqa
            app_code=self.app_code,
            app_secret=self.app_secret,
            room_id=self.room_id)

    def headers(self):
        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['QISCUS_SDK_SECRET'] = self.app_secret
        headers['QISCUS-SDK-APP-ID'] = self.app_code
        return headers

    def send_csat_enabled(self):
        r = make_request(
            method="get",
            url='https://api.qiscus.com/api/v2.1/rest/get_rooms_info?room_ids[]={room_id}'.format(
                room_id=self.room_id
            ),
            headers=self.headers()
        )

        json_r = r.json()
        rooms = json_r['results']['rooms']
        room_options = json.loads(rooms[0]['room_options'])

        if 'scalar' not in room_options:
            return True

        return room_options['scalar']
