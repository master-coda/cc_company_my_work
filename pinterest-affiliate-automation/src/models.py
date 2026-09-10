from dataclasses import dataclass
from typing import TypedDict


class ASPLink(TypedDict):
    name: str
    url: str


class Product(TypedDict):
    id: str
    name_ja: str
    name_en: str
    category: str
    a8net_link: str
    overseas_link: ASPLink


@dataclass
class PostResult:
    product_id: str
    language: str
    board_id: str
    pin_id: str | None
    status: str  # "posted" | "skipped_safety" | "failed"
    detail: str
