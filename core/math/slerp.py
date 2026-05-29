from __future__ import annotations

from typing import List

from .quaternion import Quaternion


def slerp(q1: Quaternion, q2: Quaternion, t: float) -> Quaternion:
    """Spherical linear interpolation between two quaternions."""
    return Quaternion.slerp(q1, q2, t)


def slerp_batch(q1: Quaternion, q2: Quaternion, steps: int = 12) -> List[Quaternion]:
    """Generate evenly distributed interpolation points for smooth rotation."""
    if steps < 1:
        return [q1.normalized()]
    return [slerp(q1, q2, i / steps) for i in range(steps + 1)]
