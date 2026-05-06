# ADRION 369 — Multi-Agent AI Orchestration System
### *"If you only knew the magnificence of the 3, 6 and 9, then you would have the key to the universe."* — Nikola Tesla

**Version:** 5.7.1 (Industrial Security Grade)  
**Status:** 0 Critical Vulnerabilities | 243 Tests Passing  
**Language:** [🇵🇱 Polski](README_PL.md)

---

## 🔺 About
ADRION 369 is an advanced AI swarm orchestration system that replaces traditional hierarchical safety logic with **Distributed Ethics**. The system operates in a **162-dimensional decision space**, making it resistant to manipulation (jailbreaking) and single-point-of-failure (SPOF) errors.

### Key Difference: Distributed Ethics vs. Asimov's Laws
| Aspect | Traditional Laws (Asimov) | ADRION 369 |
| :--- | :--- | :--- |
| **Evaluation** | Sequential (1→2→3) | **Parallel** (3 perspectives simultaneously) |
| **Decision** | First matching rule | **Weighted balance** + dimensionality |
| **Transparency** | Implicit | **Glass-Box**: public weights and thresholds |
| **Privacy** | Undefined | **G7 Privacy**: measurable consent thresholds |
| **Harm Prevention** | Single rule | **G8 Nonmaleficence**: hard veto at 0.95 |

---

## 🏗️ The 3-6-9 Matrix Architecture
Every decision passes through a geometric filtration process:

1.  **Layer 3 (TRINITY):** Analysis from 3 perspectives:
    * **Material:** Resource efficiency and ROI.
    * **Intellectual:** Logic and algorithmic purity.
    * **Essential:** Alignment with mission and ethics.
2.  **Layer 6 (HEXAGON):** 6 operational modes (EBDI processes, state machine):
    * `Inventory` → `Empathy` → `Process` → `Debate` → `Healing` → `Action`
3.  **Layer 9 (GUARDIANS):** 9 Guardian Laws (G1-G9). **VETO System:** ≥2 violations or any CRITICAL law breach (G7, G8) = immediate **DENY**.

The tensor product **D^162 = P^3 ⊗ H^6 ⊗ G^9** maps every decision to a point in R^162, validated against all Guardian thresholds before execution.

---

## ⚙️ Technology Stack

### Core Modules (`core/`)
| Module | Purpose |
| :--- | :--- |
| `trinity.py` | Trinity Engine — 3-perspective scoring with immutability hardening |
| `decision_space_162d.py` | D^162 formalization — tensor product, Guardian projections, Skeptics Panel |
| `security_hardening.py` | G5/G7/G8 compliance, CVC counter, SecurityHardeningEngine |
| `superior_moral_code.py` | SAV+DSV pipeline — crisis modulation, dissonance detection, Genesis logging |
| `audit_trail.py` | Blockchain-ready SHA-256 hash-chained audit trail (G5 Transparency) |
| `escalation.py` | Human-in-the-loop escalation protocol — webhooks (Slack/Discord) |
| `redis_backend.py` | Redis/In-Memory storage backends for multi-instance deployments |
| `steganography_detector.py` | Pure Python FFT-based semantic steganography detection |

### Infrastructure
* **Vortex 1740:** EBDI state machine with 174Hz pulsation and Digital Root oracle.
* **MCP Layer (Ports 9000-9005):** 6 microservices:
    * `Router`, `Vortex`, `Guardian`, `Oracle`, `Genesis`, `Healer`.
* **Dashboard:** Streamlit + Plotly monitoring (`dashboard/app.py`) — Guardian radar, decision distribution, escalation log.

### Security Features
* Frozen objects (`MappingProxyType`, `__slots__`)
* Metaclass subclassing prevention
* Duck-typing and monkeypatch blocking
* FFT steganography detection (pure Python, no numpy)
* Hash-chained audit trail with tamper detection

---

## 📈 Version History
| Version | Critical Vulns | Tests | Key Changes |
| :--- | :---: | :---: | :--- |
| **5.0.0** | 19 | 0 | Initial system, 9 Laws, public weights. |
| **5.3.0** | 5 | 64 | Python core hardening, Grock report. |
| **5.6.0** | 0 | 107 | CVC, THREAT_MODEL, industrial vulnerability elimination. |
| **5.7.0** | 0 | 173 | D^162 formalization, FFT steganography, Redis, Superior Moral Code. |
| **5.7.1** | **0** | **243** | **Audit Trail (blockchain), Escalation Protocol, Trinity Sentinel Dashboard.** |

---

## 🔄 Decision Flow
```
Request → Trinity(3) → Hexagon(6) → Guardians(9) → 369 Signature → Response
```

The process concludes with a **369 Signature** that confirms the geometric integrity of computations via a digital root checksum.

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run stress tests
python -m pytest tests/test_stress_redis.py -v -s

# Launch dashboard
streamlit run dashboard/app.py
```

---

## 📚 Documentation
| File | Description |
| :--- | :--- |
| `docs/core/01_CORE_TRINITY.md` | Trinity System — 3 perspectives, 4 decision zones |
| `docs/core/02_CORE_HEXAGON.md` | Hexagon System — 6 modes, MAX_CYCLES→DENY |
| `docs/core/03_CORE_GUARDIANS.md` | Guardian System — 9 Laws, VETO threshold=2, CVC |
| `docs/core/04_CORE_EBDI.md` | EBDI Model — STRESS_FLOOR, PADTherapyDetector |
| `docs/THREAT_MODEL.md` | Formal threat model (STRIDE + AI-specific) |
| `docs/QUICKSTART.md` | Integration guide for Redis and MCP layer |
| `GUARDIAN_LAWS_CANONICAL.json` | Single source of truth for all 9 Guardian Laws + D^162 mapping |

---

*ADRION 369 — Multi-Agent AI Orchestration System*  
*Secure by Design. Transparent by Default.*  
*https://github.com/Gruszkoland/adrion-369-architecture*
