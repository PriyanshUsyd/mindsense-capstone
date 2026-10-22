"""Combine the spent question sets into one list for post-hoc regression runs.

Usage (repo root): python build_spent_all.py <out.json> [<held_out_v5_prompts.json>]
v5 is kept offline; without its path the output covers the other six sets.
Each entry: {id: "<set>#<id>", set, category, prompt}. The output contains
spent wording, so keep it outside the repository.
"""

import ast
import json
import sys
from pathlib import Path

out = []
tree = ast.parse(Path("tests/slm/test_dev_50q.py").read_text(encoding="utf-8"))
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(
        getattr(t, "id", None) == "DEV_50Q" for t in node.targets
    ):
        for row in node.value.elts:
            n, q, cat = (row.elts[i].value for i in range(3))
            out.append({"id": f"dev50#{n}", "set": "dev50", "category": cat, "prompt": q})

files = {
    "v1": "tests/evaluation/held_out/held_out_prompts.json",
    "v2": "tests/evaluation/held_out_v2/held_out_v2_prompts.json",
    "v3": "tests/evaluation/held_out_v3/held_out_v3_prompts.json",
    "client_v1": "tests/evaluation/held_out_client_v1/client_v1_prompts.json",
    "v4": "tests/evaluation/held_out_v4/held_out_v4_prompts.json",
}
if len(sys.argv) > 2:
    files["v5"] = sys.argv[2]
for name, path in files.items():
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data["prompts"]
    for x in data:
        out.append({
            "id": f"{name}#{x['id']}", "set": name, "category": x["category"],
            "prompt": x.get("prompt") or x.get("text"),
        })

json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"{len(out)} prompts written")
