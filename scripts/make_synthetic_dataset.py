"""Client-approved synthetic dataset for demo mode.

Writes a separate, git-ignored `dataset_synthetic/` with the same files,
columns and formats the app's CES readers use (learned from the loaders and
tests, never from the real data):

    Sensing/sensing.csv            uid, day, quality_loc, loc_dist_ep_0,
                                   unlock_num_ep_0, is_ios
    EMA/general_ema.csv            uid, day, phq4_score
    Demographics/demographics.csv  uid

`day` is a YYYYMMDD integer (both files), `loc_dist_ep_0` is metres per day,
`quality_loc` is hours of valid location sensing that day, `is_ios` is 1/0,
`phq4_score` is a PHQ-4 total (0-12).

Every value is generated; nothing is derived from the real CES files.
200 participants, SYN-001 ... SYN-200, fixed seed, daily rows ending
2026-10-19:

  * 140 long history (about 4-6 months, State C):
      60 with a clear within-person link between both features and PHQ-4,
      60 with none, 20 with a weak link;
  * 30 with 7-27 days of history (State B);
  * 30 with under 7 days (State A).

The link works through one slowly varying latent wellbeing signal per person:
on worse weeks they move less and unlock their phone more, and (for linked
people) report a higher PHQ-4. Unlinked people's PHQ-4 follows a separate,
independent signal. Missing days, low-quality GPS days, implausible GPS
values, zero-unlock days and unlock spikes are included so the cleaning
rules have something to do.

Demo participant: the app's existing local-demo selection
(`participant_evidence.select_local_demo_participant`) picks the participant
with the most valid feature days, then the most PHQ-4 answers. One clear-link
long-history participant is given the longest complete record (no missing or
low-quality days), so the selection picks them for both features without
any change to the selection code. The script checks this before writing.

    python scripts/make_synthetic_dataset.py            # -> dataset_synthetic/
    python scripts/make_synthetic_dataset.py --out DIR
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "dataset_synthetic"
SEED = 20261020
END_DATE = date(2026, 10, 19)
N_PARTICIPANTS = 200

CLEAR, NONE, WEAK, STATE_B, STATE_A = "clear", "none", "weak", "state_b", "state_a"
PROFILE_COUNTS = {CLEAR: 60, NONE: 60, WEAK: 20, STATE_B: 30, STATE_A: 30}
LONG_HISTORY_DAYS = (120, 175)  # about 4 to 6 months
DEMO_HISTORY_DAYS = 180  # strictly longest and complete: the demo pick
STATE_B_DAYS = (9, 26)  # 7-27 calendar days; enough for >= 5 valid days and 1 EMA
STATE_A_DAYS = (2, 6)  # under 7 calendar days

# Mirrors backend.data_pipeline.cleaning's rules only to check the demo pick
# (quality gate 12 h; GPS over 500 km -> NA; negative unlocks -> NA).
_QUALITY_MIN_HOURS = 12
_GPS_MAX_M = 500_000


@dataclass(frozen=True)
class Person:
    uid: str
    profile: str
    n_days: int
    is_ios: int
    demo: bool = False


def _latent(rng: np.random.Generator, n: int) -> np.ndarray:
    """Slow wellbeing signal (multi-week swings), standardised to SD 1."""
    t = np.arange(n)
    period = rng.uniform(28, 56)
    signal = np.sin(2 * np.pi * t / period + rng.uniform(0, 2 * np.pi))
    signal = signal + 0.5 * np.sin(2 * np.pi * t / rng.uniform(60, 90) + rng.uniform(0, 2 * np.pi))
    ar = np.zeros(n)
    for i in range(1, n):
        ar[i] = 0.9 * ar[i - 1] + rng.normal(0, 0.25)
    signal = signal + ar
    return (signal - signal.mean()) / (signal.std() or 1.0)


def _assign_people(rng: np.random.Generator) -> list[Person]:
    profiles = [p for p, n in PROFILE_COUNTS.items() for _ in range(n)]
    assert len(profiles) == N_PARTICIPANTS
    order = rng.permutation(N_PARTICIPANTS)
    profiles = [profiles[i] for i in order]
    # The demo participant: the first clear-link person in uid order.
    demo_index = profiles.index(CLEAR)
    people = []
    for i, profile in enumerate(profiles):
        if i == demo_index:
            n_days = DEMO_HISTORY_DAYS
        elif profile in (CLEAR, NONE, WEAK):
            n_days = int(rng.integers(LONG_HISTORY_DAYS[0], LONG_HISTORY_DAYS[1] + 1))
        elif profile == STATE_B:
            n_days = int(rng.integers(STATE_B_DAYS[0], STATE_B_DAYS[1] + 1))
        else:
            n_days = int(rng.integers(STATE_A_DAYS[0], STATE_A_DAYS[1] + 1))
        is_ios = int(rng.random() < 0.7)
        people.append(Person(f"SYN-{i + 1:03d}", profile, n_days, is_ios, demo=i == demo_index))
    return people


def _person_rows(rng: np.random.Generator, person: Person) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = person.n_days
    days = [END_DATE - timedelta(days=n - 1 - k) for k in range(n)]
    mood = _latent(rng, n)  # higher = worse wellbeing

    gps_link = {CLEAR: 0.55, WEAK: 0.35, NONE: 0.45}.get(person.profile, 0.45)
    unlock_link = {CLEAR: 0.30, WEAK: 0.20, NONE: 0.25}.get(person.profile, 0.25)
    if person.demo:
        gps_link, unlock_link = 0.65, 0.35

    # GPS distance (metres/day): lognormal around a personal level, lower on worse days.
    base_km = rng.uniform(2.5, 12.0)
    log_m = np.log(base_km * 1000) - gps_link * mood + rng.normal(0, 0.45, n)
    weekend = np.array([d.weekday() >= 5 for d in days])
    log_m = log_m + np.where(weekend, rng.uniform(-0.3, 0.3), 0.0)
    gps = np.exp(log_m)
    quality = np.clip(rng.normal(20.5, 2.0, n), 0, 24)

    # Unlocks/day: higher on worse days.
    base_unlocks = rng.uniform(55, 140) * (1.1 if person.is_ios else 0.95)
    unlocks = base_unlocks * np.exp(unlock_link * mood + rng.normal(0, 0.12, n))

    if not person.demo:
        low_quality = rng.random(n) < 0.05
        quality[low_quality] = rng.uniform(1, 11.5, low_quality.sum())
        long_trip = rng.random(n) < 0.02
        gps[long_trip] *= rng.uniform(5, 15, long_trip.sum())
        glitch = rng.random(n) < 0.004
        gps[glitch] = rng.uniform(600_000, 5_000_000, glitch.sum())
        home_day = rng.random(n) < 0.02
        gps[home_day] = 0.0
        spike = rng.random(n) < 0.015
        unlocks[spike] *= rng.uniform(2.0, 3.5, spike.sum())
        zero = rng.random(n) < 0.012
        unlocks[zero] = 0.0

    sensing = pd.DataFrame(
        {
            "uid": person.uid,
            "day": [int(d.strftime("%Y%m%d")) for d in days],
            "quality_loc": np.round(quality, 2),
            "loc_dist_ep_0": np.round(gps, 1),
            "unlock_num_ep_0": np.round(unlocks).astype(float),
            "is_ios": person.is_ios,
        }
    )
    if not person.demo:
        # Missing days: whole rows absent (phone off / app not running),
        # always at least a few so the demo stays the longest complete record.
        n_missing = max(3, int(rng.binomial(n, 0.06))) if n >= 20 else int(rng.binomial(n, 0.08))
        n_missing = min(n_missing, max(0, n - 6)) if person.profile == STATE_B else n_missing
        if person.profile == STATE_A:
            n_missing = 0
        if n_missing:
            drop = rng.choice(n, size=n_missing, replace=False)
            sensing = sensing.drop(index=drop)
        # A few days with the location value missing but the row present.
        nan_gps = rng.random(len(sensing)) < 0.01
        sensing.loc[nan_gps, "loc_dist_ep_0"] = np.nan

    # PHQ-4 roughly weekly (every 5-9 days); linked people's score tracks the
    # same latent signal, unlinked people's an independent one.
    if person.profile == CLEAR:
        phq_signal, slope = mood, 2.6
    elif person.profile == WEAK:
        phq_signal, slope = 0.35 * mood + 0.94 * _latent(rng, n), 1.6
    else:
        phq_signal, slope = _latent(rng, n), 1.8
    if person.demo:
        slope = 3.0
    base_phq = rng.uniform(2.5, 6.5)
    ema_idx = []
    k = int(rng.integers(0, 5)) if n > 7 else int(rng.integers(0, n))
    while k < n:
        ema_idx.append(k)
        k += int(rng.integers(5, 10))
    if person.profile == STATE_A and rng.random() < 0.4:
        ema_idx = []
    scores = base_phq + slope * phq_signal[ema_idx] + rng.normal(0, 0.7, len(ema_idx))
    ema = pd.DataFrame(
        {
            "uid": person.uid,
            "day": [int(days[i].strftime("%Y%m%d")) for i in ema_idx],
            "phq4_score": np.clip(np.round(scores), 0, 12),
        }
    )
    if not person.demo and len(ema) > 4:
        skipped = rng.random(len(ema)) < 0.05
        ema.loc[skipped, "phq4_score"] = np.nan
    return sensing, ema


def _valid_days(sensing: pd.DataFrame) -> pd.DataFrame:
    gps_ok = (
        sensing["loc_dist_ep_0"].notna()
        & (sensing["quality_loc"] >= _QUALITY_MIN_HOURS)
        & (sensing["loc_dist_ep_0"] <= _GPS_MAX_M)
    )
    unlock_ok = sensing["unlock_num_ep_0"].notna() & (sensing["unlock_num_ep_0"] >= 0)
    return pd.DataFrame(
        {"uid": sensing["uid"], "gps": gps_ok, "unlock": unlock_ok}
    ).groupby("uid").sum()


def generate(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    rng = np.random.default_rng(seed)
    people = _assign_people(rng)
    sensing_parts, ema_parts = [], []
    for person in people:
        s, e = _person_rows(rng, person)
        sensing_parts.append(s)
        ema_parts.append(e)
    sensing = pd.concat(sensing_parts, ignore_index=True).sort_values(["uid", "day"]).reset_index(drop=True)
    ema = pd.concat(ema_parts, ignore_index=True).sort_values(["uid", "day"]).reset_index(drop=True)
    # People without any EMA contribute empty frames, which turn `day` into float.
    ema["day"] = ema["day"].astype("int64")
    sensing["day"] = sensing["day"].astype("int64")
    demographics = pd.DataFrame({"uid": [p.uid for p in people]})

    demo_uid = next(p.uid for p in people if p.demo)
    valid = _valid_days(sensing)
    for feature in ("gps", "unlock"):
        top = valid[feature].max()
        leaders = valid.index[valid[feature] == top].tolist()
        assert leaders == [demo_uid], f"demo is not the unique {feature} leader: {leaders}"
    assert sensing["day"].max() == int(END_DATE.strftime("%Y%m%d"))
    return sensing, ema, demographics, demo_uid


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if out == (REPO_ROOT / "dataset").resolve():
        raise SystemExit("refusing to write into the real dataset/ folder")

    sensing, ema, demographics, _demo_uid = generate(args.seed)
    for sub in ("Sensing", "EMA", "Demographics"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    sensing.to_csv(out / "Sensing" / "sensing.csv", index=False)
    ema.to_csv(out / "EMA" / "general_ema.csv", index=False)
    demographics.to_csv(out / "Demographics" / "demographics.csv", index=False)
    print(
        f"wrote {out.name}/: {sensing['uid'].nunique()} participants, "
        f"{len(sensing)} sensing days, {ema['phq4_score'].notna().sum()} PHQ-4 answers, "
        f"days {sensing['day'].min()}-{sensing['day'].max()}"
    )


if __name__ == "__main__":
    main()
