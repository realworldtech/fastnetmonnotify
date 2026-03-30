import json
import os
from base64 import b64encode
from unittest.mock import patch

import pytest


@pytest.fixture
def app():
    os.environ.setdefault("NOTIFY_API_USER", "testuser")
    os.environ.setdefault("NOTIFY_API_PASSWORD", "testpass")
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("REDIS_DB", "0")

    with patch("fastnetmon_notify.redis") as mock_redis:
        from fastnetmon_notify import app

        app.redis = mock_redis
        app.config["TESTING"] = True
        yield app, mock_redis


@pytest.fixture
def client(app):
    flask_app, mock_redis = app
    with flask_app.test_client() as client:
        yield client, mock_redis


def _auth_header(username="testuser", password="testpass"):
    credentials = b64encode(f"{username}:{password}".encode()).decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


class TestReceiveMessage:
    def test_ban_message_queued(self, client, ban_payload):
        c, mock_redis = client
        response = c.post(
            "/receive_message",
            json=ban_payload,
            headers=_auth_header(),
        )
        assert response.status_code == 200
        mock_redis.rpush.assert_called_once()
        queued_data = json.loads(mock_redis.rpush.call_args[0][1])
        assert queued_data["action"] == "ban"
        assert queued_data["ip_address"] == "127.0.0.1"

    def test_hostgroup_alert_uses_hostgroup_name(self, client, ban_payload):
        ban_payload["alert_scope"] = "hostgroup"
        ban_payload["hostgroup_name"] = "my_servers"
        c, mock_redis = client
        response = c.post(
            "/receive_message",
            json=ban_payload,
            headers=_auth_header(),
        )
        assert response.status_code == 200
        queued_data = json.loads(mock_redis.rpush.call_args[0][1])
        assert queued_data["ip_address"] == "my_servers"

    def test_requires_auth(self, client, ban_payload):
        c, _ = client
        response = c.post("/receive_message", json=ban_payload)
        assert response.status_code == 401

    def test_wrong_auth_rejected(self, client, ban_payload):
        c, _ = client
        response = c.post(
            "/receive_message",
            json=ban_payload,
            headers=_auth_header("wrong", "creds"),
        )
        assert response.status_code == 401
