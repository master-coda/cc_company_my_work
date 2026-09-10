import base64
import os

import requests

API_BASE = "https://api.pinterest.com/v5"


class PinterestAPIError(Exception):
    pass


class PinterestClient:
    def __init__(self, access_token=None, base_url=API_BASE):
        self.access_token = access_token or os.getenv("PINTEREST_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("PINTEREST_ACCESS_TOKEN is not set")
        self.base_url = base_url

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def list_boards(self) -> list[dict]:
        resp = requests.get(f"{self.base_url}/boards", headers=self._headers(), timeout=15)
        if resp.status_code != 200:
            raise PinterestAPIError(f"list_boards failed: {resp.status_code} {resp.text}")
        return resp.json().get("items", [])

    def create_pin(
        self,
        board_id: str,
        image_bytes: bytes,
        content_type: str,
        title: str,
        description: str,
        link: str,
        alt_text: str = "",
    ) -> dict:
        payload = {
            "board_id": board_id,
            "media_source": {
                "source_type": "image_base64",
                "content_type": content_type,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
            "title": title[:100],
            "description": description[:500],
            "link": link,
            "alt_text": (alt_text or title)[:500],
        }
        resp = requests.post(
            f"{self.base_url}/pins", headers=self._headers(), json=payload, timeout=30
        )
        if resp.status_code not in (200, 201):
            raise PinterestAPIError(f"create_pin failed: {resp.status_code} {resp.text}")
        return resp.json()

    def get_pin_analytics(self, pin_id: str, start_date: str, end_date: str) -> dict:
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "metric_types": "IMPRESSION,PIN_CLICK,OUTBOUND_CLICK",
        }
        resp = requests.get(
            f"{self.base_url}/pins/{pin_id}/analytics",
            headers=self._headers(),
            params=params,
            timeout=15,
        )
        if resp.status_code != 200:
            raise PinterestAPIError(
                f"get_pin_analytics failed: {resp.status_code} {resp.text}"
            )
        return resp.json()
