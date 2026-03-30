from unittest.mock import patch

from slack import SlackAction, format_bps


class TestSlackActionBan:
    """Test ban message formatting with v2.0.368+ payload."""

    def test_process_ban_builds_attack_description(self, ban_payload, mock_redis):
        """Ban message should describe the attack using new field names."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "ban", "ip_address": "127.0.0.1", "details": ban_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        blocks = call_args["blocks"]
        summary_text = blocks[0]["text"]["text"]
        assert "127.0.0.1" in summary_text
        assert "outgoing" in summary_text

    def test_process_ban_includes_violation_reason(self, ban_payload, mock_redis):
        """Ban message should include attack_detection_threshold as violation reason."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "ban", "ip_address": "127.0.0.1", "details": ban_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        blocks = call_args["blocks"]
        violation_text = blocks[2]["text"]["text"]
        assert "pps" in violation_text
        assert "outgoing" in violation_text

    def test_process_ban_includes_attack_uuid_in_action(self, ban_payload, mock_redis):
        """Ban message should have a remove button with the attack UUID."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "ban", "ip_address": "127.0.0.1", "details": ban_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        blocks = call_args["blocks"]
        action_block = [b for b in blocks if b.get("type") == "actions"]
        assert len(action_block) == 1
        assert action_block[0]["elements"][0]["value"] == "041eb504-2b33-4ff7-a6b7-8235408d5062"

    def test_process_ban_attack_details_table(self, ban_payload, mock_redis):
        """Attack details attachment should format traffic counters."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "ban", "ip_address": "127.0.0.1", "details": ban_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        attachments = call_args["attachments"]
        assert len(attachments) >= 1


class TestSlackActionFlowspec:
    """Test partial_block message formatting with v2.0.368+ payload."""

    def test_process_partial_block_builds_description(self, flowspec_payload, mock_redis):
        """Flowspec message should describe the attack using new field names."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "partial_block", "ip_address": "127.0.0.1", "details": flowspec_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        blocks = call_args["blocks"]
        summary_text = blocks[0]["text"]["text"]
        assert "127.0.0.1" in summary_text
        assert "incoming" in summary_text

    def test_process_partial_block_includes_flowspec_rules(self, flowspec_payload, mock_redis):
        """Flowspec message should include rule details in attachments."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "partial_block", "ip_address": "127.0.0.1", "details": flowspec_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        attachments = call_args["attachments"]
        assert len(attachments) >= 2  # attack details + at least one flowspec rule


class TestSlackActionUnban:
    """Test unban message formatting with v2.0.368+ payload."""

    def test_process_unban_includes_ip(self, unban_payload, mock_redis):
        """Unban message should include the IP address."""
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "unban", "ip_address": "127.0.0.1", "details": unban_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        blocks = call_args["blocks"]
        text = blocks[0]["text"]["text"]
        assert "127.0.0.1" in text
        assert "Ban removed" in text

    def test_process_partial_unblock_includes_ip(self, flowspec_payload, mock_redis):
        """Partial unblock message should include the IP and correct label."""
        flowspec_payload["action"] = "partial_unblock"
        with patch.object(SlackAction, "_notify", return_value="1234567890.123456") as mock_notify:
            sa = SlackAction(
                attack_details={"action": "partial_unblock", "ip_address": "127.0.0.1", "details": flowspec_payload},
                redis=mock_redis,
            )
            sa.process_attack_message()

        call_args = mock_notify.call_args[0][0]
        blocks = call_args["blocks"]
        text = blocks[0]["text"]["text"]
        assert "127.0.0.1" in text
        assert "Flow mitigation removed" in text


class TestFormatBps:
    """Test bandwidth formatting helper."""

    def test_format_bps_small(self):
        assert format_bps(500) == "500.000 bps"

    def test_format_bps_kbps(self):
        result = format_bps(2048)
        assert "Kbps" in result

    def test_format_bps_mbps(self):
        result = format_bps(2048 * 1024)
        assert "Mbps" in result

    def test_format_bps_gbps(self):
        result = format_bps(2048 * 1024 * 1024)
        assert "Gbps" in result
