#!/usr/bin/env python3
# incoming_notify
#
# FastNetMon notification relay script.
# Reads attack JSON from stdin and POSTs it to the notification service.
#
# For FastNetMon v2.0.368+, configure with:
#   sudo fcli set main notify_script_enabled enable
#   sudo fcli set main notify_script_format json
#   sudo fcli set main notify_script_path /path/to/incoming_notify.py
#   sudo fcli commit

import json
import sys
import logging
import requests

NOTIFY_API_USER = "admin"
NOTIFY_API_PASSWORD = "__changeme__"

url = "http://localhost:8090/receive_message"

logging.basicConfig(
    filename="/tmp/fastnetmon_notify_script.log",
    format="%(asctime)s %(message)s",
    level=logging.DEBUG,
)

stdin_data = sys.stdin.read()

try:
    data = json.loads(stdin_data)
except json.JSONDecodeError:
    logging.error("Failed to parse JSON from stdin")
    sys.exit(1)

action = data.get("action", "unknown")
ip_address = data.get("ip", "unknown")
logging.info("Received %s callback for %s", action, ip_address)

requests.post(url, json=data, auth=(NOTIFY_API_USER, NOTIFY_API_PASSWORD))
