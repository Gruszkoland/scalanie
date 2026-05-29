# ADRION 369 — System Orkiestracji Roju AI
### *„Jeśli znałbyś wspaniałość liczb 3, 6 i 9, miałbyś klucz do wszechświata."* — Nikola Tesla

**Wersja:** 5.7.1 (Industrial Security Grade)  
**Status:** 0 Krytycznych Podatności | 243 Testy Zaliczone  
**Język:** [🇬🇧 English](README.md)

---

## 🔺 O Systemie
ADRION 369 to zaawansowany system orkiestracji roju AI, który porzuca tradycyjną, hierarchiczną logikę bezpieczeństwa na rzecz **Etyki Rozproszonej**. System operuje w **162-wymiarowej przestrzeni decyzyjnej**, co czyni go odpornym na manipulacje (jailbreaking) i błędy pojedynczego punktu styku (SPOF).

### Kluczowa Różnica: Etyka Rozproszona vs. Prawa Asimova
| Aspekt | Tradycyjne Prawa (Asimov) | ADRION 369 |
| :--- | :--- | :--- |
| **Ewaluacja** | Sekwencyjna (1→2→3) | **Równoległa** (3 perspektywy jednocześnie) |
| **Decyzja** | Pierwsza pasująca reguła | **Zbalansowana waga** + wymiarowość |
| **Transparentność** | Niejawna | **Glass-Box**: publiczne wagi i progi |
| **Prywatność** | Brak definicji | **G7 Privacy**: mierzalne progi zgody |
| **Ochrona** | Pojedyncza reguła | **G8 Nonmaleficence**: twarde veto przy 0.95 |

---

## 🏗️ Architektura Matrycy 3-6-9
Każda decyzja w systemie przechodzi przez geometryczny proces filtracji:

1.  **Warstwa 3 (TRINITY):** Analiza z 3 perspektyw:
    * **Material:** Efektywność zasobowa i ROI.
    * **Intellectual:** Logika i czystość algorytmiczna.
    * **Essential:** Zgodność z misją i etyką.
2.  **Warstwa 6 (HEXAGON):** 6 trybów operacyjnych (procesy EBDI, maszyna stanów):
    * `Inventory` → `Empathy` → `Process` → `Debate` → `Healing` → `Action`
3.  **Warstwa 9 (GUARDIANS):** 9 Praw Opiekunów (G1-G9). **System VETO:** ≥2 naruszenia lub naruszenie prawa CRITICAL (G7, G8) = natychmiastowy **DENY**.

Iloczyn tensorowy **D^162 = P^3 ⊗ H^6 ⊗ G^9** mapuje każdą decyzję do punktu w R^162, walidowanego względem wszystkich progów Opiekunów przed wykonaniem.

---

## ⚙️ Stos Technologiczny

### Moduły Rdzenia (`core/`)
| Moduł | Funkcja |
| :--- | :--- |
| `trinity.py` | Silnik Trinity — ocena z 3 perspektyw z utwardzeniem niemutowalności |
| `decision_space_162d.py` | Formalizacja D^162 — iloczyn tensorowy, projekcje Opiekunów, Panel Sceptyków |
| `security_hardening.py` | Zgodność G5/G7/G8, licznik CVC, SecurityHardeningEngine |
| `superior_moral_code.py` | Pipeline SAV+DSV — modulacja kryzysowa, detekcja dysonansu, logowanie Genesis |
| `audit_trail.py` | Blockchain-ready łańcuch audytowy SHA-256 (Transparentność G5) |
| `escalation.py` | Protokół eskalacji Human-in-the-loop — webhooki (Slack/Discord) |
| `redis_backend.py` | Backendy Redis/In-Memory dla wdrożeń wieloinstancyjnych |
| `steganography_detector.py` | Detekcja steganografii semantycznej oparta o FFT (czysty Python) |

### Infrastruktura
* **Vortex 1740:** Maszyna stanów EBDI z pulsacją 174Hz i wyrocznią Digital Root.
* **MCP Layer (Porty 9000-9005):** 6 mikroserwisów:
    * `Router`, `Vortex`, `Guardian`, `Oracle`, `Genesis`, `Healer`.
* **Dashboard:** Monitoring Streamlit + Plotly (`dashboard/app.py`) — radar Opiekunów, rozkład decyzji, log eskalacji.

### Zabezpieczenia
* Zamrożone obiekty (`MappingProxyType`, `__slots__`)
* Blokada podklasowania przez metaklasę
* Blokowanie duck-typingu i monkeypatch
* Detekcja steganografii FFT (czysty Python, bez numpy)
* Łańcuch audytowy z detekcją manipulacji

---

## 📈 Historia Wersji i Bezpieczeństwo
| Wersja | Krytyczne Luki | Testy | Kluczowe Zmiany |
| :--- | :---: | :---: | :--- |
| **5.0.0** | 19 | 0 | Start systemu, 9 Praw, publiczne wagi. |
| **5.3.0** | 5 | 64 | Utwardzenie jądra Python, raport Grock. |
| **5.6.0** | 0 | 107 | CVC, THREAT_MODEL, eliminacja luk przemysłowych. |
| **5.7.0** | 0 | 173 | Formalizacja D^162, FFT, Redis, Superior Moral Code. |
| **5.7.1** | **0** | **243** | **Audit Trail (blockchain), Protokół Eskalacji, Dashboard Trinity Sentinel.** |

---

## 🔄 Przepływ Decyzji
```
Request → Trinity(3) → Hexagon(6) → Guardians(9) → Sygnatura 369 → Response
```

System kończy proces nadaniem **Sygnatury 369**, która potwierdza integralność geometryczną obliczeń poprzez sumę kontrolną pierwiastka cyfrowego (digital root).

---

## 🚀 Szybki Start

```bash
# Instalacja
pip install pytest

# Uruchomienie testów
python -m pytest tests/ -v

# Testy obciążeniowe
python -m pytest tests/test_stress_redis.py -v -s

# Dashboard (wymaga: pip install streamlit plotly)
streamlit run dashboard/app.py

# Push na GitHub
export GITHUB_TOKEN="ghp_twoj_token"
python scripts/push_to_github.py
```

---

## 📚 Dokumentacja Szczegółowa
| Plik | Opis |
| :--- | :--- |
| `docs/ARCHITEKTURA_SCALANIE_CALOSCI.md` | Warstwa SCALANIE_CALOSCI v1: F0-F4 + UNITY_FIELD + Protokół Cienia |
| `docs/core/01_CORE_TRINITY.md` | System Trinity — 3 perspektywy, 4 strefy decyzyjne |
| `docs/core/02_CORE_HEXAGON.md` | System Hexagon — 6 trybów, MAX_CYCLES→DENY |
| `docs/core/03_CORE_GUARDIANS.md` | System Opiekunów — 9 Praw, próg VETO=2, CVC |
| `docs/core/04_CORE_EBDI.md` | Model EBDI — STRESS_FLOOR, PADTherapyDetector |
| `docs/THREAT_MODEL.md` | Formalny model zagrożeń (STRIDE + specyficzne AI) |
| `docs/QUICKSTART.md` | Przewodnik integracji Redis i warstwy MCP |
| `GUARDIAN_LAWS_CANONICAL.json` | Jedno źródło prawdy dla 9 Praw Opiekunów + mapowanie D^162 |

---

*ADRION 369 — System Orkiestracji Roju AI*  
*Bezpieczny z Projektu. Transparentny Domyślnie.*  
*https://github.com/Gruszkoland/adrion-369-architecture*
