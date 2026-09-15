"""
Per-feature configuration for `backend.statistics.mixed_effects_model`'s
model-frame construction — the single place each Tier-1 feature's raw
column name, transform, and cleaning entry point are declared together.

Added 2026-09-14 to close a real bug class, recorded in commit 4a3379e's
own message: `build_model_frame` used to take a loose `value_col` +
`log_offset` pair, with `log_offset` defaulting to GPS's `+1000` offset
regardless of which feature was actually being fit — wiring in
`unlock_num_ep_0` silently reused that GPS-specific offset on a count
variable until the bug was caught by hand. `FeatureSpec` replaces both
loose parameters with one required object per feature. Neither
`build_model_frame` nor this module gives that object a GPS-shaped
default anywhere, so a caller cannot forget to specify a feature's own
transform the way `log_offset`'s default silently let them.

`value_col` is not a separate field on `FeatureSpec`: it is *derived*
from `name` as `f"{name}_clean"` — the convention both `clean_gps_distance`
and `clean_unlock_frequency` already follow — so the raw feature name and
its cleaned-column name cannot drift apart by a caller declaring them
inconsistently. See `backend.statistics.mixed_effects_model.build_model_frame`
for the complementary runtime check that still fires if a `clean_fn`
itself doesn't actually produce that column — a different failure mode
(a buggy `clean_fn`), not a mismatched declaration, and not something a
derived property can catch on its own.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.data_pipeline.cleaning import GPS_LOG_OFFSET_M
from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature
from backend.data_pipeline.unlock_frequency_feature import build_unlock_frequency_feature


def log_transform(offset: float) -> Callable[[pd.Series], pd.Series]:
    """`log(x + offset)` — e.g. GPS's `log(mean + 1000)`
    (docs/statistics/preregistration.md section 1.2)."""
    return lambda s: np.log(s + offset)


def identity_transform(s: pd.Series) -> pd.Series:
    """No transform — the trailing-window mean is used as-is. Correct for
    `unlock_num_ep_0`: raw skew/kurtosis (1.73 / 6.32) are nowhere near
    GPS's (160.5 / 35,552), and both `log(x+1)` (bimodal — the 3,736
    genuine zero-unlock days collapse onto `log(1)=0`) and `log(x+1000)`
    (compresses unlock's 0-754 range to SD 0.0509) make the distribution
    worse, not better — see docs/statistics/preregistration.md section
    1.6.2 for the full numbers and reasoning."""
    return s


@dataclass(frozen=True)
class FeatureSpec:
    """Everything `build_model_frame` needs to know about one Tier-1
    feature, in one place.

    `name`: the feature's raw column name in `Sensing/sensing.csv` (e.g.
    `"loc_dist_ep_0"`). Also the base for the cleaned column name — see
    `value_col`.

    `transform` / `transform_name`: the transform applied to the
    trailing-window mean before it becomes `x_it` (see
    `mixed_effects_model.build_trailing_predictor`). Neither field has a
    default anywhere in this module — every `FeatureSpec` instance must
    state its own transform explicitly; that requirement is the entire
    reason this dataclass exists. `transform_name` is a human-readable
    label (e.g. `"log(mean + 1000)"`, `"identity (no transform)"`)
    carried alongside the callable purely for output/audit purposes — a
    bare callable prints as an unhelpful `<function ... at 0x...>` in any
    report or manifest; `tier1_runner.py` writes this string into its
    output, not the function object.

    `clean_fn`: the feature-builder function that turns raw
    participant-day sensing rows into a frame carrying `value_col` — e.g.
    `build_gps_distance_feature`. Must be `Callable[[pd.DataFrame],
    pd.DataFrame]` — a single positional DataFrame in, DataFrame out.
    `build_gps_distance_feature` and (from 2026-09-14)
    `build_unlock_frequency_feature` already share this exact shape: the
    feature-specific arguments each one's own lower-level `clean_*`
    function needs (`quality_col` for GPS; nothing for unlock, since CES
    has no unlock quality field) are already bound *inside* the
    feature-builder function itself, not exposed at this level — so
    `Callable[[pd.DataFrame], pd.DataFrame]` is sufficient here without
    `functools.partial` or an extra `quality_col` field on this
    dataclass.
    """

    name: str
    transform: Callable[[pd.Series], pd.Series]
    transform_name: str
    clean_fn: Callable[[pd.DataFrame], pd.DataFrame]

    @property
    def value_col(self) -> str:
        return f"{self.name}_clean"


GPS_DISTANCE_SPEC = FeatureSpec(
    name="loc_dist_ep_0",
    transform=log_transform(GPS_LOG_OFFSET_M),
    transform_name=f"log(mean + {GPS_LOG_OFFSET_M})",
    clean_fn=build_gps_distance_feature,
)

UNLOCK_FREQUENCY_SPEC = FeatureSpec(
    name="unlock_num_ep_0",
    transform=identity_transform,
    transform_name="identity (no transform)",
    clean_fn=build_unlock_frequency_feature,
)

# Both confirmed Tier-1 features (feature-list-signoff.md, 2026-08-26),
# keyed by FeatureSpec.name -- the single registry tier1_runner.py (and
# any future caller that needs "all Tier-1 features") iterates over.
TIER1_FEATURE_SPECS: dict[str, FeatureSpec] = {
    GPS_DISTANCE_SPEC.name: GPS_DISTANCE_SPEC,
    UNLOCK_FREQUENCY_SPEC.name: UNLOCK_FREQUENCY_SPEC,
}
