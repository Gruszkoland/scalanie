"""
ADRION 369 Ecosystem v2.0
==========================
Warstwa samodoskonalenia i ogrodnictwa poznawczego.

Moduły:
  antifragility     — silnik antykruchości (AntifragilityRegistry)
  attention_economy — ekonomia uwagi (AttentionBudget)
  playful_exploration — laboratorium spekulatywne (SandboxedPlayground)
  gardener          — orkiestrator integracyjny (Gardener)
"""

__version__ = "2.0.0"

from .antifragility import AntifragilityRegistry, MicroHeuristicPatch, RepairContext
from .attention_economy import AttentionBudget, UserAction, AttentionMode
from .playful_exploration import SandboxedPlayground, SpeculativeOutcome, RelaxedGuardians
from .gardener import Gardener

__all__ = [
    "AntifragilityRegistry",
    "MicroHeuristicPatch",
    "RepairContext",
    "AttentionBudget",
    "UserAction",
    "AttentionMode",
    "SandboxedPlayground",
    "SpeculativeOutcome",
    "RelaxedGuardians",
    "Gardener",
]
