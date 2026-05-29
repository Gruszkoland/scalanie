from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SeedEncoder:
    """Deterministyczny encoder seedow dla raportow skompresowanych."""

    digest_size: int = 8

    def encode(self, text: str) -> str:
        digest = hashlib.blake2b(text.encode("utf-8"), digest_size=self.digest_size).hexdigest()
        return f"SEED-{digest}"
