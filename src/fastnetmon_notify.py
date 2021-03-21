#!/usr/bin/python

import sys
import logging
import os
from dotenv import load_dotenv
import json
import redis
from flask import Flask, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=os.getenv("REDIS_PORT", 6379),
    db=os.getenv("REDIS_DB", 0),
)
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8090, threaded=True)
