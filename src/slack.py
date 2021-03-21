from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
from pytz import timezone
import os
import sys
import logging
import json


class SlackAction:
    client = None
    channel = None
    name = None
    details = None
    redis = None
    logger = None

    def __init__(self, attack_details=None, redis=None):
        self.client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        self.channel = os.environ["SLACK_BOT_CHANNEL"]
        self.name = os.getenv("SLACK_BOT_NAME", "FastNetMon")
        self.details = attack_details["details"]
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
            response = self.client.chat_postMessage(**message)
            assert response["message"]
            return response["ts"]
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            self.logger.warning(f"Got an error: {e.response['error']}")
            self.logger.warning(json.dumps(message, indent=4))

    def _build_attack_details_table(self):
        attack_summary_fields = [
            {"type": "mrkdwn", "text": "*Key*"},
            {"type": "mrkdwn", "text": "*Value*"},
        ]
        for field in self.details["attack_details"]:
            attack_summary_fields.append({"type": "plain_text", "text": field})
            value = str(self.details["attack_details"][field])
            if value == "":
                value = "<not set>"
            attack_summary_fields.append({"type": "plain_text", "text": value},)
        return attack_summary_fields

    def _build_flowspec_details_table(self, rule):
        flowspec_details = [
            {"type": "mrkdwn", "text": "*Key*"},
            {"type": "mrkdwn", "text": "*Value*"},
        ]
        for field in rule:
            value = rule[field]
            if isinstance(value, list):
                value = ", ".join(str(x) for x in value)
            if value == "":
                value = "<not set>"
            flowspec_details.append({"type": "plain_text", "text": field})
            flowspec_details.append({"type": "plain_text", "text": str(value)})
        return flowspec_details

    def _get_attack_details(self):
        attack_details = []
        fields = self._build_attack_details_table()
        headers = fields[0:2]
        fields = fields[2:]
        field_blocks = []
        field_count = 0
        cur_block = headers
        for field in fields:
            field_count = field_count + 1
            cur_block.append(field)
            if field_count == 8:
                field_blocks.append(cur_block)
                cur_block = []
                field_count = 0
        if len(cur_block) > 2:
            field_blocks.append(cur_block)
        for field_block in field_blocks:
            attack_details.append({"type": "section", "fields": field_block})
        return {
            "blocks": attack_details,
            "fallback": "Summary of attack volumetric data",
        }

    def _get_flowspec_blocks(self, rule):
        flowspec_details = []
        fields = self._build_flowspec_details_table(rule)
        headers = fields[0:2]
        fields = fields[2:]
        field_blocks = []
        field_count = 0
        cur_block = headers
        for field in fields:
            field_count = field_count + 1
            cur_block.append(field)
            if field_count == 8:
                field_blocks.append(cur_block)
                cur_block = []
                field_count = 0
        if len(cur_block) > 2:
            field_blocks.append(cur_block)
        for field_block in field_blocks:
            flowspec_details.append({"type": "section", "fields": field_block})
        return flowspec_details

    def process_message(self):
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
            if self.details["action"] == "partial_block":
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

            message = self._get_message_payload(
                message=attack_summary_block,
                attack_details=attack_data,
                packet_details=packet_details,
                mitigation_rules=flowspec_attachments,
                fallback_message=attack_description,
                actions=actions,
            )
            message_thread = self._notify(message)
            self.redis.set(
                self.details["attack_details"]["attack_uuid"], message_thread
            )

        elif self.details["action"] == "unban":
            ban_id = self.details["attack_details"]["attack_uuid"]
            message_thread = self.redis.get(ban_id)
            if message_thread is not None:
                message_thread = message_thread.decode("utf-8")
            tz = timezone(os.getenv("TIMEZONE", "Australia/Sydney"))
            action_description = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Ban removed* for {ip_address} at {datetime}".format(
                            ip_address=self.details["ip"],
                            datetime=tz.localize(datetime.utcnow()).strftime(
                                "%a %b %d %H:%M:%S %Z %Y"
                            ),
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
