"""Acceptance checks for the medium agentic coding fixture.

python3 run_checks.py  -> exit 0 only when the task is fully complete.
"""
import sys
from inventory import Batch, Warehouse


def new_warehouse():
    w = Warehouse()
    w.add(Batch("A1", 10, 2.0))
    w.add(Batch("A1", 5, 4.0))
    w.add(Batch("B2", 7, 1.0))
    return w


def check_remove_sku_returns_quantity():
    w = new_warehouse()
    removed = w.remove_sku("A1")
    assert removed == 15, f"expected 15 removed, got {removed}"
    assert w.quantity_of("A1") == 0
    assert w.quantity_of("B2") == 7


def check_total_value_unchanged_after_remove():
    w = new_warehouse()
    w.remove_sku("A1")
    assert w.total_value() == 7.0


def check_average_unit_cost_weighted():
    w = new_warehouse()
    # (10*2 + 5*4)/15 = 40/15 = 2.666...
    got = w.average_unit_cost("A1")
    assert abs(got - (40.0 / 15.0)) < 1e-9, f"got {got}"


def check_average_missing_sku_is_zero():
    w = new_warehouse()
    assert w.average_unit_cost("ZZ") == 0.0


CHECKS = [
    check_remove_sku_returns_quantity,
    check_total_value_unchanged_after_remove,
    check_average_unit_cost_weighted,
    check_average_missing_sku_is_zero,
]


def main():
    failures = []
    for c in CHECKS:
        try:
            c()
            print(f"PASS {c.__name__}")
        except AssertionError as exc:
            failures.append(c.__name__)
            print(f"FAIL {c.__name__}: {exc}")
    if failures:
        print(f"{len(failures)}/{len(CHECKS)} checks failed")
        return 1
    print(f"all {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
