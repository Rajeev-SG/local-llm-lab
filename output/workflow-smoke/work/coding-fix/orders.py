"""Tiny order-total module used as a coding-fix fixture."""
from dataclasses import dataclass


@dataclass
class LineItem:
    name: str
    price: float
    quantity: int


def line_total(item: LineItem) -> float:
    return item.price * item.quantity


def order_subtotal(items):
    total = 0.0
    for item in items:
        total += line_total(item)
    return total


def apply_discount(subtotal: float, percent: float) -> float:
    return subtotal - subtotal * percent / 100

