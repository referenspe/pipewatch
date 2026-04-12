"""Text and JSON formatting for Digest objects."""
from __future__ import annotations

import json
from typing import List

from pipewatch.digest import Digest, DigestEntry
from pipewatch.metrics import MetricStatus

_STATUS_LABEL: dict = {
    MetricStatus.OK: "OK",
    MetricStatus.WARNING: "WARN",
    MetricStatus.CRITICAL: "CRIT",
}


class DigestReporter:
    """Formats a Digest for display or export."""

    def __init__(self, digest: Digest) -> None:
        self._digest = digest

    def has_alerts(self) -> bool:
        return self._digest.overall_status != MetricStatus.OK

    def format_text(self) -> str:
        d = self._digest
        lines: List[str] = [
            f"=== {d.title} ===",
            f"Generated : {d.generated_at.isoformat()}",
            f"Overall   : {_STATUS_LABEL[d.overall_status]}",
            f"Critical  : {d.critical_count}  Warning: {d.warning_count}  OK: {d.ok_count}",
            "-" * 48,
        ]
        if not d.entries:
            lines.append("  (no entries to display)")
        else:
            for entry in d.entries:
                label = _STATUS_LABEL[entry.status]
                avg = entry.summary.mean
                lines.append(
                    f"  [{label:4s}] {entry.metric_key:<30s}  avg={avg:.4g}"
                )
        lines.append("=" * 48)
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(self._digest.to_dict(), indent=2)
