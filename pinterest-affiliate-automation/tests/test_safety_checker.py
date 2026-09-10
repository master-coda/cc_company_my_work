import pytest

from src.safety_checker import check_copy_safety, hype_terms_for_language


def test_passes_when_disclosure_present_and_no_hype():
    result = check_copy_safety(
        product_name="Peak Design カメラストラップ",
        title="使いやすいカメラストラップ",
        description="長時間の撮影でも疲れにくいストラップです。\n#PR",
        disclosure_tag="#PR",
        hype_terms=hype_terms_for_language("ja"),
    )
    assert result.passed
    assert result.reasons == []


def test_fails_when_disclosure_missing():
    result = check_copy_safety(
        product_name="Peak Design カメラストラップ",
        title="使いやすいカメラストラップ",
        description="長時間の撮影でも疲れにくいストラップです。",
        disclosure_tag="#PR",
        hype_terms=hype_terms_for_language("ja"),
    )
    assert not result.passed
    assert any("disclosure" in r for r in result.reasons)


def test_fails_when_hype_term_present():
    result = check_copy_safety(
        product_name="Peak Design カメラストラップ",
        title="絶対に満足できます。",
        description="便利な小物です。\n#PR",
        disclosure_tag="#PR",
        hype_terms=hype_terms_for_language("ja"),
    )
    assert not result.passed
    assert any("hype" in r for r in result.reasons)


def test_passes_when_all_product_keywords_present():
    result = check_copy_safety(
        product_name="Peak Design",
        title="Peak Design カメラストラップ",
        description="便利な小物です。\n#PR",
        disclosure_tag="#PR",
        hype_terms=hype_terms_for_language("ja"),
    )
    assert result.passed
    assert result.reasons == []


def test_raises_for_unsupported_language():
    with pytest.raises(ValueError):
        hype_terms_for_language("invalid")
