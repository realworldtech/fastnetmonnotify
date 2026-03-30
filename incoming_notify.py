#!/usr/bin/env python3
# incoming_notify
#
# FastNetMon notification relay script.
# Reads attack JSON from stdin and POSTs it to the notification service.
#
# Required environment variables:
#   NOTIFY_API_USER     - HTTP Basic Auth username for the notification service
#   NOTIFY_API_PASSWORD - HTTP Basic Auth password for the notification service
#   NOTIFY_API_URL      - (optional) URL of the notification service
#                         default: http://localhost:8090/receive_message
#
# For FastNetMon v2.0.368+, configure with:
#   sudo fcli set main notify_script_enabled enable
#   sudo fcli set main notify_script_format json
#   sudo fcli set main notify_script_path /path/to/incoming_notify.py
#   sudo fcli commit

import json
import os
import sys
import logging
import requests

logging.basicConfig(
    filename="/tmp/fastnetmon_notify_script.log",
    format="%(asctime)s %(message)s",
    level=logging.DEBUG,
)

NOTIFY_API_USER = os.environ.get("NOTIFY_API_USER")
NOTIFY_API_PASSWORD = os.environ.get("NOTIFY_API_PASSWORD")
NOTIFY_API_URL = os.environ.get("NOTIFY_API_URL", "http://localhost:8090/receive_message")

if not NOTIFY_API_USER or not NOTIFY_API_PASSWORD:
    logging.error(
        "NOTIFY_API_USER and NOTIFY_API_PASSWORD environment variables must be set"
    )
    sys.exit(1)

stdin_data = sys.stdin.read()

try:
    data = json.loads(stdin_data)
except json.JSONDecodeError:
    logging.error("Failed to parse JSON from stdin")
    sys.exit(1)

action = data.get("action", "unknown")
ip_address = data.get("ip", "unknown")
logging.info("Received %s callback for %s", action, ip_address)

requests.post(NOTIFY_API_URL, json=data, auth=(NOTIFY_API_USER, NOTIFY_API_PASSWORD), timeout=10)
