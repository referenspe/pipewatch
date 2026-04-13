"""Human-readable and JSON reporting for AlertBudget state."""
from __future__ import annotations

import json
from typing import List

from pipewatch.budget import AlertBudget, BudgetResult


class BudgetReporter:
    def __init__(self, budget: AlertBudget) -> None:
        self._budget = budget

    def snapshot(self, keys: List[str]) -> List[BudgetResult]:
        """Return current budget state for each key without consuming budget."""
        return [self._budget.check(k) for k in keys]

    def has_exhausted(self, keys: List[str]) -> bool:
        return any(not r.allowed for r in self.snapshot(keys))

    def format_text(self, keys: List[str]) -> str:
        results = self.snapshot(keys)
        if not results:
            return "Budget: no keys tracked."
        lines = ["Alert Budget Report"]
        lines.append("-" * 30)
        for r in results:
            status = "OK" if r.allowed else "EXHAUSTED"
            lines.append(
                f"  [{status}] {r.key}: {r.used}/{r.limit} alerts "
                f"in last {r.window_seconds}s"
            )
        return "\n".join(lines)

    def format_json(self, keys: List[str]) -> str:
        results = self.snapshot(keys)
        return json.dumps([r.to_dict() for r in results], indent=2)
