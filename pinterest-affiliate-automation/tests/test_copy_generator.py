import pytest

from src.copy_generator import CopyGenerator


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, response_text):
        self.response_text = response_text
        self.calls = []

    def generate_content(self, model, contents):
        self.calls.append({"model": model, "contents": contents})
        return FakeResponse(self.response_text)


class FakeClient:
    def __init__(self, response_text):
        self.models = FakeModels(response_text)


def test_generate_returns_pin_copy_from_json_response():
    fake_client = FakeClient(
        '{"title": "Peak Design ストラップ", "description": "説明文です。\\n#PR"}'
    )
    gen = CopyGenerator(client=fake_client)
    copy = gen.generate("Peak Design ストラップ", "ja")
    assert copy.title == "Peak Design ストラップ"
    assert copy.description == "説明文です。\n#PR"


def test_generate_appends_nothing_extra_when_disclosure_already_present():
    fake_client = FakeClient('{"title": "商品", "description": "説明\\n#PR"}')
    gen = CopyGenerator(client=fake_client)
    copy = gen.generate("商品", "ja")
    assert copy.description.endswith("#PR")


def test_raises_when_json_missing_fields():
    gen = CopyGenerator(client=FakeClient("{}"))
    with pytest.raises(ValueError):
        gen.generate("Product", "en")


def test_raises_when_response_not_json():
    gen = CopyGenerator(client=FakeClient("not a json response at all"))
    with pytest.raises(ValueError):
        gen.generate("Product", "en")
