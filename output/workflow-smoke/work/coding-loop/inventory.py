"""Warehouse inventory fixture (medium agentic task).

Known-good target behaviour is encoded in run_checks.py.
"""
from dataclasses import dataclass, field


@dataclass
class Batch:
    sku: str
    qty: int
    unit_cost: float


@dataclass
class Warehouse:
    batches: list = field(default_factory=list)

    def add(self, batch: Batch):
        self.batches.append(batch)

    def quantity_of(self, sku: str) -> int:
        return sum(b.qty for b in self.batches if b.sku == sku)

    def total_value(self) -> float:
        return sum(b.qty * b.unit_cost for b in self.batches)

    def remove_sku(self, sku: str) -> int:
        """Remove all batches for sku; return removed quantity."""
        removed = sum(b.qty for b in self.batches if b.sku == sku)
        self.batches = [b for b in self.batches if b.sku != sku]
        return removed

    def average_unit_cost(self, sku: str) -> float:
        """Quantity-weighted average unit cost for sku; 0.0 if absent."""
        matching = [b for b in self.batches if b.sku == sku]
        total_qty = sum(b.qty for b in matching)
        if total_qty == 0:
            return 0.0
        return sum(b.qty * b.unit_cost for b in matching) / total_qty
