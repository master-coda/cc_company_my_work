"""
DiscordNotifier - Send notifications to Discord
"""
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord webhook notifier"""

    def __init__(self, webhook_url: Optional[str] = None):
        if webhook_url is None:
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

        if not webhook_url:
            logger.warning("Discord webhook URL not configured")
            self.webhook_url = None
        else:
            self.webhook_url = webhook_url
            logger.info("Discord notifier initialized")

    def is_configured(self) -> bool:
        """Check if Discord is configured"""
        return self.webhook_url is not None

    def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,
        fields: Optional[Dict[str, str]] = None,
        footer: Optional[str] = None,
    ) -> bool:
        """Send embed message to Discord. Returns True if sent successfully."""
        if not self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False

        try:
            embed: Dict[str, Any] = {
                "title": title,
                "description": description,
                "color": color,
            }

            if fields:
                embed["fields"] = [
                    {"name": k, "value": v, "inline": False} for k, v in fields.items()
                ]

            if footer:
                embed["footer"] = {"text": footer}

            payload = {"embeds": [embed]}

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url, data=data, headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 204:
                    logger.info("Discord embed sent successfully")
                    return True
                else:
                    logger.error(f"Discord returned status {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            logger.error(f"Discord HTTP error: {e.code} {e.reason}")
            return False
        except urllib.error.URLError as e:
            logger.error(f"Discord connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending Discord embed: {str(e)}")
            return False
