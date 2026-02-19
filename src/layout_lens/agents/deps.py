from __future__ import annotations

from dataclasses import dataclass

from layout_lens.core.settings import Settings
from layout_lens.core.geometry.geometry_service import GeometryService


@dataclass
class Deps:
    settings: Settings
    geometry_service: GeometryService
