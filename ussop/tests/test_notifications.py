"""
Tests for NotificationService — configuration, email (mocked SMTP),
webhook (mocked HTTP), Slack, convenience methods, and channel routing.
"""
import asyncio
import sys
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, call

_ussop_dir = Path(__file__).parent.parent
_project_root = _ussop_dir.parent
for _p in (_ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _msg(title="Alert", body="Something happened", severity="warning"):
    from services.notifications import NotificationMessage
    return NotificationMessage(
        title=title,
        body=body,
        severity=severity,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )


def _svc():
    from services.notifications import NotificationService
    return NotificationService()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Instantiation
# ══════════════════════════════════════════════════════════════════════════════

class TestNotificationService:
    def test_instantiation(self):
        assert _svc() is not None

    def test_initially_no_channels(self):
        svc = _svc()
        assert svc.enabled_channels == []

    def test_initially_no_webhooks(self):
        assert _svc().webhook_urls == []

    def test_has_send_method(self):
        assert callable(getattr(_svc(), "send", None))

    def test_singleton_returns_same_instance(self):
        from services.notifications import get_notification_service
        import services.notifications as mod
        mod._notification_service = None
        s1 = get_notification_service()
        s2 = get_notification_service()
        assert s1 is s2
        mod._notification_service = None


# ══════════════════════════════════════════════════════════════════════════════
# 2. NotificationMessage dataclass
# ══════════════════════════════════════════════════════════════════════════════

class TestNotificationMessage:
    def test_message_fields(self):
        msg = _msg(title="Test", body="Body text", severity="critical")
        assert msg.title == "Test"
        assert msg.body == "Body text"
        assert msg.severity == "critical"
        assert msg.timestamp is not None

    def test_metadata_defaults_none(self):
        msg = _msg()
        assert msg.metadata is None

    def test_message_with_metadata(self):
        from services.notifications import NotificationMessage
        msg = NotificationMessage(
            title="T", body="B", severity="info",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            metadata={"station": "S1", "count": 3}
        )
        assert msg.metadata["station"] == "S1"

    def test_all_severity_levels_accepted(self):
        for sev in ("info", "warning", "error", "critical"):
            msg = _msg(severity=sev)
            assert msg.severity == sev


# ══════════════════════════════════════════════════════════════════════════════
# 3. Email configuration
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailConfiguration:
    def test_configure_email_stores_config(self):
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", True):
            svc.configure_email(
                host="smtp.factory.com", port=587,
                username="user", password="pass",
                from_addr="ussop@factory.com",
                to_addrs=["ops@factory.com"],
            )
        assert svc.email_config is not None
        assert svc.email_config["host"] == "smtp.factory.com"
        assert svc.email_config["from_addr"] == "ussop@factory.com"

    def test_configure_email_multiple_recipients(self):
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", True):
            svc.configure_email(
                host="smtp.h", port=465, username="u", password="p",
                from_addr="from@h",
                to_addrs=["a@h", "b@h", "c@h"],
            )
        assert len(svc.email_config["to_addrs"]) == 3

    def test_configure_email_adds_channel_when_smtp_available(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", True):
            svc.configure_email("h", 25, "u", "p", "f@h", ["t@h"])
        assert NotificationChannel.EMAIL in svc.enabled_channels

    def test_configure_email_skips_channel_when_smtp_unavailable(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", False):
            svc.configure_email("h", 25, "u", "p", "f@h", ["t@h"])
        assert NotificationChannel.EMAIL not in svc.enabled_channels

    def test_configure_email_tls_default_true(self):
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", True):
            svc.configure_email("h", 587, "u", "p", "f@h", ["t@h"])
        assert svc.email_config["use_tls"] is True

    def test_configure_email_tls_can_be_disabled(self):
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", True):
            svc.configure_email("h", 25, "u", "p", "f@h", ["t@h"], use_tls=False)
        assert svc.email_config["use_tls"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. Email sending (mocked SMTP)
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailSending:
    def _configured_svc(self):
        svc = _svc()
        with patch("services.notifications.SMTP_AVAILABLE", True):
            svc.configure_email(
                host="smtp.h", port=587, username="u", password="p",
                from_addr="from@h", to_addrs=["to@h"],
            )
        return svc

    def _smtp_patches(self):
        """Context manager that installs aiosmtplib + MIME stubs."""
        from email.mime.text import MIMEText as _MIMEText
        from email.mime.multipart import MIMEMultipart as _MIMEMultipart
        import contextlib

        @contextlib.contextmanager
        def _ctx():
            with patch("services.notifications.SMTP_AVAILABLE", True), \
                 patch("services.notifications.aiosmtplib", create=True) as mock_smtp, \
                 patch("services.notifications.MIMEText", _MIMEText, create=True), \
                 patch("services.notifications.MIMEMultipart", _MIMEMultipart, create=True):
                yield mock_smtp
        return _ctx()

    @pytest.mark.asyncio
    async def test_send_email_calls_aiosmtplib(self):
        svc = self._configured_svc()
        with self._smtp_patches() as mock_smtp:
            mock_smtp.send = AsyncMock()
            await svc._send_email(_msg())
            mock_smtp.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_email_subject_includes_severity(self):
        svc = self._configured_svc()
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["subject"] = msg["Subject"]

        with self._smtp_patches() as mock_smtp:
            mock_smtp.send = fake_send
            await svc._send_email(_msg(title="High Temp", severity="critical"))

        assert "CRITICAL" in captured.get("subject", "")
        assert "High Temp" in captured.get("subject", "")

    @pytest.mark.asyncio
    async def test_email_from_address_set(self):
        svc = self._configured_svc()
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["from"] = msg["From"]

        with self._smtp_patches() as mock_smtp:
            mock_smtp.send = fake_send
            await svc._send_email(_msg())

        assert captured.get("from") == "from@h"

    @pytest.mark.asyncio
    async def test_email_exception_does_not_raise(self):
        svc = self._configured_svc()
        with self._smtp_patches() as mock_smtp:
            mock_smtp.send = AsyncMock(side_effect=ConnectionRefusedError("no server"))
            # Must not propagate
            await svc._send_email(_msg())

    @pytest.mark.asyncio
    async def test_send_skips_email_when_not_configured(self):
        svc = _svc()  # no configure_email called
        with self._smtp_patches() as mock_smtp:
            mock_smtp.send = AsyncMock()
            await svc._send_email(_msg())
            mock_smtp.send.assert_not_awaited()


# ══════════════════════════════════════════════════════════════════════════════
# 5. Webhook configuration & sending
# ══════════════════════════════════════════════════════════════════════════════

class TestWebhookNotifications:
    def test_configure_webhook_stores_urls(self):
        svc = _svc()
        with patch("services.notifications.AIOHTTP_AVAILABLE", True):
            svc.configure_webhook(["https://hook1.com", "https://hook2.com"])
        assert len(svc.webhook_urls) == 2

    def test_configure_webhook_adds_channel(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        with patch("services.notifications.AIOHTTP_AVAILABLE", True):
            svc.configure_webhook(["https://hook.com"])
        assert NotificationChannel.WEBHOOK in svc.enabled_channels

    def test_configure_webhook_skips_channel_when_aiohttp_unavailable(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        with patch("services.notifications.AIOHTTP_AVAILABLE", False):
            svc.configure_webhook(["https://hook.com"])
        assert NotificationChannel.WEBHOOK not in svc.enabled_channels

    @pytest.mark.asyncio
    async def test_webhook_posts_to_each_url(self):
        svc = _svc()
        svc.webhook_urls = ["https://url1.com", "https://url2.com"]

        post_calls = []

        class FakeResp:
            status = 200
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        class FakeSession:
            def post(self, url, **kw):
                post_calls.append(url)
                return FakeResp()
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        with patch("services.notifications.AIOHTTP_AVAILABLE", True), \
             patch("services.notifications.aiohttp") as mock_aio:
            mock_aio.ClientSession.return_value = FakeSession()
            mock_aio.ClientTimeout = MagicMock(return_value=None)
            await svc._send_webhook(_msg())

        assert len(post_calls) == 2

    @pytest.mark.asyncio
    async def test_webhook_payload_has_required_fields(self):
        svc = _svc()
        svc.webhook_urls = ["https://hook.com"]
        captured = {}

        class FakeResp:
            status = 200
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        class FakeSession:
            def post(self, url, json=None, **kw):
                captured.update(json or {})
                return FakeResp()
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        with patch("services.notifications.AIOHTTP_AVAILABLE", True), \
             patch("services.notifications.aiohttp") as mock_aio:
            mock_aio.ClientSession.return_value = FakeSession()
            mock_aio.ClientTimeout = MagicMock(return_value=None)
            await svc._send_webhook(_msg(title="Test Alert", severity="error"))

        for key in ("source", "timestamp", "severity", "title", "message"):
            assert key in captured, f"Missing key: {key}"
        assert captured["source"] == "ussop"

    @pytest.mark.asyncio
    async def test_webhook_failure_does_not_raise(self):
        svc = _svc()
        svc.webhook_urls = ["https://bad-url.com"]

        class BrokenPost:
            async def __aenter__(self): raise Exception("network error")
            async def __aexit__(self, *a): pass

        class FakeSession:
            def post(self, url, **kwargs): return BrokenPost()
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        with patch("services.notifications.AIOHTTP_AVAILABLE", True), \
             patch("services.notifications.aiohttp") as mock_aio:
            mock_aio.ClientSession.return_value = FakeSession()
            mock_aio.ClientTimeout = MagicMock(return_value=None)
            await svc._send_webhook(_msg())  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# 6. Slack
# ══════════════════════════════════════════════════════════════════════════════

class TestSlackNotifications:
    def test_configure_slack_adds_channel(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        with patch("services.notifications.AIOHTTP_AVAILABLE", True):
            svc.configure_slack("https://hooks.slack.com/test")
        assert NotificationChannel.SLACK in svc.enabled_channels

    def test_configure_slack_stores_url(self):
        svc = _svc()
        with patch("services.notifications.AIOHTTP_AVAILABLE", True):
            svc.configure_slack("https://hooks.slack.com/test")
        assert svc.slack_webhook == "https://hooks.slack.com/test"

    @pytest.mark.asyncio
    async def test_slack_payload_has_attachments(self):
        svc = _svc()
        svc.slack_webhook = "https://hooks.slack.com/test"
        captured = {}

        class FakeResp:
            status = 200
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        class FakeSession:
            def post(self, url, json=None, **kw):
                captured.update(json or {})
                return FakeResp()
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        with patch("services.notifications.AIOHTTP_AVAILABLE", True), \
             patch("services.notifications.aiohttp") as mock_aio:
            mock_aio.ClientSession.return_value = FakeSession()
            mock_aio.ClientTimeout = MagicMock(return_value=None)
            await svc._send_slack(_msg(severity="critical"))

        assert "attachments" in captured
        assert len(captured["attachments"]) > 0

    @pytest.mark.asyncio
    async def test_slack_color_maps_severity(self):
        svc = _svc()
        svc.slack_webhook = "https://hooks.slack.com/test"
        colors_seen = {}

        class FakeResp:
            status = 200
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        class FakeSession:
            def post(self_, url, json=None, **kw):
                if json and "attachments" in json:
                    colors_seen[json["attachments"][0].get("color")] = True
                return FakeResp()
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        with patch("services.notifications.AIOHTTP_AVAILABLE", True), \
             patch("services.notifications.aiohttp") as mock_aio:
            mock_aio.ClientSession.return_value = FakeSession()
            mock_aio.ClientTimeout = MagicMock(return_value=None)
            await svc._send_slack(_msg(severity="warning"))

        assert len(colors_seen) > 0  # a color was set


# ══════════════════════════════════════════════════════════════════════════════
# 7. send() — channel routing
# ══════════════════════════════════════════════════════════════════════════════

class TestSendRouting:
    @pytest.mark.asyncio
    async def test_send_calls_all_enabled_channels(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        svc._send_email   = AsyncMock()
        svc._send_webhook = AsyncMock()
        svc._send_slack   = AsyncMock()
        svc.enabled_channels = [
            NotificationChannel.EMAIL,
            NotificationChannel.WEBHOOK,
            NotificationChannel.SLACK,
        ]
        await svc.send(_msg())
        svc._send_email.assert_awaited_once()
        svc._send_webhook.assert_awaited_once()
        svc._send_slack.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_skips_disabled_channels(self):
        from services.notifications import NotificationChannel
        svc = _svc()
        svc._send_email   = AsyncMock()
        svc._send_webhook = AsyncMock()
        svc.enabled_channels = [NotificationChannel.WEBHOOK]
        await svc.send(_msg())
        svc._send_email.assert_not_awaited()
        svc._send_webhook.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_no_channels_does_nothing(self):
        svc = _svc()
        svc._send_email   = AsyncMock()
        svc._send_webhook = AsyncMock()
        svc.enabled_channels = []
        await svc.send(_msg())
        svc._send_email.assert_not_awaited()
        svc._send_webhook.assert_not_awaited()


# ══════════════════════════════════════════════════════════════════════════════
# 8. Convenience methods
# ══════════════════════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    @pytest.mark.asyncio
    async def test_send_defect_alert_calls_send(self):
        svc = _svc()
        svc.send = AsyncMock()
        await svc.send_defect_alert("LINE-1", "PART-001", defect_count=2)
        svc.send.assert_awaited_once()
        msg = svc.send.call_args[0][0]
        assert "LINE-1" in msg.title
        assert msg.severity in ("warning", "error")

    @pytest.mark.asyncio
    async def test_send_defect_alert_severity_scales_with_count(self):
        svc = _svc()
        messages = []
        async def capture(m): messages.append(m)
        svc.send = capture
        await svc.send_defect_alert("S1", None, defect_count=1)
        await svc.send_defect_alert("S1", None, defect_count=5)
        assert messages[0].severity == "warning"
        assert messages[1].severity == "error"

    @pytest.mark.asyncio
    async def test_send_system_alert_calls_send(self):
        svc = _svc()
        svc.send = AsyncMock()
        await svc.send_system_alert("Disk Full", "Storage at 99%", severity="critical")
        svc.send.assert_awaited_once()
        msg = svc.send.call_args[0][0]
        assert msg.severity == "critical"
        assert "Disk Full" in msg.title

    @pytest.mark.asyncio
    async def test_send_daily_report_calls_send(self):
        svc = _svc()
        svc.send = AsyncMock()
        stats = {"total": 500, "pass_rate": 0.97, "defects": 15, "avg_time_ms": 320}
        await svc.send_daily_report("admin@factory.com", stats)
        svc.send.assert_awaited_once()
        msg = svc.send.call_args[0][0]
        assert msg.severity == "info"
        assert "500" in msg.body

    @pytest.mark.asyncio
    async def test_send_defect_alert_metadata_has_station(self):
        svc = _svc()
        messages = []
        async def capture(m): messages.append(m)
        svc.send = capture
        await svc.send_defect_alert("STATION-3", "PART-X", defect_count=1)
        assert messages[0].metadata["station_id"] == "STATION-3"

    @pytest.mark.asyncio
    async def test_send_defect_alert_metadata_has_count(self):
        svc = _svc()
        messages = []
        async def capture(m): messages.append(m)
        svc.send = capture
        await svc.send_defect_alert("S1", "P1", defect_count=7)
        assert messages[0].metadata["defect_count"] == 7
