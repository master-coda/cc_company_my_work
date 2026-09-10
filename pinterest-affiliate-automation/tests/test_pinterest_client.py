import os
from unittest.mock import MagicMock, patch

import pytest

from src.pinterest_client import PinterestAPIError, PinterestClient


def test_missing_access_token_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            PinterestClient()


def test_create_pin_sends_expected_payload_and_returns_response():
    client = PinterestClient(access_token="token123")
    with patch("src.pinterest_client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "pin_1"})
        result = client.create_pin(
            board_id="board_ja",
            image_bytes=b"fake-image-bytes",
            content_type="image/jpeg",
            title="タイトル",
            description="説明文\n#PR",
            link="https://a8.example/p1",
        )
        assert result["id"] == "pin_1"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["board_id"] == "board_ja"
        assert payload["link"] == "https://a8.example/p1"
        assert payload["media_source"]["source_type"] == "image_base64"


def test_create_pin_raises_on_non_2xx_status():
    client = PinterestClient(access_token="token123")
    with patch("src.pinterest_client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, text="bad request")
        with pytest.raises(PinterestAPIError):
            client.create_pin(
                board_id="board_ja",
                image_bytes=b"fake-image-bytes",
                content_type="image/jpeg",
                title="タイトル",
                description="説明文",
                link="https://example.com",
            )


def test_list_boards_returns_items():
    client = PinterestClient(access_token="token123")
    with patch("src.pinterest_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"items": [{"id": "b1"}, {"id": "b2"}]}
        )
        boards = client.list_boards()
        assert len(boards) == 2
        assert boards[0]["id"] == "b1"
