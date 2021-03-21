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
        (queue, message) = redis.blpop(
            ["slack_attack_action", "slack_update_blackhole"]
        )
        message = json.loads(message.decode("utf-8"))
        if queue == "slack_attack_action":
            sa = SlackAction(attack_details=message, redis=redis)
            sa.process_message()
            sa = None
        elif queue == "slack_update_blackhole":
            sa = SlackAction(update_message=message, redis=redis)
            sa.update_message()
            sa = None
        time.sleep(1)
