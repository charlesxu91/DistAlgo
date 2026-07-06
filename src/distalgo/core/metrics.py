from __future__ import annotations

from collections import defaultdict
from typing import Dict, Mapping, Tuple


class MetricsRegistry:
    def __init__(self):
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)

    def increment(self, name: str, value: float = 1.0, labels: Mapping[str, str] | None = None) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        self._counters[key] = value

    def to_prometheus_text(self) -> str:
        lines = []
        for (name, labels), value in sorted(self._counters.items()):
            label_text = ""
            if labels:
                rendered = ",".join(f'{key}="{val}"' for key, val in labels)
                label_text = "{" + rendered + "}"
            lines.append(f"{name}{label_text} {value}")
        return "\n".join(lines) + ("\n" if lines else "")
