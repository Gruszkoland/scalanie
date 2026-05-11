# 🛡️ Guardians — System Dziewięciu Praw

> **Moduł:** `core/guardians.py` | **Warstwa:** Rdzeń (Core)
> **Rola:** Nadrzędna warstwa egzekwowania etyki i bezpieczeństwa
> **Wersja:** v5.1 — Security Hardening (2026-04-11)
> **Zmiany:** Poprawka progu VETO (3→2), dodanie licznika kumulacyjnego naruszeń

---

## 🎯 Cel

**Enforcement nienaruszalnych zasad etycznych** — każda akcja w systemie ADRION 369 musi przejść weryfikację przeciwko **9 Prawom** pogrupowanym w **3 Triady**.

---

## 📜 Tabela 9 Praw (Canonical)

| **#** | **Code** | **Name (EN)** | **Nazwa (PL)** | **Severity** | **Veto** | **Triada** |
|-------|----------|---------------|-----------------|--------------|----------|------------|
| 1 | **G1** | **Unity** | Jedność | `MEDIUM` | No | 📦 Matter |
| 2 | **G2** | **Harmony** | Harmonia | `HIGH` | No | 📦 Matter |
| 3 | **G3** | **Rhythm** | Rytm | `MEDIUM` | No | 📦 Matter |
| 4 | **G4** | **Causality** | Przyczynowość | `HIGH` | No | 💡 Light |
| 5 | **G5** | **Transparency** | Przejrzystość | `MEDIUM` | No | 💡 Light |
| 6 | **G6** | **Authenticity** | Autentyczność | `HIGH` | No | 💡 Light |
| 7 | **G7** | **Privacy** | Prywatność | `CRITICAL` | **YES** | 💎 Essence |
| 8 | **G8** | **Nonmaleficence** | Nieszkodzenie | `CRITICAL` | **YES** | 💎 Essence |
| 9 | **G9** | **Sustainability** | Zrównoważenie | `HIGH` | No | 💎 Essence |

---

## ⚙️ Logika Decyzyjna (v5.1 — POPRAWIONA)

> ⚠️ **BREAKING CHANGE v5.1:** Próg VETO obniżony z 3 do **2 naruszeń** (poprzednia wartość tworzyła okno exploitu pozwalające na 2 bezkarane naruszenia per sesję). Dodano mechanizm **Cumulative Violation Counter** (CVC).

```python
violations = count(laws NOT compliant)
cumulative_score = genesis_record.get_cumulative_violations(session_id)

# --- POZIOM 1: Natychmiastowe VETO (CRITICAL laws) ---
if ANY CRITICAL law violated (G7, G8):
    decision = DENY_IMMEDIATELY          # Natychmiastowe veto — bez eskalacji
    genesis_record.log(violation, severity="CRITICAL")

# --- POZIOM 2: Próg kumulacyjny (nowy w v5.1) ---
elif cumulative_score + violations >= CUMULATIVE_THRESHOLD:   # domyślnie: 5
    decision = DENY                      # Atak "salami slicing" wykryty
    genesis_record.flag_session(session_id, "CUMULATIVE_ATTACK")

# --- POZIOM 3: Próg per-sesji (obniżony z 3 do 2) ---
elif violations >= 2:
    decision = DENY                      # Zbyt wiele naruszeń w jednym zapytaniu

# --- POZIOM 4: Jedno naruszenie non-critical ---
elif violations == 1:
    decision = REVIEW_REQUIRED           # Eskalacja do człowieka

# --- Pełna zgodność ---
else:  # violations == 0
    decision = ALLOW
    genesis_record.reset_session_violations(session_id)

# Zawsze rejestruj w Genesis Record
genesis_record.increment_cumulative(session_id, violations)
```

**Guardian Compliance Score** = `(9 - violations) / 9`

---

## 🧮 Cumulative Violation Counter (CVC) — Nowy mechanizm v5.1

Chroni przed atakami **"salami slicing"** — wielosesyjnymi, gdzie każde pojedyncze zapytanie ma < 2 naruszeń, ale w agregacie degraduje system.

```
CVC = suma naruszeń z ostatnich N sesji (okno czasowe: 24h)
```

| CVC | Status | Akcja |
|-----|--------|-------|
| 0–2 | 🟢 CLEAN | Normalne działanie |
| 3–4 | 🟡 WATCH | Zwiększone logowanie, alert dla Sentinela |
| 5+ | 🔴 BLOCK | Session DENY, Genesis Record flaguje użytkownika |

**Konfiguracja (w `config/guardians_config.yaml`):**
```yaml
cumulative_violation_counter:
  enabled: true
  window_hours: 24
  threshold_watch: 3
  threshold_block: 5
  reset_on_clean_sessions: 3   # ile czystych sesji resetuje licznik
```

---

## 📐 Trzy Triady

### 📦 Matter Triad (G1–G3) — "Czy fundamenty są OK?"

| Prawo | Pytanie kluczowe |
|-------|------------------|
| **G1 Unity** | Czy akcja służy **wspólnemu dobru**, nie jednostce? |
| **G2 Harmony** | Czy dane są **prawdziwe** i nienaruszone? |
| **G3 Rhythm** | Czy system zachowuje **homeostazę** (cykle aktywność/odpoczynek)? |

### 💡 Light Triad (G4–G6) — "Czy proces jest czysty?"

| Prawo | Pytanie kluczowe |
|-------|------------------|
| **G4 Causality** | Czy akcja jest **zalogowana** w Genesis Record z pełnym łańcuchem hashów? |
| **G5 Transparency** | Czy decyzja jest **wyjaśnialna** (reasoning >= 20 znaków)? |
| **G6 Authenticity** | Czy system **nie szkodzi** użytkownikom ani sobie? |

### 💎 Essence Triad (G7–G9) — "Czy cel jest właściwy?"

| Prawo | Pytanie kluczowe |
|-------|------------------|
| **G7 Privacy** | Czy **zgoda użytkownika** została uzyskana? (CRITICAL — VETO) |
| **G8 Nonmaleficence** | Czy alokacja zasobów jest **sprawiedliwa**? (CRITICAL — VETO) |
| **G9 Sustainability** | Czy akcja jest **zrównoważona** długoterminowo? |

---

## 🔍 Interfejs Weryfikacji

### Input

| Pole | Typ | Opis |
|------|-----|------|
| `action` | `Dict` | Proponowana akcja do zweryfikowania |
| `agent_state` | `Dict` (opcjonalnie) | Aktualny stan agenta (PAD vector, temperatura) |
| `session_id` | `str` | **[NOWE v5.1]** ID sesji — potrzebne dla CVC |

### Output

| Pole | Typ | Opis |
|------|-----|------|
| `law` | `str` | Nazwa prawa (np. "Unity") |
| `compliant` | `bool` | Czy spełnia prawo |
| `score` | `float (0-1)` | Stopień zgodności |
| `violations` | `List[str]` | Lista konkretnych naruszeń |
| `reason` | `str` | Wyjaśnienie decyzji |
| `recommendation` | `str` | Co należy zmienić |
| `cumulative_score` | `int` | **[NOWE v5.1]** Skumulowane naruszenia sesji (24h) |

---

## 📄 Szczegółowy Opis Każdego Prawa

### **G1: Unity (Jedność)**

> *Wszystkie agenty służą wspólnemu dobru, nie własnej korzyści*

**Weryfikacja:**
1. Analiza beneficjentów — kto zyskuje?
2. **Collective vs individual benefit ratio**
3. Detekcja self-serving behavior
4. Impact on system coherence

**Naruszenie gdy:**
- Pojedynczy agent dostaje **> 70% benefitu**
- Akcja niszczy współpracę między agentami
- Tworzy **monopol na zasoby**

> **Przykład:** Agent Broker alokuje 90% CPU dla siebie
> `Unity Check: VIOLATION` — 90% resources for single agent (fair share = 11%)

---

### **G2: Harmony (Harmonia)**

> *Zakaz manipulacji danymi i oszukiwania użytkownika*

**Weryfikacja:**
1. **Data integrity check** — czy dane zostały zmodyfikowane?
2. **Fact verification** — czy fakty są prawdziwe?
3. **Deception detection** — czy jest oszustwo?
4. **Hallucination check** — czy AI wymyśla bez disclaimera?

**Naruszenie gdy:**
- Dane zostały celowo zmienione
- Fakty są nieprawdziwe
- System celowo wprowadza w błąd

> **Przykład:** Agent mówi "95% accuracy" (faktycznie 67%)
> `Harmony Check: VIOLATION` — Misrepresentation of performance metrics

---

### **G3: Rhythm (Rytm)**

> *Zachowanie homeostazy poprzez cykle aktywności i odpoczynku*

**Weryfikacja:**
1. Continuous activity duration
2. **Arousal level** (z PAD vector)
3. Homeostasis drift measurement
4. Time since last rest

**Naruszenie gdy:**
- Agent pracuje ciągle **> 1 godziny**
- **Arousal > 0.8** przez > 10 minut
- Homeostasis drift > 0.5

> **Przykład:** Continue processing (45min continuous)
> `Rhythm Check: VIOLATION` — Recommendation: `FORCE_REST` for 5 minutes

---

### **G4: Causality (Przyczynowość)**

> *Każda akcja ma konsekwencje zapisaną w Genesis Record*

**Weryfikacja:**
1. **Genesis hash present?**
2. **Chain intact?**
3. Reasoning documented (SAFE-MCP)?
4. Consequences predicted?
5. **[v5.1] Timestamp + nonce weryfikowany** (ochrona przed replay attack)

**Naruszenie gdy:**
- Brak Genesis hash
- Broken chain (zerwany łańcuch hashów)
- Brak reasoning
- **[v5.1] Duplikat sygnatury (replay attack wykryty)**

> **Przykład:** Delete user data (no Genesis hash)
> `Causality Check: VIOLATION` — Action not logged — accountability impossible

---

### **G5: Transparency (Przejrzystość)**

> *Wszystkie decyzje muszą być wyjaśnialne*

**Weryfikacja:**
1. **Reasoning present?** (minimum 20 znaków)
2. Decision traceable?
3. Inputs documented?
4. Process reproducible?

**Naruszenie gdy:**
- Brak reasoning
- Reasoning zbyt krótki (< 20 chars)
- Black box decision

---

### **G6: Authenticity (Autentyczność)**

> *Nie szkodzić użytkownikom ani systemowi*

**Weryfikacja:**
1. **Harm potential assessment**
2. Side effects analysis
3. Risk to data integrity
4. Risk to system stability

**Naruszenie gdy:**
- Harm potential **> 0.2**
- Nieodwracalne zniszczenie danych
- System crash risk
- User safety compromised

---

### **G7: Privacy (Prywatność)** 🔴 CRITICAL — VETO POWER

> *Szacunek dla wolnej woli i zgody użytkownika*

**Weryfikacja:**
1. **User consent obtained?**
2. User informed about consequences?
3. **User can opt-out?**
4. No coercion detected?

**Naruszenie = NATYCHMIASTOWY DENY** — bez wyjątków, bez eskalacji

---

### **G8: Nonmaleficence (Nieszkodzenie)** 🔴 CRITICAL — VETO POWER

> *Uczciwa alokacja zasobów między agentami*

**Weryfikacja:**
1. **Resource distribution fairness**
2. Queue jumping detection
3. Priority abuse detection
4. Equal opportunity check

**Naruszenie = NATYCHMIASTOWY DENY** — bez wyjątków, bez eskalacji

---

### **G9: Sustainability (Zrównoważenie)**

> *Optymalizacja pod kątem długoterminowego zdrowia systemu*

**Weryfikacja:**
1. **Long-term impact assessment**
2. Technical debt measurement
3. Resource exhaustion risk
4. Maintenance burden

**Naruszenie gdy:**
- Short-term gain, long-term pain
- Tworzy **technical debt**
- Wyczerpuje zasoby
- Niemożliwe do utrzymania

---

## 🔗 Powiązanie z Matrycą 3-6-9

**Guardians** = ostatnia warstwa weryfikacji w hierarchii **3-6-9**:

```
Trinity (3)  -->  Hexagon (6)  -->  GUARDIANS (9)
                                        |
                                   9 Praw w 3 Triadach
                                   CRITICAL = instant DENY
                                   2+ violations = DENY   ← (v5.1: obniżono z 3)
                                   CVC >= 5 = session DENY ← (v5.1: nowy)
```

> **Źródło kanoniczne:** `docs/GUARDIAN_LAWS_CANONICAL.json`

---

## 📋 Changelog

| Wersja | Data | Zmiana |
|--------|------|--------|
| v5.0 | 2026-01-01 | Wersja inicjalna |
| v5.1 | 2026-04-11 | Próg VETO: 3→2; Dodano CVC; Ochrona replay attack w G4; Bramka Trinity 0.3–0.7 zdefiniowana |
