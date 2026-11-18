"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

import numpy as np
from scipy import stats as sp_stats

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError(f"human has {len(human)} labels but judge has {len(judge)}")
    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for h, j in zip(human, judge):
        h_pos, j_pos = h == POS, j == POS
        cm["tp" if h_pos and j_pos else "fp" if j_pos else "fn" if h_pos else "tn"] += 1
    return cm


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    flagged, actual = cm["tp"] + cm["fp"], cm["tp"] + cm["fn"]
    return (cm["tp"] / flagged if flagged else 0.0, cm["tp"] / actual if actual else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    if len(human) != len(judge):
        raise ValueError(f"human has {len(human)} labels but judge has {len(judge)}")
    n = len(human)
    if n == 0:
        raise ValueError("kappa is undefined for an empty sample")
    p_o = sum(h == j for h, j in zip(human, judge)) / n
    p_e = sum((human.count(c) / n) * (judge.count(c) / n) for c in set(human) | set(judge))
    if p_e >= 1.0:
        raise ValueError("kappa is undefined: chance agreement is 1 (a constant judge carries no signal)")
    return (p_o - p_e) / (1.0 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denom = sensitivity + specificity - 1.0
    if denom <= 0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity <= 1 (judge no better than chance)")
    return min(1.0, max(0.0, (observed_rate + specificity - 1.0) / denom))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    if len(a) != len(b):
        raise ValueError(f"paired samples need equal length, got {len(a)} and {len(b)}")
    if len(a) == 0:
        raise ValueError("paired_bootstrap needs at least one item")
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if np.array_equal(x, y):                      # no difference anywhere: scipy's CI would be degenerate
        return 0.0, 0.0, 0.0

    def mean_diff(u, v, axis=-1):
        return np.mean(u, axis=axis) - np.mean(v, axis=axis)

    res = sp_stats.bootstrap((x, y), mean_diff, paired=True, vectorized=True, n_resamples=n_resamples,
                             confidence_level=confidence, method="percentile", rng=np.random.default_rng(rng))
    low, high = res.confidence_interval
    return float(x.mean() - y.mean()), float(low), float(high)


def _check_nck(n: int, c: int, k: int) -> None:
    """Shared argument check for pass@k / pass^k: n runs, c passing, k drawn."""
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (n, c, k)):
        raise ValueError(f"n, c, k must be integers, got {n!r}, {c!r}, {k!r}")
    if n < 1:
        raise ValueError(f"need at least one run, got n={n}")
    if not 0 <= c <= n:
        raise ValueError(f"passing count c={c} must be between 0 and n={n}")
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if k > n:
        raise ValueError(f"k={k} exceeds the number of runs n={n}")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _check_nck(n, c, k)
    return 1.0 - comb(n - c, k) / comb(n, k)       # comb(n-c, k) is 0 when fewer than k trials fail


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _check_nck(n, c, k)
    return comb(c, k) / comb(n, k)                 # comb(c, k) is 0 when fewer than k trials pass
