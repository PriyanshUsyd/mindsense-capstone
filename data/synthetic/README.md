# Synthetic demo dataset

**This is synthetic data. It describes no real people.** The client approved it for testing and demonstration (20 October 2026). It is not the StudentLife / CES data and must never be described as real study results.

## What is here

| File | Columns | Rows |
| --- | --- | ---: |
| `Sensing/sensing.csv` | `uid, day, quality_loc, loc_dist_ep_0, unlock_num_ep_0, is_ios` | 19,834 |
| `EMA/general_ema.csv` | `uid, day, phq4_score` | 3,029 (2,889 answered) |
| `Demographics/demographics.csv` | `uid` | 200 |

There are 200 participants, `SYN-001` to `SYN-200`, with daily rows from 2026-04-23 to 2026-10-19. The files have the same names, columns and formats as the CES files the app reads, so the app runs on them unchanged. They take up about 0.8 MB.

## How it was generated

`scripts/make_synthetic_dataset.py`, seed `20261020`. Every value is drawn from NumPy's seeded generator (`numpy.random.default_rng`). The script never opens the real `dataset/` folder, and it refuses to write into it. The column layout was taken from the app's loaders and tests, not from the real files.

- **History groups:**
  - 140 long-history participants, about 4 to 6 months. Of these, 60 have a clear within-person link between both features and PHQ-4, 60 have no link and 20 have a weak link.
  - 30 with 7 to 27 days of history.
  - 30 with under 7 days.
- **The link:** it works through one slowly varying "wellbeing" signal per person. On worse weeks a person moves less, unlocks their phone more and, if linked, reports a higher PHQ-4.
- **Imperfect data:** missing days, low-quality GPS days, implausible GPS values, zero-unlock days and unlock spikes are included, so the cleaning rules are exercised.
- **The demo participant:** the app's `local-demo` selection picks one clear-link participant with the longest complete record. The script checks this before writing.

The output is deterministic. Running the script again gives the same values: two runs, and runs under numpy 2.4.5 and 2.5.3, were byte-identical before commit. A check against the local real CES copy found no shared participant IDs. The script cannot copy rows, because it never reads them.

```
python scripts/make_synthetic_dataset.py          # rewrites data/synthetic/
```

On Windows pandas writes CRLF line endings; Git stores these files with LF (`.gitattributes`). The values are the same either way.

## Using it

```
# Windows PowerShell, from the repository root, with the project .venv
$env:MINDSENSE_DATASET_DIR = 'data/synthetic'
.venv\Scripts\python -m backend.statistics.bootstrap_cache --all --engine python   # once per machine
$env:MINDSENSE_SLM_RUNTIME = 'ollama'
.venv\Scripts\python -m uvicorn backend.api.app:app
```

`/health` and `/models` then report `dataset: synthetic`, and the UI shows "Demo mode: synthetic data".

**The bootstrap cache is not committed.** Its fingerprint records the exact Python, numpy, pandas and scipy versions, and the dataset folder name. `requirements.txt` does not pin all of these, so a cache built on one machine is usually stale on another. Build it locally with the command above; it writes to `outputs/bootstrap_cache_datasets/synthetic/`. If the server log shows `bootstrap_cache_unusable`, the cache does not match the running interpreter and every answer falls back to "no claim". Rebuild it, or start the server with the interpreter that built it.

## Privacy

Only this folder is shared. The real CES copy at `dataset/` stays git-ignored. `tests/privacy/test_synthetic_dataset_privacy.py` checks three things:
- the real files can't be committed;
- this folder contains only the expected generated files and `SYN-` identifiers;
- the committed files match what the generator produces.
