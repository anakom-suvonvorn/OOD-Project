"""Text menu (owner: P5). The only place that uses print() / input().

Every core call is wrapped so a HotelError is shown as a message and the menu keeps running.
Large lists show the first 50 rows plus the total count.
"""
from __future__ import annotations

from hotel import HotelError, HotelSystem


class Menu:
    def __init__(self) -> None:
        self.system: HotelSystem | None = None

    def run(self) -> None:
        """Main loop. Options (see PLAN.md section 8.6):
        1 new system, 2 add guest, 3 add batch, 4 remove guest, 5 add building,
        6 remove building, 7 find by guest id, 8 find by room, 9 list rooms,
        10 load report, 11 benchmark, 12 compare with hash mod N, 13 export CSV, 0 quit."""
        raise NotImplementedError("P5")
