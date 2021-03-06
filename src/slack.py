from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
from pytz import timezone
import os
import sys
import logging
import json
import time


def format_bps(val):
    num = val
    depths = ["bps", "Kbps", "Mbps", "Gbps", "Tbps"]
    depth = 0
    while depth < len(depths):
        if num / 1024.0 < 1:
            return "{:.3f} {}".format(num, depths[depth])
        num = num / 1024.0
        depth = depth + 1
    return "{:.3f} {}".format(num, depths[depth - 1])


class SlackAction:
    client = None
    channel = None
    name = None
    details = None
    redis = None
    logger = None
    type = None

    def __init__(self, attack_details=None, update_message=None, redis=None):
        self.client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        self.channel = os.environ["SLACK_BOT_CHANNEL"]
        self.name = os.getenv("SLACK_BOT_NAME", "FastNetMon")
        if attack_details:
            self.details = attack_details["details"]
            self.type = "attack"
        elif update_message:
            self.details = update_message
            self.type = "update"
        self.redis = redis
        self.logger = logging.getLogger(__name__)

    def _get_message_payload(
        self,
        message,
        mitigation_rules=None,
        packet_details=None,
        attack_details=None,
        thread_ts=None,
        fallback_message=None,
        actions=None,
    ):
        attachments = []
        blocks = message
        if actions:
            blocks = blocks + actions
        if attack_details is not None:
            attachments.append(attack_details)
        if mitigation_rules is not None:
            attachments = attachments + mitigation_rules
        if packet_details is not None:
            attachments.append(packet_details)
        return {
            "channel": self.channel,
            "username": self.name,
            "thread_ts": thread_ts,
            "icon_emoji": ":robot_face:",
            "fallback": fallback_message,
            "blocks": blocks,
            "attachments": attachments,
        }

    def _notify(self, message):
        try:
            # logger.warning(json.dumps(message, indent=4))
            attachments = message["attachments"]
            del message["attachments"]
            response = self.client.chat_postMessage(**message)
            assert response["message"]
            if message["thread_ts"] is None:
                message_thread_id = response["ts"]
            else:
                message_thread_id = message["thread_ts"]
            time.sleep(1)
            del message["blocks"]
            for attachment in attachments:
                message["attachments"] = [attachment]
                message["thread_ts"] = message_thread_id
                response = self.client.chat_postMessage(**message)
                assert response["message"]
                time.sleep(1)
            return message_thread_id
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            self.logger.warning(f"Got an error: {e.response['error']}")
            self.logger.warning(json.dumps(message, indent=4))

    def _build_attack_details_table(self):
        dataset = self.details["attack_details"]
        dataset = dict(sorted(dataset.items()))
        attack_summary_fields = []
        for field in dataset:
            if "traffic" in field:
                raw_value = self.details["attack_details"][field]
                value = format_bps(raw_value)
            else:
                value = str(self.details["attack_details"][field])
            if value == "":
                value = "<not set>"
            attack_summary_fields.append(
                "_{field}:_ {value}".format(field=field, value=value)
            )
        return "\n".join(attack_summary_fields)

    def _build_flowspec_details_table(self, rule):
        flowspec_details = []
        for field in rule:
            value = rule[field]
            if isinstance(value, list):
                value = ", ".join(str(x) for x in value)
            if value == "":
                value = "<not set>"
            flowspec_details.append(
                "_{field}:_ {value}".format(field=field, value=value)
            )
        return "\n".join(flowspec_details)

    def _get_attack_details(self):
        fields = self._build_attack_details_table()
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Attack Summary Details*"},
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": fields}},
            ],
            "fallback": "Summary of attack volumetric data",
        }

    def _get_flowspec_blocks(self, rule):
        fields = self._build_flowspec_details_table(rule)
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Flowspec Rules*"},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": fields}},
        ]

    def process_message(self):
        if self.type == "attack":
            self.process_attack_message()
        elif self.type == "update":
            self.process_update_message()

    def process_update_message(self):
        if "message" in self.details:
            blocks = self.details["message"]["blocks"]
            new_blocks = []
            for block in blocks:
                if block["type"] != "actions":
                    new_blocks.append(block)
            try:
                # logger.warning(json.dumps(message, indent=4))
                response = self.client.chat_update(
                    channel=self.details["channel"]["id"],
                    ts=self.details["message"]["ts"],
                    text="Ban has been removed",
                    blocks=new_blocks,
                )
                assert response["message"]
                return response["ts"]
            except SlackApiError as e:
                # You will get a SlackApiError if "ok" is False
                assert e.response["ok"] is False
                assert e.response[
                    "error"
                ]  # str like 'invalid_auth', 'channel_not_found'
                self.logger.warning(f"Got an error: {e.response['error']}")
                self.logger.warning(json.dumps(self.details, indent=4))

    def process_attack_message(self):
        if self.details["action"] == "ban" or self.details["action"] == "partial_block":
            attack_description = (
                "*RTBH IP {ip_address}*: {attack_protocol} "
                + "{attack_direction} with {attack_severity} severity {attack_type} "
                + "attack"
            ).format(
                ip_address=self.details["ip"],
                attack_protocol=self.details["attack_details"]["attack_protocol"],
                attack_direction=self.details["attack_details"]["attack_direction"],
                attack_severity=self.details["attack_details"]["attack_severity"],
                attack_type=self.details["attack_details"]["attack_type"],
            )
            flowspec_attachments = None
            redis_key = self.details["attack_details"]["attack_uuid"]
            if self.details["action"] == "partial_block":
                redis_key = "fs-{attack_direction}-{ip_address}".format(
                    attack_direction=self.details["attack_details"]["attack_direction"],
                    ip_address=self.details["ip"],
                )
                attack_description = (
                    "*Flow Mitigation for IP {ip_address}*: {attack_protocol} "
                    + "{attack_direction} with {attack_severity} severity {attack_type} "
                    + "attack"
                ).format(
                    ip_address=self.details["ip"],
                    attack_protocol=self.details["attack_details"]["attack_protocol"],
                    attack_direction=self.details["attack_details"]["attack_direction"],
                    attack_severity=self.details["attack_details"]["attack_severity"],
                    attack_type=self.details["attack_details"]["attack_type"],
                )
                flowspec_attachments = []
                for rule in self.details["flow_spec_rules"]:
                    flowspec_details = {
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Flow Rules for the block*",
                                },
                            }
                        ],
                        "fallback": "Flow rules for the attack",
                    }
                    flowspec_details["blocks"] = flowspec_details[
                        "blocks"
                    ] + self._get_flowspec_blocks(rule)
                    flowspec_attachments.append(flowspec_details)
            packet_capture_details = "Not available"
            if "packet_dump" in self.details:
                packet_capture_details = "```{packet_details}```".format(
                    packet_details="\n".join(self.details["packet_dump"])
                )

            attack_summary_block = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": attack_description},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Violation reason is {violation} in {direction} direction".format(
                            violation=self.details["attack_details"][
                                "attack_detection_threshold"
                            ],
                            direction=self.details["attack_details"][
                                "attack_direction"
                            ],
                        ),
                    },
                },
            ]

            attack_data = self._get_attack_details()

            packet_details = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Packet Capture Sample*"},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": packet_capture_details},
                    },
                ],
                "fallback": "Packets in the capture",
            }

            actions = [
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Remove block :lock:",
                                "emoji": True,
                            },
                            "value": self.details["attack_details"]["attack_uuid"],
                        },
                    ],
                }
            ]

            message_thread = self.redis.get(redis_key)
            if message_thread is not None:
                message_thread = message_thread.decode("utf-8")
                actions = None

            message = self._get_message_payload(
                message=attack_summary_block,
                attack_details=attack_data,
                packet_details=packet_details,
                mitigation_rules=flowspec_attachments,
                fallback_message=attack_description,
                actions=actions,
                thread_ts=message_thread,
            )

            message_thread = self._notify(message)
            self.redis.set(redis_key, message_thread)
            if self.details["action"] == "partial_block":
                self.redis.expire(redis_key, 1800)

        elif self.details["action"] == "unban":
            ban_id = self.details["attack_details"]["attack_uuid"]
            message_thread = self.redis.get(ban_id)
            if message_thread is not None:
                message_thread = message_thread.decode("utf-8")
            tz = timezone(os.getenv("TIMEZONE", "Australia/Sydney"))
            action_time = (
                datetime.utcnow().replace(tzinfo=timezone("utc")).astimezone(tz=tz)
            )
            action_description = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Ban removed* for {ip_address} at {datetime}".format(
                            ip_address=self.details["ip"],
                            datetime=action_time.strftime("%a %b %d %H:%M:%S %Z %Y"),
                        ),
                    },
                }
            ]
            message = self._get_message_payload(
                message=action_description,
                thread_ts=message_thread,
                fallback_message="Ban removed",
            )
            self._notify(message)
        else:
            self.logger.warn(
                "Data for unknown action type {action}".format(
                    action=self.details["action"]
                )
            )
