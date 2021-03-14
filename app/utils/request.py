import requests
from .logging import http_outgoing_log


def make_request(**kwargs):
    try:
        response = requests.request(**kwargs)
        request = response.request

        # create logging
        http_outgoing_log(req=request, res=response)

        response.raise_for_status()
        return response
    except requests.RequestException as err:
        raise err