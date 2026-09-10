from datetime import date
from unittest.mock import patch

import pytest

from src.copy_generator import PinCopy
from src.pinterest_client import PinterestAPIError
from src.pipeline import Pipeline


@pytest.fixture(autouse=True)
def no_real_sleep():
    with patch("src.pipeline.time.sleep"):
        yield


class FakeCatalog:
    def __init__(self, products):
        self._products = products

    def pick_for_date(self, target_date, count=3):
        return self._products[:count]


class FakeCopyGenerator:
    def __init__(self, safe=True):
        self.safe = safe
        self.calls = []

    def generate(self, product_name, language):
        self.calls.append((product_name, language))
        disclosure = "#PR" if language == "ja" else "#affiliate"
        if self.safe:
            return PinCopy(title=f"{product_name} タイトル", description=f"説明\n{disclosure}")
        return PinCopy(title="無関係なタイトル", description=f"無関係な説明\n{disclosure}")


class FakePinterestClient:
    def __init__(self, fail_times=0):
        self.calls = []
        self.fail_times = fail_times

    def create_pin(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.fail_times:
            raise PinterestAPIError("simulated failure")
        return {"id": f"pin_{len(self.calls)}"}


class FakeRunLogger:
    def __init__(self):
        self.recorded = []

    def record_run(self, run_date, results):
        self.recorded.append((run_date, results))


class FakeDiscord:
    def __init__(self):
        self.sent = []

    def send_embed(self, **kwargs):
        self.sent.append(kwargs)
        return True


PRODUCT = {
    "id": "p1",
    "name_ja": "カメラストラップ",
    "name_en": "Camera Strap",
    "category": "accessory",
    "a8net_link": "https://a8.example/p1",
    "overseas_link": {"name": "amazon_us", "url": "https://amazon.example/p1"},
}


def make_pipeline(copy_gen=None, pinterest_client=None):
    return Pipeline(
        catalog=FakeCatalog([PRODUCT]),
        copy_generator=copy_gen or FakeCopyGenerator(safe=True),
        pinterest_client=pinterest_client or FakePinterestClient(),
        run_logger=FakeRunLogger(),
        discord=FakeDiscord(),
        boards={"ja": "board_ja", "en": "board_en"},
    )


def test_run_posts_both_languages_and_logs_no_notification_on_success():
    pipeline = make_pipeline()
    images = {("p1", "ja"): b"img_ja", ("p1", "en"): b"img_en"}

    results = pipeline.run(date(2026, 9, 10), images, count=1)

    assert len(results) == 2
    assert all(r.status == "posted" for r in results)
    assert pipeline.discord.sent == []
    assert len(pipeline.run_logger.recorded) == 1


def test_run_marks_failed_when_image_missing():
    pipeline = make_pipeline()
    images = {("p1", "ja"): b"img_ja"}  # en画像なし

    results = pipeline.run(date(2026, 9, 10), images, count=1)

    en_result = next(r for r in results if r.language == "en")
    assert en_result.status == "failed"
    assert "image" in en_result.detail.lower()
    assert len(pipeline.discord.sent) == 1


def test_run_retries_and_succeeds_after_transient_pinterest_failure():
    pipeline = make_pipeline(pinterest_client=FakePinterestClient(fail_times=1))
    images = {("p1", "ja"): b"img_ja", ("p1", "en"): b"img_en"}

    results = pipeline.run(date(2026, 9, 10), images, count=1)

    assert all(r.status == "posted" for r in results)
    assert pipeline.discord.sent == []


def test_run_marks_failed_and_notifies_after_exhausting_retries():
    pipeline = make_pipeline(pinterest_client=FakePinterestClient(fail_times=99))
    images = {("p1", "ja"): b"img_ja", ("p1", "en"): b"img_en"}

    results = pipeline.run(date(2026, 9, 10), images, count=1)

    assert all(r.status == "failed" for r in results)
    assert len(pipeline.discord.sent) == 1


def test_run_marks_skipped_safety_when_copy_never_passes_check():
    pipeline = make_pipeline(copy_gen=FakeCopyGenerator(safe=False))
    images = {("p1", "ja"): b"img_ja", ("p1", "en"): b"img_en"}

    results = pipeline.run(date(2026, 9, 10), images, count=1)

    assert all(r.status == "skipped_safety" for r in results)
    assert len(pipeline.discord.sent) == 1
