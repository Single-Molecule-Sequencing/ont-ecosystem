"""Q-score utility functions for Oxford Nanopore data.

FUNDAMENTAL RULE: Q-scores are logarithmic (Phred scale) and MUST NOT be averaged directly.
The correct procedure for averaging Q-scores is:
1. Convert each Q-score to error probability: P = 10^(-Q/10)
2. Average the probabilities
3. Convert back to Q-score: Q = -10 * log10(P_avg)

This module provides utility functions that implement this correctly.
"""

import math
from typing import Union, List, Sequence

# Try numpy for vectorized operations, fall back to pure Python
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def qscore_to_probability(qscore: float) -> float:
    """Convert a Phred Q-score to error probability.

    Formula: P = 10^(-Q/10)

    Args:
        qscore: Phred-scaled quality score (e.g., Q10 = 10% error, Q20 = 1% error)

    Returns:
        Error probability (0 to 1)

    Examples:
        >>> qscore_to_probability(10)
        0.1
        >>> qscore_to_probability(20)
        0.01
        >>> qscore_to_probability(30)
        0.001
    """
    return 10 ** (-qscore / 10)


def probability_to_qscore(probability: float, max_q: float = 60.0) -> float:
    """Convert an error probability to Phred Q-score.

    Formula: Q = -10 * log10(P)

    Args:
        probability: Error probability (0 to 1)
        max_q: Maximum Q-score to return (default 60, capped to avoid infinity)

    Returns:
        Phred-scaled quality score

    Examples:
        >>> probability_to_qscore(0.1)
        10.0
        >>> probability_to_qscore(0.01)
        20.0
        >>> probability_to_qscore(0.001)
        30.0
    """
    if probability <= 0:
        return max_q
    return min(-10 * math.log10(probability), max_q)


def mean_qscore(qscores: Sequence[float], max_q: float = 60.0) -> float:
    """Calculate mean Q-score correctly via probability space.

    IMPORTANT: Q-scores are logarithmic (Phred scale), so we MUST:
    1. Convert each Q to error probability: P = 10^(-Q/10)
    2. Average the probabilities
    3. Convert back to Q-score: Q = -10 * log10(P_avg)

    Direct averaging of Q-scores is INCORRECT and will underestimate error rates.

    Args:
        qscores: Sequence of Phred-scaled quality scores
        max_q: Maximum Q-score to return (default 60)

    Returns:
        Mean Q-score computed via probability space

    Examples:
        >>> mean_qscore([10, 20, 30])  # NOT simply 20!
        12.88...  # Weighted toward lower Q (higher error)

        >>> mean_qscore([20, 20, 20])
        20.0  # Same values = same result
    """
    if not qscores:
        return 0.0

    if len(qscores) == 1:
        return float(qscores[0])

    if HAS_NUMPY:
        # Vectorized numpy implementation
        q_array = np.asarray(qscores, dtype=np.float64)
        probs = np.power(10, -q_array / 10)
        mean_prob = np.mean(probs)
    else:
        # Pure Python fallback
        probs = [10 ** (-q / 10) for q in qscores]
        mean_prob = sum(probs) / len(probs)

    return probability_to_qscore(mean_prob, max_q)


def weighted_mean_qscore(qscores: Sequence[float], weights: Sequence[float],
                         max_q: float = 60.0) -> float:
    """Calculate weighted mean Q-score correctly via probability space.

    Useful when Q-scores have different numbers of associated bases.

    Args:
        qscores: Sequence of Phred-scaled quality scores
        weights: Weights for each Q-score (e.g., number of bases)
        max_q: Maximum Q-score to return (default 60)

    Returns:
        Weighted mean Q-score computed via probability space
    """
    if not qscores or not weights:
        return 0.0

    if len(qscores) != len(weights):
        raise ValueError("qscores and weights must have same length")

    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0

    if HAS_NUMPY:
        q_array = np.asarray(qscores, dtype=np.float64)
        w_array = np.asarray(weights, dtype=np.float64)
        probs = np.power(10, -q_array / 10)
        weighted_prob = np.sum(probs * w_array) / np.sum(w_array)
    else:
        probs = [10 ** (-q / 10) for q in qscores]
        weighted_prob = sum(p * w for p, w in zip(probs, weights)) / total_weight

    return probability_to_qscore(weighted_prob, max_q)


# Alias for backwards compatibility
phred_mean = mean_qscore
