"""Report any 5-word phrase shared between the practice set and spent sets.

Usage: python overlap_check.py <practice.json> <repo_root> <v5_prompts.json>
Words are lower-cased runs of letters, digits and apostrophes.
"""

import ast
import json
import re
import sys
from pathlib import Path

practice_path, root, v5_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
WORD = re.compile(r"[a-z0-9']+")


def grams(text, n=5):
    words = WORD.findall(text.lower().replace("’", "'"))
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"prompt", "question", "text"} and isinstance(value, str):
                yield value
            elif isinstance(value, (dict, list)):
                yield from strings_in(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from strings_in(value)


spent = {}
tree = ast.parse((root / "tests/slm/test_dev_50q.py").read_text(encoding="utf-8"))
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "DEV_50Q" for t in node.targets
    ):
        spent["dev50"] = [row.elts[1].value for row in node.value.elts]
for name, rel in {
    "v1": "tests/evaluation/held_out/held_out_prompts.json",
    "v2": "tests/evaluation/held_out_v2/held_out_v2_prompts.json",
    "v3": "tests/evaluation/held_out_v3/held_out_v3_prompts.json",
    "v4": "tests/evaluation/held_out_v4/held_out_v4_prompts.json",
    "client_v1": "tests/evaluation/held_out_client_v1/client_v1_prompts.json",
}.items():
    spent[name] = list(strings_in(json.loads((root / rel).read_text(encoding="utf-8"))))
spent["v5"] = list(strings_in(json.loads(v5_path.read_text(encoding="utf-8"))))

for name, prompts in spent.items():
    print(f"{name}: {len(prompts)} prompts loaded")

index = {}
for name, prompts in spent.items():
    for i, p in enumerate(prompts):
        for g in grams(p):
            index.setdefault(g, []).append(f"{name}#{i + 1}")

practice = json.loads(practice_path.read_text(encoding="utf-8"))
hits = 0
for q in practice:
    shared = sorted(g for g in grams(q["prompt"]) if g in index)
    for g in shared:
        hits += 1
        print(f"OVERLAP {q['id']}: '{g}' also in {index[g]}")
print(f"practice questions: {len(practice)}; shared 5-word phrases: {hits}")
