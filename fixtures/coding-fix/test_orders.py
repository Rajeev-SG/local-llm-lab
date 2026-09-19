"""Acceptance checks for the coding-fix fixture.

Runnable with plain python3 (no pytest needed):
    python3 test_orders.py
Exits non-zero on the first failing check.
"""
import sys
from orders import LineItem, line_total, order_subtotal, apply_discount


def check_line_total_multiplies_quantity():
    assert line_total(LineItem("widget", 2.50, 4)) == 10.0


def check_order_subtotal_sums_lines():
    items = [LineItem("a", 2.50, 4), LineItem("b", 1.00, 3)]
    assert order_subtotal(items) == 13.0


def check_apply_discount_is_a_percentage():
    # 10% off 200.00 is 180.00 (not 190.00, which is subtracting a flat amount)
    assert apply_discount(200.0, 10.0) == 180.0


CHECKS = [
    check_line_total_multiplies_quantity,
    check_order_subtotal_sums_lines,
    check_apply_discount_is_a_percentage,
]


def main():
    failures = []
    for check in CHECKS:
        try:
            check()
            print(f"PASS {check.__name__}")
        except AssertionError as exc:
            failures.append(check.__name__)
            print(f"FAIL {check.__name__}: {exc!r}")
    if failures:
        print(f"{len(failures)}/{len(CHECKS)} checks failed")
        return 1
    print(f"all {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
