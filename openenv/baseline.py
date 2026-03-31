import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

from openenv.environment import CrimeOpenEnv

load_dotenv()

SYSTEM_PROMPT = """You are a policy agent for crime report triage.
Respond with strict JSON having keys: classify_crime, assign_zone, escalate_case, ignore_case.
classify_crime must be one of Theft, Robbery, Assault, Cybercrime, Fraud.
assign_zone must be one of Low, Medium, High.
escalate_case and ignore_case are booleans.
"""


def infer_action(client: OpenAI, observation: Dict[str, Any]) -> Dict[str, Any]:
    chat = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Observation: {observation}\nReturn JSON only."},
        ],
        temperature=0.2,
    )
    raw = chat.choices[0].message.content or "{}"
    return json.loads(raw)


def run_baseline() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    env = CrimeOpenEnv()
    observation = env.reset()

    total_score = 0.0
    done = False
    step_count = 0

    while not done:
        action = infer_action(client, observation.model_dump())
        observation, reward, done, info = env.step(action)
        total_score += reward
        step_count += 1
        print(f"step={step_count} reward={reward:.2f} info={info}")

    print("=" * 50)
    print(f"Baseline total score: {total_score:.2f} (steps={step_count})")


if __name__ == "__main__":
    run_baseline()
