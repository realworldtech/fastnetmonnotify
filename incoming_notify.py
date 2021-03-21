#!/usr/bin/python
# incoming_notify

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

if len(sys.argv) != 3:
    logging.error("Please provide two arguments for script: action and IP address")
    sys.exit(1)

action = sys.argv[1]
ip_address = sys.argv[2]

stdin_data = sys.stdin.read()
data = json.loads(stdin_data)

requests.post(url, json=data, auth=(NOTIFY_API_USER, NOTIFY_API_PASSWORD))
