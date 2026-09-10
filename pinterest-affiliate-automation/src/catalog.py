import json
from datetime import date
from pathlib import Path

from src.models import Product


class ProductCatalog:
    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        self.products: list[Product] = self._load()

    def _load(self) -> list[Product]:
        with open(self.catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        products = data.get("products", [])
        return products

    def pick_for_date(self, target_date: date, count: int = 3) -> list[Product]:
        if not self.products:
            raise ValueError("catalog is empty")

        start_index = target_date.toordinal() % len(self.products)
        return [
            self.products[(start_index + i) % len(self.products)] for i in range(count)
        ]
