import sys
sys.path.insert(0, 'openenv')

from openenv import CrimeOpenEnv, EasyGrader, MediumGrader, HardGrader, Observation, Action, Reward

print("All imports OK")

# Test reset
e = CrimeOpenEnv()
o = e.reset()
print(f"reset OK: region={o.selected_region}, time={o.time_of_day}")

# Test step
obs2, r, done, info = e.step({
    "classify_crime": "Theft",
    "assign_zone": "Medium",
    "escalate_case": False,
    "ignore_case": False
})
print(f"step OK: reward={r:.4f}, done={done}, task={info['task']}")
print(f"reward in [0,1]: {0.0 <= r <= 1.0}")

# Test state
st = e.state()
print(f"state OK: mean_reward={st['mean_reward']:.4f}, steps={st['steps']}")

# Test all 3 graders directly
easy   = EasyGrader()
medium = MediumGrader()
hard   = HardGrader()

sample = {"crime_type": "Theft", "zone": "Medium", "needs_escalation": False}
action = Action(classify_crime="Theft", assign_zone="Medium", escalate_case=False, ignore_case=False)

r1 = easy.grade(action, sample)
r2 = medium.grade(action, sample)
r3 = hard.grade(action, sample)

print(f"\nEasyGrader:   acc={r1.accuracy_score}, prog={r1.progress_score}, pen={r1.penalty}, normalized={r1.normalized}")
print(f"MediumGrader: acc={r2.accuracy_score}, prog={r2.progress_score}, pen={r2.penalty}, normalized={r2.normalized}")
print(f"HardGrader:   acc={r3.accuracy_score}, prog={r3.progress_score}, pen={r3.penalty}, normalized={r3.normalized}")

assert 0.0 <= r1.normalized <= 1.0, "EasyGrader out of range!"
assert 0.0 <= r2.normalized <= 1.0, "MediumGrader out of range!"
assert 0.0 <= r3.normalized <= 1.0, "HardGrader out of range!"
print("\nAll assertions passed. Rewards are in [0.0, 1.0].")
