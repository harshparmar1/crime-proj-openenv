"""
app.py — Gradio UI for CrimeTriageOpenEnv on Hugging Face Spaces
─────────────────────────────────────────────────────────────────
Exposes an interactive web demo where users can:
  1. Run the deterministic heuristic baseline automatically.
  2. Play manually by choosing their own action each step.
  3. See per-step rewards, task difficulty, and a final score.

Port: 7860 (required by Hugging Face Docker Spaces)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import gradio as gr

from openenv.environment import CrimeOpenEnv
from baseline_heuristic import heuristic_action, run_heuristic_baseline

# ── Shared env instance (one per session via Gradio State) ────────────────────

def _new_env() -> CrimeOpenEnv:
    return CrimeOpenEnv()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_obs(obs_dict: Dict[str, Any]) -> str:
    return json.dumps(obs_dict, indent=2)


def _fmt_state(state: Dict[str, Any]) -> str:
    rewards = state.get("episode_rewards", [])
    mean    = state.get("mean_reward", 0.0)
    return (
        f"Step: {state['steps']}  |  Remaining: {state['remaining']}\n"
        f"Mean reward so far: {mean:.4f}\n"
        f"Per-step rewards:   {[round(r, 3) for r in rewards]}"
    )


# ── Tab 1: Auto Heuristic Baseline ───────────────────────────────────────────

def run_auto_baseline() -> tuple[str, str]:
    """Run the full heuristic episode and return formatted log + score."""
    env = CrimeOpenEnv()
    observation = env.reset()

    rows: List[str] = []
    done = False
    step = 0

    while not done:
        action = heuristic_action(observation.model_dump())
        observation, reward, done, info = env.step(action)
        step += 1
        difficulty = info.get("difficulty", "")
        task_name  = info.get("task", "")
        bd = info.get("reward_breakdown", {})
        rows.append(
            f"Step {step:2d} │ {difficulty:<6} │ {task_name:<36} │ "
            f"reward={reward:.4f}  acc={bd.get('accuracy_score',0):.2f}  "
            f"prog={bd.get('progress_score',0):.2f}  pen={bd.get('penalty',0):.2f}"
        )

    final = env.state()
    mean  = final.get("mean_reward", 0.0)
    log   = "\n".join(rows)
    score = f"✅  Final normalized score: {mean:.4f}  (seed=42, fully reproducible)"
    return log, score


# ── Tab 2: Manual Play ────────────────────────────────────────────────────────

def manual_reset(env_state: Dict) -> tuple[str, str, str, Dict]:
    env = _new_env()
    obs = env.reset()
    env_state = {
        "env": env,
        "done": False,
        "log": [],
    }
    return _fmt_obs(obs.model_dump()), _fmt_state(env.state()), "Episode started.", env_state


def manual_step(
    classify_crime: str,
    assign_zone: str,
    escalate_case: bool,
    ignore_case: bool,
    env_state: Dict,
) -> tuple[str, str, str, Dict]:
    if env_state.get("done"):
        return "", "", "⚠️ Episode finished. Click Reset to start a new episode.", env_state

    env: CrimeOpenEnv = env_state["env"]
    action = {
        "classify_crime": classify_crime,
        "assign_zone":    assign_zone,
        "escalate_case":  escalate_case,
        "ignore_case":    ignore_case,
    }

    obs, reward, done, info = env.step(action)
    env_state["done"] = done
    task   = info.get("task", "")
    diff   = info.get("difficulty", "")
    bd     = info.get("reward_breakdown", {})

    log_line = (
        f"[{diff}] {task}  →  reward={reward:.4f}  "
        f"(acc={bd.get('accuracy_score',0):.2f}  "
        f"prog={bd.get('progress_score',0):.2f}  "
        f"pen={bd.get('penalty',0):.2f})"
    )
    env_state["log"].append(log_line)

    obs_text   = _fmt_obs(obs.model_dump()) if not done else "🎉 Episode complete!"
    state_text = _fmt_state(env.state())
    history    = "\n".join(env_state["log"])

    if done:
        mean = env.state().get("mean_reward", 0.0)
        history += f"\n\n🏁 Final mean reward: {mean:.4f}"

    return obs_text, state_text, history, env_state


# ── Build Gradio UI ───────────────────────────────────────────────────────────

def build_demo() -> gr.Blocks:
    with gr.Blocks(
        title="CrimeTriageOpenEnv",
        theme=gr.themes.Soft(primary_hue="red"),
        css="""
        .title  { text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.2rem; }
        .sub    { text-align: center; color: #666; margin-bottom: 1.5rem; }
        .mono   { font-family: monospace; font-size: 0.85rem; }
        """,
    ) as demo:
        gr.HTML('<div class="title">🚨 CrimeTriageOpenEnv</div>')
        gr.HTML(
            '<div class="sub">Real-world crime-incident triage · '
            'easy → medium → hard · rewards normalized 0.0–1.0</div>'
        )

        with gr.Tabs():
            # ── Tab 1 ─────────────────────────────────────────────────
            with gr.Tab("🤖 Auto Heuristic Baseline"):
                gr.Markdown(
                    "Runs the **deterministic heuristic policy** (no API key needed, seed=42). "
                    "Click the button to see per-step rewards and a final normalized score."
                )
                run_btn   = gr.Button("▶ Run Baseline", variant="primary")
                log_box   = gr.Textbox(label="Step-by-step log", lines=12, elem_classes="mono")
                score_box = gr.Textbox(label="Final Score", lines=1)

                run_btn.click(fn=run_auto_baseline, outputs=[log_box, score_box])

            # ── Tab 2 ─────────────────────────────────────────────────
            with gr.Tab("🕹️ Play Manually"):
                gr.Markdown(
                    "Control the agent yourself. Choose an action each step and see how the "
                    "graders score your decisions across easy / medium / hard tasks."
                )

                env_state = gr.State({})

                with gr.Row():
                    obs_box   = gr.Textbox(label="Current Observation", lines=10, elem_classes="mono")
                    state_box = gr.Textbox(label="Episode State", lines=10, elem_classes="mono")

                with gr.Row():
                    crime_dd  = gr.Dropdown(
                        choices=["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"],
                        value="Theft", label="classify_crime"
                    )
                    zone_dd   = gr.Dropdown(
                        choices=["Low", "Medium", "High"],
                        value="Low", label="assign_zone"
                    )
                    esc_cb    = gr.Checkbox(label="escalate_case", value=False)
                    ign_cb    = gr.Checkbox(label="ignore_case (always penalized)", value=False)

                with gr.Row():
                    reset_btn = gr.Button("🔄 Reset Episode", variant="secondary")
                    step_btn  = gr.Button("⏭ Submit Action", variant="primary")

                history_box = gr.Textbox(label="Action History & Rewards", lines=10, elem_classes="mono")

                reset_btn.click(
                    fn=manual_reset,
                    inputs=[env_state],
                    outputs=[obs_box, state_box, history_box, env_state],
                )
                step_btn.click(
                    fn=manual_step,
                    inputs=[crime_dd, zone_dd, esc_cb, ign_cb, env_state],
                    outputs=[obs_box, state_box, history_box, env_state],
                )

            # ── Tab 3: Spec Reference ──────────────────────────────────
            with gr.Tab("📋 Environment Spec"):
                gr.Markdown("""
## CrimeTriageOpenEnv — Quick Reference

### Observation Space
| Field | Type | Description |
|---|---|---|
| `current_reports` | list[dict] | Active crime report(s) for the region |
| `selected_region` | string | City under evaluation |
| `crime_stats` | dict[str, int] | Crime type frequency across dataset |
| `time_of_day` | AM \| PM \| Night | Broad time bucket |

### Action Space
| Field | Type | Values |
|---|---|---|
| `classify_crime` | string | Theft, Robbery, Assault, Cybercrime, Fraud |
| `assign_zone` | string | Low, Medium, High |
| `escalate_case` | bool | true / false |
| `ignore_case` | bool | Always penalized — keep false |

### Tasks & Rewards (0.0 – 1.0)
| Task | Difficulty | Goal | Max Score |
|---|---|---|---|
| Task 1 | Easy | Correct crime type | 1.0 |
| Task 2 | Medium | Correct risk zone (partial credit for adjacent) | 1.0 |
| Task 3 | Hard | Crime + Zone + Escalation simultaneously | 1.0 |

### Reward Formula
```
reward = clamp(accuracy_score + progress_score + penalty, 0.0, 1.0)
```
                """)

    return demo


if __name__ == "__main__":
    demo = build_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)
