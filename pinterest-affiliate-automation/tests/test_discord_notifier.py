import os
from unittest.mock import MagicMock, patch

from src.discord_notifier import DiscordNotifier


def test_is_configured_true_when_webhook_url_set():
    with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.example/webhook"}):
        notifier = DiscordNotifier()
        assert notifier.is_configured() is True


def test_send_embed_returns_false_when_not_configured():
    with patch.dict(os.environ, {}, clear=True):
        notifier = DiscordNotifier()
        assert notifier.send_embed(title="t", description="d") is False


def test_send_embed_posts_and_returns_true_on_204():
    notifier = DiscordNotifier(webhook_url="https://discord.example/webhook")
    with patch("src.discord_notifier.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = notifier.send_embed(
            title="Pinterest自動投稿: エラー発生", description="1件失敗しました"
        )
        assert result is True
