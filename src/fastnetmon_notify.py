#!/usr/bin/python

import logging
import os
from dotenv import load_dotenv
import json
import redis
from flask import Flask, request, make_response
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from slack_sdk.signature import SignatureVerifier
import requests

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=os.getenv("REDIS_PORT", 6379),
    db=os.getenv("REDIS_DB", 0),
)
if "SLACK_SIGNING_SECRET" in os.environ:
    signature_verifier = SignatureVerifier(os.environ["SLACK_SIGNING_SECRET"])
else:
    signature_verifier = None
app.redis = redis


auth = HTTPBasicAuth()

users = {
    os.getenv("NOTIFY_API_USER"): generate_password_hash(
        os.getenv("NOTIFY_API_PASSWORD")
    ),
}


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.route("/receive_message", methods=["POST"])
@auth.login_required
def receive_message():
    if request.method == "POST":
        content = request.get_json()
        attack_details = {
            "action": content["action"],
            "ip_address": content["ip"],
            "details": content,
        }
        message = json.dumps(attack_details)
        app.redis.rpush("slack_attack_action", message)
    return "Success"


@app.route("/slack_interaction", methods=["POST"])
def slack_incoming():
    # @todo move the bulk of this code into the slack_runner to allow the
    # removes to run asychronously to the main thread
    if signature_verifier is None:
        return "Not implemented"
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)

    if "payload" in request.form:
        slack_req = json.loads(request.form.get("payload"))
        if slack_req["type"] == "block_actions":
            if len(slack_req["actions"]):
                attack_uuid = slack_req["actions"][0]["value"]
                logger.warning(
                    "Trying to remove blackhole for {attack_uuid}".format(
                        attack_uuid=attack_uuid
                    )
                )
                try:
                    auth = (
                        os.environ["FNM_API_USERNAME"],
                        os.environ["FNM_API_PASSWORD"],
                    )
                    url = os.environ["FNM_API_URL"]
                    response = requests.delete(
                        url + "/blackhole/{uuid}".format(uuid=attack_uuid), auth=auth
                    )
                    if not response.ok:
                        return make_response("invalid request", 403)
                    message = json.dumps(slack_req)
                    app.redis.rpush("slack_update_blackhole", message)
                except Exception:
                    pass

    return ""


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8090, threaded=True)
