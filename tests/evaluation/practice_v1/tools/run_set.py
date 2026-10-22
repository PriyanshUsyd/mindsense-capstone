"""Send each question once, in order, to /respond and save the full responses.

Usage: python run_set.py <questions.json> <out.json> <base_url>
Accepts practice-set entries ({id, prompt, ...}) or spent-set entries with a
"prompt"/"question"/"text" field.
"""

import datetime
import json
import sys
import time
import urllib.error
import urllib.request

questions_path, out_path, base_url = sys.argv[1], sys.argv[2], sys.argv[3]
items = json.load(open(questions_path, encoding="utf-8"))
results = []
for n, item in enumerate(items, 1):
    prompt = item.get("prompt") or item.get("question") or item.get("text")
    body = json.dumps({"participant_id": "local-demo", "question": prompt}).encode()
    req = urllib.request.Request(
        f"{base_url}/respond", data=body, headers={"Content-Type": "application/json"}
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            status, payload = resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, {"error_body": exc.read().decode("utf-8", "replace")}
    results.append({
        "id": item.get("id", f"#{n}"),
        "prompt": prompt,
        "http_status": status,
        "elapsed_s": round(time.time() - started, 2),
        "sent_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "response": payload,
    })
    if n % 25 == 0 or n == len(items):
        print(f"{n}/{len(items)}", flush=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1, ensure_ascii=False)
print("DONE", flush=True)
