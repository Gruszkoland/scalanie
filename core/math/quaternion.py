from __future__ import annotations

from dataclasses import dataclass
from math import acos, cos, sin, sqrt


@dataclass(frozen=True)
class Quaternion:
    """Minimalna implementacja kwaternionu pod rotacje stanu."""

    w: float
    x: float
    y: float
    z: float

    def norm(self) -> float:
        return sqrt(self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> "Quaternion":
        n = self.norm()
        if n == 0.0:
            raise ValueError("Nie mozna znormalizowac zerowego kwaternionu")
        return Quaternion(self.w / n, self.x / n, self.y / n, self.z / n)

    def dot(self, other: "Quaternion") -> float:
        return self.w * other.w + self.x * other.x + self.y * other.y + self.z * other.z

    def __mul__(self, other: "Quaternion") -> "Quaternion":
        return Quaternion(
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
        )

    @staticmethod
    def identity() -> "Quaternion":
        return Quaternion(1.0, 0.0, 0.0, 0.0)

    @staticmethod
    def from_axis_angle(axis: tuple[float, float, float], angle_rad: float) -> "Quaternion":
        ax, ay, az = axis
        magnitude = sqrt(ax * ax + ay * ay + az * az)
        if magnitude == 0.0:
            raise ValueError("Os obrotu nie moze byc zerowa")
        ux, uy, uz = ax / magnitude, ay / magnitude, az / magnitude
        half = angle_rad / 2.0
        s = sin(half)
        return Quaternion(cos(half), ux * s, uy * s, uz * s).normalized()

    @staticmethod
    def slerp(a: "Quaternion", b: "Quaternion", t: float) -> "Quaternion":
        if t <= 0.0:
            return a.normalized()
        if t >= 1.0:
            return b.normalized()

        qa = a.normalized()
        qb = b.normalized()
        cos_theta = qa.dot(qb)

        if cos_theta < 0.0:
            qb = Quaternion(-qb.w, -qb.x, -qb.y, -qb.z)
            cos_theta = -cos_theta

        if cos_theta > 0.9995:
            # Near-linear interpolation for numerical stability.
            w = qa.w + t * (qb.w - qa.w)
            x = qa.x + t * (qb.x - qa.x)
            y = qa.y + t * (qb.y - qa.y)
            z = qa.z + t * (qb.z - qa.z)
            return Quaternion(w, x, y, z).normalized()

        theta = acos(max(-1.0, min(1.0, cos_theta)))
        sin_theta = sin(theta)
        a_factor = sin((1.0 - t) * theta) / sin_theta
        b_factor = sin(t * theta) / sin_theta
        return Quaternion(
            qa.w * a_factor + qb.w * b_factor,
            qa.x * a_factor + qb.x * b_factor,
            qa.y * a_factor + qb.y * b_factor,
            qa.z * a_factor + qb.z * b_factor,
        ).normalized()
