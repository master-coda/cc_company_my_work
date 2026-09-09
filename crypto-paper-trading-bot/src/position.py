from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Position:
    direction: Literal["long", "short"]
    entry_index: int
    entry_price: float
    stop_price: float
    target_price: Optional[float] = None
