# Week 8 Data-Pipeline Pilot Issue Log

## Scope

This log records data-pipeline issues identified from the Week 7 pilot and
followed up during Week 8. It distinguishes data-pipeline remediation from
API, UI, and integration work owned elsewhere.

No Tier-1 feature definitions, cleaning rules, window rules, statistical
models, or evidence contracts are changed by this work.

## W7-UI-006 — Local CES dataset not provisioned for the production path

### Pilot observation

During the Week 7 end-to-end pilot, the application health path was available,
but the real-participant `/respond` path could not complete because the
production backend could not find the required local CES dataset.

The failure was associated with the expected production path:

```text
dataset/Sensing/sensing.csv
```

This blocked the real-participant end-to-end UI path.

### Reproduction

The issue was reproduced locally during Week 8.

The available CES download used the following nested layout:

```text
dataset/CES/Sensing/sensing.csv
dataset/CES/EMA/general_ema.csv
dataset/CES/Demographics/demographics.csv
```

The production paths expected by the backend were:

```text
dataset/Sensing/sensing.csv
dataset/EMA/general_ema.csv
dataset/Demographics/demographics.csv
```

Before provisioning, checks against the direct production paths returned
`False`, while the corresponding files under `dataset/CES/` returned `True`.

Running:

```powershell
python .\backend\data_pipeline\verify_ces.py
```

also reproduced the production-path failure with a `FileNotFoundError` for
`dataset/Sensing/sensing.csv`.

No participant-level data is included in this log.

### Root cause

This was a local dataset provisioning and runtime-layout gap rather than a
defect in the frozen Tier-1 feature logic.

The repository correctly excludes `dataset/` from version control and tells
developers to obtain CES locally. However, the previous setup guidance did not
state the exact production runtime layout.

Development/validation scripts can resolve a nested CES location, while the
production backend and statistics path use the direct `dataset/...` layout.
This allowed data-pipeline development to succeed locally while leaving the
production provisioning requirement unclear.

### Data-pipeline remediation

The following remediation was added:

1. `docs/data-pipeline/ces_local_provisioning.md` defines the required
   production layout and local-only provisioning procedure.
2. The repository `Readme.md` now points teammates to that provisioning
   document.
3. The provisioning document includes explicit preflight path checks and the
   existing `backend/data_pipeline/verify_ces.py` verification step.
4. The privacy boundary remains unchanged: participant-level CES files stay
   under the gitignored `dataset/` directory and are never committed.

This remediation preserves the existing production data contract instead of
changing the frozen Tier-1 pipeline or introducing a second runtime resolver.

### Remaining cross-layer work

`W7-UI-006` also identified API/UI behaviour around unavailable local data.
Those integration concerns are separate from the data-pipeline provisioning
remediation documented here.

In particular, API handling should fail closed with a controlled response when
required local data is unavailable, and the UI should distinguish that failure
from ordinary participant-data states.

This log does not claim those API/UI changes as part of the data-pipeline fix.

### Validation status

The provisioning procedure is considered validated when all three production
path checks return `True` and the existing CES verifier can run against the
direct production layout.

End-to-end closure of `W7-UI-006` remains dependent on the corresponding
integration/UI verification where applicable.

## Week 7 critical data-pipeline bug-fix review

The Week 7 pilot did not identify a critical or blocking defect in the frozen
Tier-1 data-pipeline feature logic requiring a separate Week 7 data-pipeline
bug-fix branch.

The pilot did identify cross-layer issues, including request/feature routing
and local dataset provisioning. The provisioning issue is documented above;
routing and presentation issues belong to their respective integration/API/UI
paths.

Accordingly, there is no separate Week 7 Tier-1 data-pipeline bug-fix branch to
link.