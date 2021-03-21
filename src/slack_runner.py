#!/usb/bin/python

# really basic runner that stops messages being posted
# more than once per second as per rate limits
# Really, this hsould live in Celery or something better

from fastnetmon_notify import redis
from slack import SlackAction
import time
import json

if __name__ == "__main__":
    while True:
        (queue, attack) = redis.blpop("slack_attack_action")
        attack_details = json.loads(attack.decode("utf-8"))
        sa = SlackAction(attack_details=attack_details, redis=redis)
        sa.process_message()
        time.sleep(1)
