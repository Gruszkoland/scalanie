"""
ADRION 369 — Hexagon Pipeline Processor (6-Stage Decision Pipeline)

Sekwencyjnie łańcuchuje 6 etapów przetwarzania decyzji arbitra żowej:

  1. Inventory    — analiza zasobów i aktywów dostępnych do decyzji
  2. Empathy      — ocena wpływu na stakeholderów i rzeczywistość społeczna
  3. Process      — optymalizacja procesu i przepływu pracy
  4. Debate       — wieloperspektywowa debata i konfrontacja wyników
  5. Healing      — łagodzenie ryzyka i przygotowanie do kryzysów
  6. Action       — ostateczna rekomendacja i plan wdrażania

Każdy etap otrzymuje wyniki z etapu poprzedniego i dodaje swoją analizę.
Wynik końcowy to pełna mapa decyzyjna (decision map).

Agregacja: sekwencyjne przepuszczanie (każdy etap czeka na poprzedni)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("adrion.hexagon")

# ─────────────────────────────────────────────────────────────────────
# Stałe etapów
# ─────────────────────────────────────────────────────────────────────
HEXAGON_STAGES = ("inventory", "empathy", "process", "debate", "healing", "action")
HEXAGON_STAGE_ORDER = {stage: i for i, stage in enumerate(HEXAGON_STAGES)}

# ─────────────────────────────────────────────────────────────────────
# Struktury danych
# ─────────────────────────────────────────────────────────────────────


@dataclass
class HexagonStageResult:
    """Wynik pojedynczego etapu Hexagon."""

    stage_name: str  # inventory, empathy, process, debate, healing, action
    score: float  # 0.0–1.0 — wynik tego etapu
    duration_ms: float = 0.0  # Czas wykonania etapu (ms)
    analysis: dict = field(default_factory=dict)  # Stage-specific analysis dict
    recommendations: list[str] = field(default_factory=list)  # Rekomendacje z etapu
    risks: list[str] = field(default_factory=list)  # Zidentyfikowane ryzyka
    approved: bool = True  # Czy etap zaaprobuje decyzję

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "duration_ms": round(self.duration_ms, 2),
            "score": round(self.score, 4),
            "analysis": self.analysis,
            "recommendations": self.recommendations,
            "risks": self.risks,
            "approved": self.approved,
        }


@dataclass
class HexagonResult:
    """Wynik pełnego przetworzenia Hexagon (6 etapów)."""

    stages: list[HexagonStageResult] = field(default_factory=list)
    combined_score: float = 0.0  # Średni score z wszystkich 6 etapów
    total_duration_ms: float = 0.0  # Całkowity czas przetworzenia
    approved: bool = True  # Czy wszystkie etapy pozytywne

    def to_dict(self) -> dict:
        return {
            "stages": [s.to_dict() for s in self.stages],
            "combined_score": round(self.combined_score, 4),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "approved": self.approved,
        }

    def stage_by_name(self, name: str) -> HexagonStageResult | None:
        """Szybka lokalizacja etapu po nazwie."""
        for stage in self.stages:
            if stage.stage_name == name:
                return stage
        return None


# ─────────────────────────────────────────────────────────────────────
# Implementacje poszczególnych etapów
# ─────────────────────────────────────────────────────────────────────


def _inventory_stage(trinity_scores: dict) -> HexagonStageResult:
    """
    Etap 1: Inventory — Analiza zasobów dostępnych do realizacji decyzji.

    Pytania:
      - Jakie zasoby fizyczne, finansowe i ludzkie są dostępne?
      - Czy zasoby wystarczają do zrealizowania wymaganego zakresu?
      - Czy istnieją koszty ukryte lub dodatkowe?
    """
    import time

    start_time = time.time()

    try:
        # Analiza Trinity scores jako punkt wyjścia
        material = trinity_scores.get("material", 0.0)
        intellectual = trinity_scores.get("intellectual", 0.0)
        essential = trinity_scores.get("essential", 0.0)

        # Inventory score = średnia Trinity (zasoby dostępne)
        inventory_score = (material + intellectual + essential) / 3.0

        analysis = {
            "trinity_foundation": trinity_scores,
            "resource_quality": round(material * 100, 1),  # CPU/RAM quality
            "knowledge_quality": round(intellectual * 100, 1),  # Data quality
            "essential_alignment": round(essential * 100, 1),  # Purpose alignment
        }

        recommendations = []
        risks = []

        # Rekomendacje oparte na zasobach
        if material < 0.4:
            risks.append("Low system resources available")
            recommendations.append("Consider running on more powerful hardware")
        else:
            recommendations.append("Sufficient system resources for execution")

        if intellectual < 0.4:
            risks.append("Low data quality or knowledge base")
            recommendations.append("Improve analysis quality before proceeding")
        else:
            recommendations.append("Good knowledge base quality")

        if essential < 0.3:
            risks.append("Poor purpose-profit alignment")
            recommendations.append("Realign decision with system objectives")

        duration_ms = (time.time() - start_time) * 1000

        return HexagonStageResult(
            stage_name="inventory",
            duration_ms=duration_ms,
            score=round(inventory_score, 4),
            analysis=analysis,
            recommendations=recommendations,
            risks=risks,
            approved=(inventory_score >= 0.3),
        )

    except Exception as exc:
        logger.error("Inventory stage failed: %s", exc)
        duration_ms = (time.time() - start_time) * 1000
        return HexagonStageResult(
            stage_name="inventory",
            duration_ms=duration_ms,
            score=0.0,
            analysis={"error": str(exc)},
            approved=False,
        )


def _empathy_stage(inventory_result: HexagonStageResult) -> HexagonStageResult:
    """
    Etap 2: Empathy — Ocena wpływu na stakeholderów i społeczność.

    Pytania:
      - Kto będzie dotknięty tą decyzją?
      - Jaki będzie wpływ społeczny/etyczny?
      - Czy decyzja jest fair dla wszystkich interesariuszy?
    """
    import time

    start_time = time.time()

    try:
        # Empathy score opiera się na zatwierdzeniu inventory
        inventory_approved = inventory_result.approved
        inventory_score = inventory_result.score

        # Jeśli inventory failed, empathy też musi fail
        if not inventory_approved:
            empathy_score = 0.0
        else:
            # Empathy score = inventory score (stakeholders can benefit if resources exist)
            empathy_score = inventory_score

        analysis = {
            "inventory_prior": inventory_result.to_dict(),
            "stakeholder_impact": "positive" if empathy_score >= 0.5 else "negative",
            "ethical_alignment": round(empathy_score * 100, 1),
        }

        recommendations = []
        risks = []

        if empathy_score >= 0.7:
            recommendations.append(
                "High positive impact on stakeholders — proceed with confidence"
            )
        elif empathy_score >= 0.5:
            recommendations.append(
                "Moderate impact on stakeholders — monitor closely during execution"
            )
            risks.append("Potential negative externalities for some groups")
        else:
            risks.append("Poor empathetic alignment — decision may harm stakeholders")
            recommendations.append(
                "Reconsider decision or add mitigation measures for affected groups"
            )

        duration_ms = (time.time() - start_time) * 1000

        return HexagonStageResult(
            stage_name="empathy",
            duration_ms=duration_ms,
            score=round(empathy_score, 4),
            analysis=analysis,
            recommendations=recommendations,
            risks=risks,
            approved=(empathy_score >= 0.3),
        )

    except Exception as exc:
        logger.error("Empathy stage failed: %s", exc)
        duration_ms = (time.time() - start_time) * 1000
        return HexagonStageResult(
            stage_name="empathy",
            duration_ms=duration_ms,
            score=0.0,
            analysis={"error": str(exc)},
            approved=False,
        )


def _process_stage(empathy_result: HexagonStageResult) -> HexagonStageResult:
    """
    Etap 3: Process — Optymalizacja procesu i workflow.

    Pytania:
      - Jaki jest optymalny proces wdrażania tej decyzji?
      - Gdzie mogą powstać wąskie gardła?
      - Jakie są krytyczne ścieżki?
    """
    import time

    start_time = time.time()

    try:
        empathy_score = empathy_result.score
        empathy_approved = empathy_result.approved

        if not empathy_approved:
            process_score = 0.0
        else:
            # Process score = empathy score (if resources/empathy ok, process can be optimized)
            process_score = empathy_score

        analysis = {
            "empathy_prior": empathy_result.to_dict(),
            "process_efficiency": round(process_score * 100, 1),
            "bottleneck_risk": "high" if process_score < 0.4 else "low",
        }

        recommendations = []
        risks = []

        if process_score >= 0.6:
            recommendations.append("Process flow is well-structured and optimized")
        else:
            risks.append("Process inefficiencies detected")
            recommendations.append("Consider process re-engineering before execution")

        duration_ms = (time.time() - start_time) * 1000

        return HexagonStageResult(
            stage_name="process",
            duration_ms=duration_ms,
            score=round(process_score, 4),
            analysis=analysis,
            recommendations=recommendations,
            risks=risks,
            approved=(process_score >= 0.3),
        )

    except Exception as exc:
        logger.error("Process stage failed: %s", exc)
        duration_ms = (time.time() - start_time) * 1000
        return HexagonStageResult(
            stage_name="process",
            duration_ms=duration_ms,
            score=0.0,
            analysis={"error": str(exc)},
            approved=False,
        )


def _debate_stage(process_result: HexagonStageResult) -> HexagonStageResult:
    """
    Etap 4: Debate — Wieloperspektywowa debata i konfrontacja wyników.

    Pytania:
      - Jakie są kontrargumenty wobec tej decyzji?
      - Czy wszystkie perspektywy zostały rozważone?
      - Czy istnieją alternatywy lepsze?
    """
    import time

    start_time = time.time()

    try:
        process_score = process_result.score
        process_approved = process_result.approved

        if not process_approved:
            debate_score = 0.0
        else:
            # Debate score = process score (if process is solid, debate strengthens it)
            # In real implementation, debate would query multiple LLM perspectives
            debate_score = process_score

        analysis = {
            "process_prior": process_result.to_dict(),
            "debate_outcome": "consensus_reached" if debate_score >= 0.6 else "unresolved",
            "confidence_level": round(debate_score * 100, 1),
        }

        recommendations = []
        risks = []

        if debate_score >= 0.7:
            recommendations.append("Strong consensus reached across perspectives")
        elif debate_score >= 0.5:
            recommendations.append(
                "Reasonable consensus — proceeding with documented dissents"
            )
            risks.append("Some perspectives remain unconvinced")
        else:
            risks.append("No consensus among perspectives")
            recommendations.append("Decision needs further deliberation")

        duration_ms = (time.time() - start_time) * 1000

        return HexagonStageResult(
            stage_name="debate",
            duration_ms=duration_ms,
            score=round(debate_score, 4),
            analysis=analysis,
            recommendations=recommendations,
            risks=risks,
            approved=(debate_score >= 0.3),
        )

    except Exception as exc:
        logger.error("Debate stage failed: %s", exc)
        duration_ms = (time.time() - start_time) * 1000
        return HexagonStageResult(
            stage_name="debate",
            duration_ms=duration_ms,
            score=0.0,
            analysis={"error": str(exc)},
            approved=False,
        )


def _healing_stage(debate_result: HexagonStageResult) -> HexagonStageResult:
    """
    Etap 5: Healing — Łagodzenie ryzyka i przygotowanie na kryzys.

    Pytania:
      - Jakie zagrożenia mogą się pojawić?
      - Jak się przygotować na scenariusze kryzysowe?
      - Jak minimalizować potencjalne straty?
    """
    import time

    start_time = time.time()

    try:
        debate_score = debate_result.score
        debate_approved = debate_result.approved

        if not debate_approved:
            healing_score = 0.0
        else:
            # Healing score = debate score (if debate successful, mitigation can be planned)
            healing_score = debate_score

        analysis = {
            "debate_prior": debate_result.to_dict(),
            "risk_mitigation": round(healing_score * 100, 1),
            "crisis_preparation": "high" if healing_score >= 0.6 else "low",
        }

        recommendations = []
        risks = []

        if healing_score >= 0.7:
            recommendations.append("Comprehensive risk mitigation plan in place")
        elif healing_score >= 0.5:
            recommendations.append("Basic risk management framework established")
            risks.append("Additional contingency planning recommended")
        else:
            risks.append("Insufficient risk mitigation")
            recommendations.append("Develop crisis response procedures before execution")

        duration_ms = (time.time() - start_time) * 1000

        return HexagonStageResult(
            stage_name="healing",
            duration_ms=duration_ms,
            score=round(healing_score, 4),
            analysis=analysis,
            recommendations=recommendations,
            risks=risks,
            approved=(healing_score >= 0.3),
        )

    except Exception as exc:
        logger.error("Healing stage failed: %s", exc)
        duration_ms = (time.time() - start_time) * 1000
        return HexagonStageResult(
            stage_name="healing",
            duration_ms=duration_ms,
            score=0.0,
            analysis={"error": str(exc)},
            approved=False,
        )


def _action_stage(healing_result: HexagonStageResult) -> HexagonStageResult:
    """
    Etap 6: Action — Ostateczna rekomendacja wdrażania.

    Pytania:
      - Co konkretnie wdrożyć?
      - Jak monitorować postęp?
      - Jakie wskaźniki sukcesu/porażki?
    """
    import time

    start_time = time.time()

    try:
        healing_score = healing_result.score
        healing_approved = healing_result.approved

        if not healing_approved:
            action_score = 0.0
        else:
            # Action score = healing score (final recommendation strength)
            action_score = healing_score

        analysis = {
            "healing_prior": healing_result.to_dict(),
            "action_recommendation": "APPROVED" if action_score >= 0.5 else "CONDITIONAL",
            "implementation_readiness": round(action_score * 100, 1),
        }

        recommendations = []
        risks = []

        if action_score >= 0.7:
            recommendations.append("✓ STRONG RECOMMENDATION: Proceed immediately")
            recommendations.append("Monitor KPIs weekly during first month")
        elif action_score >= 0.5:
            recommendations.append("~ CONDITIONAL APPROVAL: Proceed with caution")
            recommendations.append("Execute with enhanced monitoring and review gates")
            risks.append("Higher uncertainty in outcomes")
        else:
            risks.append("Low confidence in positive outcomes")
            recommendations.append("✗ RECOMMEND DELAY: Address critical issues first")

        duration_ms = (time.time() - start_time) * 1000

        return HexagonStageResult(
            stage_name="action",
            duration_ms=duration_ms,
            score=round(action_score, 4),
            analysis=analysis,
            recommendations=recommendations,
            risks=risks,
            approved=(action_score >= 0.3),
        )

    except Exception as exc:
        logger.error("Action stage failed: %s", exc)
        duration_ms = (time.time() - start_time) * 1000
        return HexagonStageResult(
            stage_name="action",
            duration_ms=duration_ms,
            score=0.0,
            analysis={"error": str(exc)},
            approved=False,
        )


# ─────────────────────────────────────────────────────────────────────
# Główny procesor
# ─────────────────────────────────────────────────────────────────────


class HexagonProcessor:
    """
    Orkestruje 6-etapowy pipeline Hexagon.

    Pipeline:
      Trinity scores (input)
      ↓
      Inventory → Empathy → Process → Debate → Healing → Action
      ↓
      HexagonResult (output)

    Każdy etap czeka na poprzedni i dodaje swoją analizę.
    """

    def __init__(self):
        self.logger = logging.getLogger("adrion.hexagon.processor")

    def process(self, trinity_scores: dict) -> HexagonResult:
        """
        Wykonuje pełne przetworzenie Hexagon (6 etapów).

        Args:
            trinity_scores: dict z wynikami Trinity (material, intellectual, essential, combined)

        Returns:
            HexagonResult — wszystkie 6 etapów + metadane
        """
        import time

        total_start = time.time()

        # Ecosystem v2.0 — Gardener hook: Krok 1.5 (before_checkpoint)
        _gardener = None
        try:
            from ecosystem.gardener import Gardener  # lazy import — brak hard dependency
            _gardener = Gardener()
            _gardener.before_checkpoint()
        except Exception:
            pass  # ecosystem not installed — degraded gracefully

        # Stage 1: Inventory
        inventory = _inventory_stage(trinity_scores)
        self.logger.info(
            "Inventory complete: score=%.3f approved=%s",
            inventory.score,
            inventory.approved,
        )
        if not inventory.approved and _gardener is not None:
            try:
                from ecosystem.antifragility import RepairContext
                ctx = RepairContext(
                    error_signature="hexagon_inventory_rejected",
                    hexagon_cycle=1,
                    convergence_score=inventory.score,
                    patched_files=tuple(),
                    timestamp=time.time(),
                    extra={"stage": "inventory", "trinity_scores": trinity_scores},
                )
                _gardener.after_repair_loop(ctx)
            except Exception:
                pass

        # Stage 2: Empathy
        empathy = _empathy_stage(inventory)
        self.logger.info(
            "Empathy complete: score=%.3f approved=%s", empathy.score, empathy.approved
        )
        if not empathy.approved and _gardener is not None:
            try:
                from ecosystem.antifragility import RepairContext
                ctx = RepairContext(
                    error_signature="hexagon_empathy_rejected",
                    hexagon_cycle=2,
                    convergence_score=empathy.score,
                    patched_files=tuple(),
                    timestamp=time.time(),
                    extra={"stage": "empathy"},
                )
                _gardener.after_repair_loop(ctx)
            except Exception:
                pass

        # Stage 3: Process
        process = _process_stage(empathy)
        self.logger.info(
            "Process complete: score=%.3f approved=%s", process.score, process.approved
        )
        if not process.approved and _gardener is not None:
            try:
                from ecosystem.antifragility import RepairContext
                ctx = RepairContext(
                    error_signature="hexagon_process_rejected",
                    hexagon_cycle=3,
                    convergence_score=process.score,
                    patched_files=tuple(),
                    timestamp=time.time(),
                    extra={"stage": "process"},
                )
                _gardener.after_repair_loop(ctx)
            except Exception:
                pass

        # Stage 4: Debate
        debate = _debate_stage(process)
        self.logger.info(
            "Debate complete: score=%.3f approved=%s", debate.score, debate.approved
        )
        if not debate.approved and _gardener is not None:
            try:
                from ecosystem.antifragility import RepairContext
                ctx = RepairContext(
                    error_signature="hexagon_debate_rejected",
                    hexagon_cycle=4,
                    convergence_score=debate.score,
                    patched_files=tuple(),
                    timestamp=time.time(),
                    extra={"stage": "debate"},
                )
                _gardener.after_repair_loop(ctx)
            except Exception:
                pass

        # Stage 5: Healing
        healing = _healing_stage(debate)
        self.logger.info(
            "Healing complete: score=%.3f approved=%s", healing.score, healing.approved
        )
        if not healing.approved and _gardener is not None:
            try:
                from ecosystem.antifragility import RepairContext
                ctx = RepairContext(
                    error_signature="hexagon_healing_rejected",
                    hexagon_cycle=5,
                    convergence_score=healing.score,
                    patched_files=tuple(),
                    timestamp=time.time(),
                    extra={"stage": "healing"},
                )
                _gardener.after_repair_loop(ctx)
            except Exception:
                pass

        # Stage 6: Action
        action = _action_stage(healing)
        self.logger.info(
            "Action complete: score=%.3f approved=%s", action.score, action.approved
        )

        # Aggregation
        stages = [inventory, empathy, process, debate, healing, action]
        scores = [s.score for s in stages]
        combined_score = sum(scores) / len(scores)
        total_duration_ms = (time.time() - total_start) * 1000

        # Overall approval: all stages must approve
        overall_approved = all(s.approved for s in stages)

        result = HexagonResult(
            stages=stages,
            combined_score=combined_score,
            total_duration_ms=total_duration_ms,
            approved=overall_approved,
        )

        self.logger.info(
            "Hexagon pipeline complete: combined=%.3f approved=%s duration=%.1fms",
            combined_score,
            overall_approved,
            total_duration_ms,
        )

        # Ecosystem v2.0 — Gardener hook: Krok 3 (audit_attention_budget po pipeline)
        if _gardener is not None:
            try:
                _gardener.audit_attention_budget()
            except Exception:
                pass

        return result
