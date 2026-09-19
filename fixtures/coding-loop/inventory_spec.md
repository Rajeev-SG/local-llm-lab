# Task spec: Warehouse inventory

`inventory.py` defines `Batch`, `Warehouse`, and several methods. Two methods are
stubs that return wrong placeholder values:

- `Warehouse.remove_sku(sku)` must remove every batch with that SKU and return the
  total quantity removed. Currently it removes nothing and returns 0.
- `Warehouse.average_unit_cost(sku)` must return the quantity-weighted average unit
  cost for that SKU, or `0.0` when the SKU is absent. Currently it always returns 0.0.

Make `run_checks.py` pass. Run it with `python3 run_checks.py`.
