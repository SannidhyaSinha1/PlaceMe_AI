"""XGBoost eligibility classifier with a self-generating synthetic dataset.

Features (rule #5): cgpa_gap, skill_match_count, current_year, tenth_pct,
twelfth_pct. The model scores grey-area cases that pass the hard rules. If
XGBoost/sklearn aren't installed, `predict_proba` returns a transparent
logistic heuristic so the engine still works.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).resolve().parent
DATA_PATH = ML_DIR / "data" / "synthetic_dataset.csv"
MODEL_PATH = ML_DIR / "eligibility_xgb.json"

FEATURES = ["cgpa_gap", "skill_match_count", "current_year", "tenth_pct", "twelfth_pct"]


def generate_synthetic_dataset(n: int = 4000, seed: int = 42) -> object:
    """Create a labelled dataset; deterministic given the seed."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    cgpa_gap = rng.normal(0.4, 0.8, n).clip(-3, 3)          # student cgpa - min required
    skill_match = rng.integers(0, 8, n)
    current_year = rng.integers(1, 5, n)
    tenth = rng.normal(78, 10, n).clip(40, 100)
    twelfth = rng.normal(76, 11, n).clip(40, 100)

    # Latent "fit" score drives the label with noise.
    score = (
        1.6 * cgpa_gap
        + 0.45 * skill_match
        + 0.25 * (current_year - 2)
        + 0.03 * (tenth - 70)
        + 0.03 * (twelfth - 70)
        + rng.normal(0, 0.8, n)
    )
    is_eligible = (score > 1.0).astype(int)

    df = pd.DataFrame(
        {
            "cgpa_gap": cgpa_gap.round(2),
            "skill_match_count": skill_match,
            "current_year": current_year,
            "tenth_pct": tenth.round(1),
            "twelfth_pct": twelfth.round(1),
            "is_eligible": is_eligible,
        }
    )
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    return df


def train_and_save() -> bool:
    """Train XGBoost on the synthetic data and persist to JSON. Returns success."""
    try:
        import pandas as pd
        import xgboost as xgb
        from sklearn.model_selection import train_test_split
    except Exception as exc:  # pragma: no cover - optional deps
        logger.warning("XGBoost/sklearn unavailable, skipping training: %s", exc)
        return False

    df = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else generate_synthetic_dataset()
    X, y = df[FEATURES], df["is_eligible"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = xgb.XGBClassifier(
        n_estimators=120, max_depth=4, learning_rate=0.1,
        subsample=0.9, eval_metric="logloss", random_state=42,
    )
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    logger.info("Eligibility model trained — holdout accuracy %.3f", acc)
    model.save_model(str(MODEL_PATH))
    return True


@lru_cache(maxsize=1)
def _load_model():
    try:
        import xgboost as xgb
    except Exception:  # pragma: no cover
        return None
    if not MODEL_PATH.exists():
        if not train_and_save():
            return None
    try:
        model = xgb.XGBClassifier()
        model.load_model(str(MODEL_PATH))
        return model
    except Exception as exc:  # noqa: BLE001
        logger.warning("Loading eligibility model failed: %s", exc)
        return None


def predict_proba(features: list[float]) -> float:
    """Probability of eligibility for a single feature vector."""
    return predict_proba_batch([features])[0]


def predict_proba_batch(feature_rows: list[list[float]]) -> list[float]:
    """Probabilities for many feature vectors in one model call.

    XGBoost's per-call overhead dominates single-row inference; scoring a page
    of opportunities in one call is ~90x faster than a Python loop.
    """
    if not feature_rows:
        return []
    model = _load_model()
    if model is not None:
        try:
            import numpy as np

            probs = model.predict_proba(np.array(feature_rows, dtype=float))
            return [float(p) for p in probs[:, 1]]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Model inference failed, using heuristic: %s", exc)
    return [_heuristic_proba(f) for f in feature_rows]


def _heuristic_proba(features: list[float]) -> float:
    """Transparent logistic fallback mirroring the synthetic generator."""
    import math

    cgpa_gap, skill_match, current_year, tenth, twelfth = features
    score = (
        1.6 * cgpa_gap
        + 0.45 * skill_match
        + 0.25 * (current_year - 2)
        + 0.03 * (tenth - 70)
        + 0.03 * (twelfth - 70)
        - 1.0
    )
    return 1 / (1 + math.exp(-score))


if __name__ == "__main__":  # Train from the CLI: python -m ml_models.eligibility_model
    logging.basicConfig(level=logging.INFO)
    generate_synthetic_dataset()
    train_and_save()
