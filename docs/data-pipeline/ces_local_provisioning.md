# CES Local Dataset Provisioning

## Purpose

The College Experience Study (CES) dataset is intentionally not distributed
with this repository. It contains participant-level research data and must
remain local to an authorised project machine.

This document defines the local directory layout required by the production
backend and provides a reproducible provisioning check for local development
and pilot testing.

The `dataset/` directory is gitignored and must never be committed or pushed.

## Dataset source

The project uses the College Experience Study (CES), available from Kaggle:

`subigyanepal/college-experience-dataset`

See `build-reference.md` Section 2 for the locked dataset choice, study
description, licence note, and project data assumptions.

Download the dataset locally using an authorised Kaggle account. Do not upload
the CES files to GitHub or redistribute participant-level files through the
repository.

## Required production layout

The production backend resolves CES data relative to the repository root and
requires the following layout:

```text
dataset/
|-- Sensing/
|   `-- sensing.csv
|-- EMA/
|   `-- general_ema.csv
`-- Demographics/
    `-- demographics.csv
```

The current production data-pipeline and statistics modules read these paths
directly.

A downloaded or extracted copy may instead initially look like:

```text
dataset/
`-- CES/
    |-- Sensing/
    |-- EMA/
    `-- Demographics/
```

That nested layout is not the production runtime layout. If the CES archive is
extracted under `dataset/CES/`, provision the required CES directories into
`dataset/` before starting the real-participant API path.

Do not provision StudentLife or other datasets into these CES production paths.

## Local-only provisioning

From the repository root, first confirm that the downloaded CES files exist:

```powershell
Test-Path .\dataset\CES\Sensing\sensing.csv
Test-Path .\dataset\CES\EMA\general_ema.csv
Test-Path .\dataset\CES\Demographics\demographics.csv
```

If the CES download is stored under `dataset/CES/`, copy the three required production CSV files into the expected runtime locations:

```powershell
New-Item -ItemType Directory -Force .\dataset\Sensing | Out-Null
New-Item -ItemType Directory -Force .\dataset\EMA | Out-Null
New-Item -ItemType Directory -Force .\dataset\Demographics | Out-Null

Copy-Item -LiteralPath .\dataset\CES\Sensing\sensing.csv -Destination .\dataset\Sensing\sensing.csv
Copy-Item -LiteralPath .\dataset\CES\EMA\general_ema.csv -Destination .\dataset\EMA\general_ema.csv
Copy-Item -LiteralPath .\dataset\CES\Demographics\demographics.csv -Destination .\dataset\Demographics\demographics.csv
```

This operation is local only. Both the source and provisioned copies remain
under the gitignored `dataset/` directory.

If the download was extracted elsewhere, copy the corresponding `Sensing`,
`EMA`, and `Demographics` directories into the repository's local `dataset/`
directory instead.

## Preflight check

Before starting the real-participant API path, verify the required production
files:

```powershell
Test-Path .\dataset\Sensing\sensing.csv
Test-Path .\dataset\EMA\general_ema.csv
Test-Path .\dataset\Demographics\demographics.csv
```

All three commands must return `True`.

Then run the existing CES verification:

```powershell
python .\backend\data_pipeline\verify_ces.py
```

A `FileNotFoundError` referring to one of the required files means local
provisioning is incomplete. Do not work around that error by committing CES
files to the repository.

## Privacy and repository boundary

- `dataset/` must remain gitignored.
- Never stage, commit, or push CES participant-level files.
- Do not copy raw CES UIDs or participant-level exports into tracked documentation.
- Generated participant-level analytical outputs must remain in their existing gitignored locations.
- This procedure changes only local dataset placement; it does not modify the frozen Tier-1 feature definitions, cleaning rules, statistical models, or evidence contract.

## Pilot issue addressed

Week 7 pilot issue `W7-UI-006` showed that the application health endpoint
could succeed while the real-participant `/respond` path failed because the
required local CES files had not been provisioned at the production paths.

The repository previously stated that CES should be downloaded locally but did
not document the exact runtime directory layout. This procedure makes that
local-only provisioning contract explicit and provides a preflight check before
end-to-end pilot testing.

API error handling and UI presentation of missing-data/server failures are
separate integration/UI concerns and are not changed by this provisioning
procedure.