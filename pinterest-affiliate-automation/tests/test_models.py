from datetime import date

from src.models import PostResult


def test_post_result_is_dataclass_with_expected_fields():
    result = PostResult(
        product_id="p1",
        language="ja",
        board_id="board_ja",
        pin_id="pin123",
        status="posted",
        detail="ok",
    )
    assert result.product_id == "p1"
    assert result.language == "ja"
    assert result.pin_id == "pin123"
    assert result.status == "posted"
