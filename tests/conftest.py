import json
import os
import pytest


@pytest.fixture(autouse=True)
def slack_env_vars(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_BOT_CHANNEL", "C0TEST12345")


@pytest.fixture
def ban_payload():
    with open(os.path.join(os.path.dirname(__file__), "..", "samples", "test_data.json")) as f:
        return json.load(f)


@pytest.fixture
def unban_payload():
    with open(os.path.join(os.path.dirname(__file__), "..", "samples", "unban_json.json")) as f:
        return json.load(f)


@pytest.fixture
def flowspec_payload():
    with open(os.path.join(os.path.dirname(__file__), "..", "samples", "flowspec_test.json")) as f:
        return json.load(f)


@pytest.fixture
def mock_redis(mocker):
    mock = mocker.MagicMock()
    mock.get.return_value = None
    return mock
