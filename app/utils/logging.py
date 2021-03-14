import time
import json
from flask import current_app


def http_request_log(flask_g, req, res):
    now = time.time()

    skip_current_path = ['/favicon.ico']
    if req.path in skip_current_path:
        return

    req_body = req.get_json(
        force=True) if req.is_json else dict(req.form)

    req_log = {}
    req_log["method"] = req.method
    req_log["path"] = req.path
    req_log["params"] = dict(req.args)
    req_log["req_body"] = req_body
    req_log["status"] = res.status_code
    req_log["latency"] = round(now - flask_g.start, 2)
    req_log["ip"] = req.headers.get(
        "X-Forwarded-For", req.remote_addr)
    req_log["host"] = req.host.split(":", 1)[0]
    req_log["message"] = "REQUEST_LOG"

    current_app.logger.info(json.dumps(req_log))
    pass


def http_outgoing_log(req, res):
    req_log = {}
    req_log["method"] = req.method
    req_log["url"] = req.url
    req_log["req_body"] = req.body
    req_log["status"] = res.status_code
    req_log["message"] = "OUTGOING_LOG"

    current_app.logger.info(json.dumps(req_log))
    pass
