"""V5 M11 isolated intraday research review capsule.

This package owns only M11 artifacts and does not replace shared V4/V5 services.
"""

from .intraday_capsule import IntradayCapsuleStore, M11Slot

__all__ = ["IntradayCapsuleStore", "M11Slot"]
