"""
Simple warehouse route optimizer.

Strategy: S-shape traversal (standard wave picking).
  - Sort locations by (row, rack) alternating direction per row.
  - This minimises travel distance for a single operator with a list of picks.

For 4 rows, 3 dock points — TZ §7.6 step 3.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.warehouse import Location


@dataclass
class RouteStop:
    location: Location
    sequence: int


def optimise_route(locations: list[Location]) -> list[RouteStop]:
    """
    Given a set of pick locations, return them in S-shape traversal order.
    Locations without row/rack/tier info go at the end.
    """
    defined = [loc for loc in locations if loc.row is not None and loc.rack is not None]
    undefined = [loc for loc in locations if loc.row is None or loc.rack is None]

    # Group by row
    rows: dict[str, list[Location]] = {}
    for loc in defined:
        rows.setdefault(loc.row, []).append(loc)  # type: ignore[arg-type]

    ordered: list[Location] = []
    for i, (row_key, locs) in enumerate(sorted(rows.items())):
        # Alternate direction: even rows left→right, odd rows right→left
        locs_sorted = sorted(locs, key=lambda l: (l.rack or 0, l.tier or 0, l.position or 0))
        if i % 2 == 1:
            locs_sorted = list(reversed(locs_sorted))
        ordered.extend(locs_sorted)

    ordered.extend(undefined)

    return [RouteStop(location=loc, sequence=idx + 1) for idx, loc in enumerate(ordered)]
