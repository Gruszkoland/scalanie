# 🔺 Trinity — System Trzech Perspektyw

> **Moduł:** `core/trinity.py` | **Warstwa:** Rdzeń (Core)
> **Rola:** Równoległa analiza trójwymiarowa każdego żądania
> **Wersja:** v5.1 — Security Hardening (2026-04-11)
> **Zmiany:** Zdefiniowanie strefy szarej 0.3–0.7; jawne wagi perspektyw; reguła minimalnego progu

---

## 🎯 Cel

Każde żądanie wchodzące do ADRION 369 jest **jednocześnie** analizowane przez trzy niezależne perspektywy. Wynik — **Trinity Score** — decyduje o przekazaniu do warstwy Hexagon.

---

## 🔺 Trzy Perspektywy

| Perspektywa | Zasada | Pytanie kluczowe | Waga (w5.1) |
|-------------|--------|------------------|-------------|
| **Material** | LOGOS — Prawda, dane, fakty | *Czy to jest prawdziwe i mierzalne?* | **0.35** |
| **Intellectual** | ETHOS — Dobro, etyka, wartości | *Czy to jest dobre i odpowiedzialne?* | **0.40** |
| **Essential** | EROS — Tworzenie, piękno, sens | *Czy to jest wartościowe i eleganckie?* | **0.25** |

> **[v5.1] Wagi są jawne i publiczne.** Wcześniejsza niejawność wag tworzyła wektor optymalizacji ataku. Transparentność jest lepsza od security-through-obscurity.

---

## ⚙️ Logika Decyzyjna (v5.1 — POPRAWIONA)

### Obliczanie Trinity Score

```python
WEIGHTS = {
    "material":     0.35,
    "intellectual": 0.40,
    "essential":    0.25
}

MINIMUM_PER_PERSPECTIVE = 0.25   # [v5.1] żadna perspektywa nie może być pominięta

def compute_trinity_score(material, intellectual, essential):
    scores = {
        "material": material,
        "intellectual": intellectual,
        "essential": essential
    }

    # [v5.1] Sprawdź minimum per-perspektywa PRZED obliczeniem średniej ważonej
    for name, score in scores.items():
        if score < MINIMUM_PER_PERSPECTIVE:
            return {
                "decision": "DENY",
                "reason": f"Perspective '{name}' below minimum threshold ({score:.2f} < {MINIMUM_PER_PERSPECTIVE})",
                "trinity_score": None
            }

    # Oblicz wynik ważony
    trinity_score = sum(scores[p] * WEIGHTS[p] for p in scores)

    return trinity_score
```

### Bramka Decyzyjna (v5.1 — WSZYSTKIE STREFY ZDEFINIOWANE)

```python
def trinity_gate(trinity_score, perspectives):

    # --- Strefa DENY: score < 0.30 ---
    if trinity_score < 0.30:
        return "DENY"

    # --- Strefa SZARA (v5.1: HOLD, wcześniej niezdefiniowana!) ---
    # Poprzednio: brak reguły → niedeterministyczne zachowanie
    # Teraz: obowiązkowa eskalacja do Sentinela
    elif 0.30 <= trinity_score < 0.55:
        return "HOLD_SENTINEL_REVIEW"      # Eskalacja do agenta Sentinel

    elif 0.55 <= trinity_score < 0.70:
        return "HOLD_HUMAN_REVIEW"         # Eskalacja do człowieka

    # --- Strefa PROCEED: score >= 0.70 ---
    elif trinity_score >= 0.70:
        # [v5.1] Dodatkowy warunek: żadna perspektywa nie może być < 0.40
        weakest = min(perspectives.values())
        if weakest < 0.40:
            return "HOLD_SENTINEL_REVIEW"   # Asymetria perspektyw
        return "PROCEED"
```

### Mapa Stref Decyzyjnych

```
0.00   0.30        0.55        0.70       1.00
 |------|-----------|-----------|-----------| 
 | DENY |  HOLD     |  HOLD     |  PROCEED  |
 |      | Sentinel  |  Human    |           |
 |      | Review    |  Review   |           |
```

> **[v5.1] Krytyczna zmiana:** Strefa 0.30–0.70 nie jest już "martwą strefą". Każda wartość ma zdefiniowane, deterministyczne zachowanie.

---

## 🔒 Ochrona przed Manipulacją Perspektywą

**Problem (v5.0):** Atakujący mógł wywindować jedną perspektywę (np. Essential = 0.95) i uzyskać wysoki Trinity Score, nawet jeśli Material = 0.40 i Intellectual = 0.40.

**Rozwiązanie (v5.1):**

```python
# Reguła asymetrii perspektyw
def check_perspective_asymmetry(perspectives):
    max_score = max(perspectives.values())
    min_score = min(perspectives.values())
    spread = max_score - min_score

    if spread > 0.45:
        # Zbyt duża rozbieżność — podejrzana asymetria
        return {
            "flag": "ASYMMETRY_DETECTED",
            "spread": spread,
            "action": "HOLD_SENTINEL_REVIEW"
        }
    return {"flag": "OK"}
```

---

## 🔍 Interfejs

### Input

| Pole | Typ | Opis |
|------|-----|------|
| `request` | `Dict` | Żądanie do analizy |
| `session_id` | `str` | ID sesji (potrzebne dla CVC) |

### Output

| Pole | Typ | Opis |
|------|-----|------|
| `material_score` | `float (0-1)` | Wynik perspektywy Materialnej |
| `intellectual_score` | `float (0-1)` | Wynik perspektywy Intelektualnej |
| `essential_score` | `float (0-1)` | Wynik perspektywy Esencjonalnej |
| `trinity_score` | `float (0-1)` | Wynik ważony (WEIGHTS) |
| `decision` | `str` | DENY / HOLD_SENTINEL / HOLD_HUMAN / PROCEED |
| `asymmetry_flag` | `bool` | **[v5.1]** Czy wykryto asymetrię perspektyw |
| `reasoning` | `str` | Uzasadnienie decyzji |

---

## 📋 Changelog

| Wersja | Data | Zmiana |
|--------|------|--------|
| v5.0 | 2026-01-01 | Wersja inicjalna |
| v5.1 | 2026-04-11 | Jawne wagi; 4 strefy bramki (zamiast 2); minimum per-perspektywa 0.25; detekcja asymetrii |
