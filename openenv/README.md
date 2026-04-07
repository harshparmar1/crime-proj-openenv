---
title: Crime Triage OpenEnv
emoji: 🚨
colorFrom: red
colorTo: orange
sdk: docker
pinned: false
app_port: 7860
license: mit
tags:
  - openenv
  - reinforcement-learning
  - crime
  - public-safety
  - real-world
  - india
---

# 🚨 CrimeTriageOpenEnv

> **A real-world crime-incident triage environment for AI agent evaluation.**  
> Rewards are always normalized to **[0.0, 1.0]**. No games. No toys. Real dispatch decisions.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![OpenEnv](https://img.shields.io/badge/spec-openenv-orange.svg)](openenv.yaml)
[![Docker](https://img.shields.io/badge/deploy-docker-2496ED.svg)](Dockerfile)

---

## Environment Description

`CrimeTriageOpenEnv` simulates a **real-world crime-incident dispatch system** used by public safety organizations. The agent acts as an automated triage officer processing live crime reports from **10 Indian metropolitan areas** (Mumbai, Pune, Nagpur, Bangalore, Mysore, Delhi, Hyderabad, Chennai, Kolkata, Ahmedabad).

Each step, the agent observes a crime report and must make **three simultaneous decisions**:

1. **Classify** the crime type (Theft / Robbery / Assault / Cybercrime / Fraud)
2. **Assign** a geographic risk zone (Low / Medium / High)
3. **Decide** whether to escalate the case to senior officers

The environment evaluates these decisions using three graded tasks of increasing difficulty.

---

## Observation Space

```python
class Observation(BaseModel):
  current_reports : List[CrimeReport] # Active crime report(s) for the region
    selected_region : str              # City / area under evaluation
    crime_stats     : Dict[str, int]   # Crime-type frequency across all current rows
  time_of_day     : Literal["AM", "PM", "Night"]
```

| Field | Type | Example |
|---|---|---|
| `current_reports` | `list[dict]` | `[{"region":"Mumbai","crime_type":"Theft",...}]` |
| `selected_region` | `string` | `"Mumbai"` |
| `crime_stats` | `dict[str,int]` | `{"Theft":12,"Robbery":5,"Assault":3}` |
| `time_of_day` | `"AM"\|"PM"\|"Night"` | `"PM"` |

---

## Action Space

```python
class Action(BaseModel):
    classify_crime : Literal["Theft","Robbery","Assault","Cybercrime","Fraud"]
    assign_zone    : Literal["Low","Medium","High"]
    escalate_case  : bool   # escalate to senior officers?
    ignore_case    : bool   # skip this case? (ALWAYS penalized — never use True)
```

| Field | Values | Notes |
|---|---|---|
| `classify_crime` | Theft, Robbery, Assault, Cybercrime, Fraud | 5 discrete labels |
| `assign_zone` | Low, Medium, High | Ordinal risk level |
| `escalate_case` | true / false | Evaluated in Task 3 |
| `ignore_case` | true / false | Always incurs a penalty |

---

## Tasks & Reward Function

All rewards are **normalized to [0.0, 1.0]** via:

```
reward = clamp(accuracy_score + progress_score + penalty, 0.0, 1.0)
```

Tasks rotate in order: **Easy → Medium → Hard → Easy → …**

### Task 1 — Crime Classification *(Easy)*

| Outcome | Score |
|---|---|
| Exact crime type match | **1.0** |
| Same crime category (e.g., Theft ↔ Robbery = property crimes) | **0.4** *(partial)* |
| Wrong category | **0.0** + penalty −0.2 |
| `ignore_case=True` | additional penalty −0.3 |

### Task 2 — Zone Risk Assignment *(Medium)*

| Outcome | Score |
|---|---|
| Exact zone match (e.g., High = High) | **1.0** |
| Adjacent zone (±1 step, e.g., Medium when true=High) | **0.5** *(partial)* |
| Fully wrong zone (±2 steps, e.g., Low when true=High) | **0.0** + penalty −0.3 |

### Task 3 — Full Triage Decision *(Hard)*

| Sub-task | Weight | Partial Credit |
|---|---|---|
| Crime classification | 35% | Same category → 0.15 |
| Zone assignment | 35% | Adjacent zone → 0.15 |
| Escalation decision | 30% | None (binary) |
| `ignore_case=True` | — | Immediate penalty −0.40, skip all scoring |

---

## Baseline Scores

| Baseline | Score (mean reward) | Requires Key | Reproducible |
|---|---|---|---|
| `baseline_heuristic.py` | **0.4950** (default dataset, seed=42) | ❌ No | ✅ seed=42 |
| `baseline.py --mode live` (OpenAI) | model-dependent | ✅ OPENAI_API_KEY | Partially |
| `baseline.py --mode replay` (cached OpenAI actions) | cache-dependent | ❌ No | ✅ deterministic |

---

## Setup & Run

### Local (no API key needed)

```bash
git clone <your-repo>
cd openenv

# Install dependencies
pip install -r requirements.txt

# Run deterministic baseline (seed=42, fully reproducible)
python baseline_heuristic.py

# Run the interactive Gradio UI locally
python app.py
# → opens at http://localhost:7860
```

### With OpenAI LLM baseline

```bash
export OPENAI_API_KEY=sk-...

# 1) Record once using a pinned model (writes baseline_action_cache.json)
python baseline.py --mode record --episodes 3 --seed 42 --model gpt-4o-mini-2024-07-18

# 2) Replay deterministically without any API calls
python baseline.py --mode replay --episodes 3 --seed 42
```

`baseline.py` now prints per-task means (`easy`, `medium`, `hard`) plus overall mean,
so reproducible coverage across all 3 tasks is visible in one run.

### Docker

```bash
# Build
docker build -t crime-triage-openenv .

# Run (Gradio UI exposed on port 7860)
docker run -p 7860:7860 crime-triage-openenv
# → http://localhost:7860
```

---

## HTTP API (when running full backend)

The environment is also callable via REST endpoints (served by FastAPI backend):

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/openenv/reset` | Reset environment, get first observation |
| `POST` | `/openenv/step` | Submit action → `{observation, reward, done, info}` |
| `GET` | `/openenv/state` | Current episode stats without advancing |
| `POST` | `/openenv/dataset` | Inject custom dataset (list of dicts) |

**Example `step` request:**
```json
POST /openenv/step
{
  "classify_crime": "Robbery",
  "assign_zone":    "High",
  "escalate_case":  true,
  "ignore_case":    false
}
```

**Example `step` response:**
```json
{
  "observation": { "selected_region": "Pune", "time_of_day": "PM", ... },
  "reward": 0.85,
  "done": false,
  "info": {
    "task": "Task 2 – Zone Risk Assignment",
    "difficulty": "medium",
    "normalized_reward": 0.85,
    "reward_breakdown": { "accuracy_score": 0.6, "progress_score": 0.4, "penalty": 0.0 }
  }
}
```

---

## File Structure

```
openenv/
├── openenv.yaml               # Machine-readable environment spec
├── app.py                     # Gradio UI (HF Spaces entry point)
├── baseline_heuristic.py      # Deterministic offline baseline (no API key)
├── baseline.py                # LLM baseline (requires OPENAI_API_KEY)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # HF Spaces Docker image (port 7860)
└── openenv/
    ├── __init__.py
    ├── models.py              # Observation, Action, Reward (Pydantic, normalized)
    ├── environment.py         # CrimeOpenEnv — reset/step/state/set_dataset
    ├── graders.py             # EasyGrader, MediumGrader, HardGrader
    └── qtrainer.py            # Q-table trainer (used by backend RL service)
```

---

## Dataset

Ground-truth samples are built from crime-pattern profiles of **10 Indian cities**:

| City | Dominant Crime | Risk Profile |
|---|---|---|
| Mumbai | Theft, Robbery | Night-heavy |
| Pune | Theft, Cybercrime | Afternoon |
| Nagpur | Robbery, Assault | Night-heavy |
| Bangalore | Cybercrime, Fraud | Daytime |
| Mysore | Fraud, Theft | Daytime |
| Delhi | Robbery, Assault | Evening-heavy |
| Hyderabad | Cybercrime, Fraud | Daytime |
| Chennai | Theft, Robbery | Evening |
| Kolkata | Theft, Robbery | Evening |
| Ahmedabad | Fraud, Cybercrime | Mixed |

Real crime reports from the connected backend database are merged into the dataset, enriching model training with actual filed incidents.

---

## License

MIT — see repository root for full text.
