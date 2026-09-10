import json
from datetime import date
from pathlib import Path

import pytest

from src.catalog import ProductCatalog
from src.models import Product


def write_catalog(path: Path, products: list[dict]) -> Path:
    path.write_text(json.dumps({"products": products}), encoding="utf-8")
    return path


def sample_products(n: int) -> list[dict]:
    return [
        {
            "id": f"p{i}",
            "name_ja": f"商品{i}",
            "name_en": f"Product {i}",
            "category": "camera",
            "a8net_link": f"https://a8.example/p{i}",
            "overseas_link": {"name": "amazon_us", "url": f"https://amazon.example/p{i}"},
        }
        for i in range(n)
    ]


def test_pick_for_date_is_deterministic_for_same_date(tmp_path):
    path = write_catalog(tmp_path / "catalog.json", sample_products(5))
    catalog = ProductCatalog(path)
    picked1 = catalog.pick_for_date(date(2026, 9, 10), count=2)
    picked2 = catalog.pick_for_date(date(2026, 9, 10), count=2)
    assert picked1 == picked2
    assert len(picked1) == 2


def test_pick_for_date_rotates_across_days(tmp_path):
    path = write_catalog(tmp_path / "catalog.json", sample_products(5))
    catalog = ProductCatalog(path)
    picked_day1 = catalog.pick_for_date(date(2026, 9, 10), count=2)
    picked_day2 = catalog.pick_for_date(date(2026, 9, 11), count=2)
    assert picked_day1 != picked_day2


def test_pick_for_date_raises_on_empty_catalog(tmp_path):
    path = write_catalog(tmp_path / "catalog.json", [])
    catalog = ProductCatalog(path)
    with pytest.raises(ValueError):
        catalog.pick_for_date(date(2026, 9, 10), count=1)
