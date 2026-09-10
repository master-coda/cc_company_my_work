import json
from dataclasses import dataclass

MODEL = "gemini-2.5-flash"

DISCLOSURE_JA = "#PR"
DISCLOSURE_EN = "#affiliate"

_PROMPT_TEMPLATE = """You are writing a Pinterest pin for an affiliate camera-gear listing.
Product name: {product_name}
Language: {lang_label}
Write a concise, keyword-rich Pinterest title (max 100 characters) and a
description (max 500 characters) that would rank well in Pinterest search for
someone shopping for this kind of product. Only mention the literal
product name given, no other brand claims. End the description with the
disclosure tag on its own line: {disclosure}
Respond with JSON only, no markdown fences: {{"title": "...", "description": "..."}}"""


@dataclass
class PinCopy:
    title: str
    description: str


class CopyGenerator:
    def __init__(self, client=None):
        if client is None:
            from google import genai

            client = genai.Client()
        self.client = client

    def generate(self, product_name: str, language: str) -> PinCopy:
        if language not in ("ja", "en"):
            raise ValueError(f"unsupported language: {language}")
        disclosure = DISCLOSURE_JA if language == "ja" else DISCLOSURE_EN
        lang_label = "Japanese" if language == "ja" else "English"
        prompt = _PROMPT_TEMPLATE.format(
            product_name=product_name, lang_label=lang_label, disclosure=disclosure
        )
        response = self.client.models.generate_content(model=MODEL, contents=prompt)
        data = _extract_json(response.text)
        if "title" not in data or "description" not in data:
            raise ValueError(f"response missing title/description: {data}")
        return PinCopy(title=data["title"], description=data["description"])


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object found in response: {text}")
    return json.loads(text[start : end + 1])
