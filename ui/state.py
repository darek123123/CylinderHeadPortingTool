from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class UIState:
    units: str = "SI"
    main_inputs: Dict[str, Any] = field(default_factory=dict)
    flow_header: Dict[str, Any] = field(default_factory=dict)
    flow_rows: List[Dict[str, Any]] = field(default_factory=list)
    A_points: List[Dict[str, Any]] = field(default_factory=list)
    B_points: List[Dict[str, Any]] = field(default_factory=list)
