#!/usr/bin/env python3
"""
Basecaller Calibration Analysis: ECE and Reliability Diagrams
==============================================================

This module implements Expected Calibration Error (ECE) and reliability diagram
generation for Oxford Nanopore basecaller quality assessment using plasmid truth sets.

Key features:
- Per-base calibration analysis (Phred Q → predicted error vs observed error)
- Reliability diagram plotting with binned statistics
- ECE and MCE computation (Expected/Maximum Calibration Error)
- End_reason stratification for complete vs incomplete reads
- Integration with SMA-seq plasmid standards
- Isotonic regression and Platt scaling for recalibration

Reference: Chapter 11 (SMA-seq Methodology), SMS Haplotype Framework Textbook

Author: SMS Framework Project
Date: 2025-11-15
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
import warnings


@dataclass
class CalibrationMetrics:
    """Container for calibration assessment metrics."""
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    brier: float  # Brier score
    n_bins: int  # Number of bins used
    n_bases: int  # Total bases analyzed
    bin_stats: pd.DataFrame  # Per-bin statistics


def phred_to_error_prob(Q: np.ndarray) -> np.ndarray:
    """
    Convert Phred quality scores to error probabilities.

    Q = -10 * log10(p_err)  =>  p_err = 10^(-Q/10)

    Args:
        Q: Array of Phred quality scores (float or int)

    Returns:
        p_err: Array of predicted error probabilities

    Example:
        >>> Q = np.array([10, 20, 30, 40])
        >>> p = phred_to_error_prob(Q)
        >>> print(p)  # [0.1, 0.01, 0.001, 0.0001]
    """
    return 10.0 ** (-Q / 10.0)


def error_prob_to_phred(p: np.ndarray) -> np.ndarray:
    """
    Convert error probabilities to Phred quality scores.

    Args:
        p: Array of error probabilities (must be > 0)

    Returns:
        Q: Array of Phred quality scores

    Example:
        >>> p = np.array([0.1, 0.01, 0.001])
        >>> Q = error_prob_to_phred(p)
        >>> print(Q)  # [10., 20., 30.]
    """
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=RuntimeWarning)
        Q = -10.0 * np.log10(np.clip(p, 1e-10, 1.0))
    return Q


def compute_ece(
    p_pred: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 20,
    strategy: str = 'quantile'
) -> Tuple[float, pd.DataFrame]:
    """
    Compute Expected Calibration Error (ECE) with binned statistics.

    ECE = Σ (n_b / N) * |mean_pred_b - mean_obs_b|

    Args:
        p_pred: Predicted error probabilities (per base)
        y_true: Observed errors (0 = correct, 1 = error)
        n_bins: Number of bins for calibration analysis
        strategy: Binning strategy ('quantile' or 'uniform')
            - 'quantile': Equal-frequency bins (recommended for skewed distributions)
            - 'uniform': Equal-width bins

    Returns:
        ece: Expected Calibration Error (weighted mean absolute deviation)
        bin_stats: DataFrame with per-bin statistics

    Example:
        >>> p_pred = np.array([0.01, 0.01, 0.05, 0.1, 0.1])
        >>> y_true = np.array([0, 1, 0, 1, 1])
        >>> ece, stats = compute_ece(p_pred, y_true, n_bins=2)
    """
    df = pd.DataFrame({'p_pred': p_pred, 'err': y_true})

    # Create bins
    if strategy == 'quantile':
        df['bin'] = pd.qcut(df['p_pred'], q=n_bins, duplicates='drop')
    elif strategy == 'uniform':
        df['bin'] = pd.cut(df['p_pred'], bins=n_bins, duplicates='drop')
    else:
        raise ValueError(f"Unknown binning strategy: {strategy}")

    # Aggregate per bin
    bin_stats = df.groupby('bin', observed=True).agg(
        p_pred_mean=('p_pred', 'mean'),
        p_obs_mean=('err', 'mean'),
        n_bases=('err', 'size'),
        p_pred_min=('p_pred', 'min'),
        p_pred_max=('p_pred', 'max')
    ).reset_index(drop=True)

    # Compute ECE
    N = bin_stats['n_bases'].sum()
    bin_stats['weight'] = bin_stats['n_bases'] / N
    bin_stats['deviation'] = (bin_stats['p_obs_mean'] - bin_stats['p_pred_mean']).abs()

    ece = (bin_stats['weight'] * bin_stats['deviation']).sum()

    return ece, bin_stats


def compute_mce(bin_stats: pd.DataFrame) -> float:
    """
    Compute Maximum Calibration Error (MCE).

    MCE = max_b |mean_pred_b - mean_obs_b|

    Args:
        bin_stats: Per-bin statistics from compute_ece

    Returns:
        mce: Maximum calibration error across all bins
    """
    return bin_stats['deviation'].max()


def compute_brier_score(p_pred: np.ndarray, y_true: np.ndarray) -> float:
    """
    Compute Brier score for calibration assessment.

    Brier = (1/N) * Σ (p_pred - y_true)^2

    Args:
        p_pred: Predicted error probabilities
        y_true: Observed errors (0 or 1)

    Returns:
        brier: Brier score (lower is better)

    Note:
        This uses the convention y=1 for error, y=0 for correct,
        which is opposite to typical ML convention. See Chapter 11,
        Remark after Definition of Brier Score.
    """
    return np.mean((p_pred - y_true) ** 2)


def plot_reliability_diagram(
    bin_stats: pd.DataFrame,
    title: str = "Basecaller Calibration Diagram",
    ece: Optional[float] = None,
    mce: Optional[float] = None,
    ax: Optional[plt.Axes] = None,
    show_diagonal: bool = True,
    show_histogram: bool = True
) -> plt.Axes:
    """
    Generate reliability diagram for calibration visualization.

    Points above diagonal → under-confident (observed error < predicted)
    Points below diagonal → over-confident (observed error > predicted)

    Args:
        bin_stats: Per-bin statistics from compute_ece
        title: Plot title
        ece: Expected Calibration Error (displayed in title if provided)
        mce: Maximum Calibration Error (displayed in title if provided)
        ax: Matplotlib axes (creates new figure if None)
        show_diagonal: Whether to show y=x reference line
        show_histogram: Whether to show marginal histogram of bin sizes

    Returns:
        ax: Matplotlib axes object

    Example:
        >>> ece, bin_stats = compute_ece(p_pred, y_true)
        >>> plot_reliability_diagram(bin_stats, ece=ece)
        >>> plt.show()
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))

    # Scatter plot with point sizes proportional to bin count
    scatter = ax.scatter(
        bin_stats['p_pred_mean'],
        bin_stats['p_obs_mean'],
        s=bin_stats['weight'] * 1000,  # Scale for visibility
        alpha=0.6,
        c=bin_stats['deviation'],
        cmap='RdYlGn_r',  # Red for high deviation, green for low
        edgecolors='black',
        linewidth=1
    )

    # Perfect calibration reference line
    if show_diagonal:
        lims = [
            min(bin_stats['p_pred_mean'].min(), bin_stats['p_obs_mean'].min()),
            max(bin_stats['p_pred_mean'].max(), bin_stats['p_obs_mean'].max())
        ]
        ax.plot(lims, lims, 'k--', alpha=0.5, linewidth=2, label='Perfect calibration')

    # Labels and title
    ax.set_xlabel('Predicted error probability (mean $10^{-Q/10}$)', fontsize=12)
    ax.set_ylabel('Observed error rate (empirical)', fontsize=12)

    # Add metrics to title
    title_parts = [title]
    if ece is not None:
        title_parts.append(f"ECE={ece:.4f}")
    if mce is not None:
        title_parts.append(f"MCE={mce:.4f}")
    title_parts.append(f"bins={len(bin_stats)}")
    ax.set_title(" | ".join(title_parts), fontsize=14, fontweight='bold')

    # Colorbar for deviation
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('|Predicted - Observed|', fontsize=10)

    # Grid
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Equal aspect ratio for visual clarity
    ax.set_aspect('equal', adjustable='box')

    return ax


def analyze_calibration(
    Q: np.ndarray,
    err: np.ndarray,
    n_bins: int = 20,
    strategy: str = 'quantile',
    plot: bool = True
) -> CalibrationMetrics:
    """
    Complete calibration analysis pipeline.

    Args:
        Q: Array of Phred quality scores per base
        err: Array of observed errors per base (0 or 1)
        n_bins: Number of bins for ECE calculation
        strategy: Binning strategy ('quantile' or 'uniform')
        plot: Whether to generate reliability diagram

    Returns:
        metrics: CalibrationMetrics object with ECE, MCE, Brier, and bin stats

    Example:
        >>> # Simulate data
        >>> Q = np.random.uniform(10, 40, 100000)
        >>> p_true = 10**(-Q/10)
        >>> err = (np.random.rand(100000) < p_true).astype(int)
        >>>
        >>> # Analyze calibration
        >>> metrics = analyze_calibration(Q, err, n_bins=20, plot=True)
        >>> print(f"ECE: {metrics.ece:.4f}")
        >>> print(f"MCE: {metrics.mce:.4f}")
        >>> print(f"Brier: {metrics.brier:.4f}")
    """
    # Convert Q to predicted error probabilities
    p_pred = phred_to_error_prob(Q)

    # Compute metrics
    ece, bin_stats = compute_ece(p_pred, err, n_bins=n_bins, strategy=strategy)
    mce = compute_mce(bin_stats)
    brier = compute_brier_score(p_pred, err)

    # Plot if requested
    if plot:
        plot_reliability_diagram(bin_stats, ece=ece, mce=mce)
        plt.tight_layout()

    return CalibrationMetrics(
        ece=ece,
        mce=mce,
        brier=brier,
        n_bins=len(bin_stats),
        n_bases=len(Q),
        bin_stats=bin_stats
    )


def stratify_by_end_reason(
    df: pd.DataFrame,
    end_reason_col: str = 'end_reason',
    Q_col: str = 'Q',
    err_col: str = 'err',
    n_bins: int = 20
) -> Dict[str, CalibrationMetrics]:
    """
    Stratify calibration analysis by end_reason.

    Analyzes calibration separately for:
    - signal_positive: Complete reads
    - unblock_mux_change: Truncated reads
    - Other categories as present

    Args:
        df: DataFrame with columns [end_reason, Q, err]
        end_reason_col: Column name for end_reason
        Q_col: Column name for Phred Q scores
        err_col: Column name for observed errors (0/1)
        n_bins: Number of bins for ECE calculation

    Returns:
        results: Dict mapping end_reason → CalibrationMetrics

    Example:
        >>> df = pd.DataFrame({
        ...     'Q': np.random.uniform(10, 40, 10000),
        ...     'err': np.random.randint(0, 2, 10000),
        ...     'end_reason': np.random.choice(['signal_positive', 'unblock_mux_change'], 10000)
        ... })
        >>> results = stratify_by_end_reason(df)
        >>> for er, metrics in results.items():
        ...     print(f"{er}: ECE={metrics.ece:.4f}, n={metrics.n_bases}")
    """
    results = {}

    for end_reason in df[end_reason_col].unique():
        subset = df[df[end_reason_col] == end_reason]

        if len(subset) < 100:  # Skip categories with too few bases
            print(f"Skipping {end_reason}: only {len(subset)} bases")
            continue

        Q = subset[Q_col].values
        err = subset[err_col].values

        metrics = analyze_calibration(Q, err, n_bins=n_bins, plot=False)
        results[end_reason] = metrics

        print(f"\n{end_reason} ({len(subset):,} bases):")
        print(f"  ECE: {metrics.ece:.4f}")
        print(f"  MCE: {metrics.mce:.4f}")
        print(f"  Brier: {metrics.brier:.4f}")

    return results


def compare_end_reasons(
    results: Dict[str, CalibrationMetrics],
    metric: str = 'ece'
) -> pd.DataFrame:
    """
    Compare calibration metrics across end_reason categories.

    Args:
        results: Dict from stratify_by_end_reason
        metric: Metric to compare ('ece', 'mce', 'brier')

    Returns:
        comparison: DataFrame with metrics per end_reason
    """
    data = []
    for end_reason, metrics in results.items():
        data.append({
            'end_reason': end_reason,
            'ece': metrics.ece,
            'mce': metrics.mce,
            'brier': metrics.brier,
            'n_bases': metrics.n_bases,
            'n_bins': metrics.n_bins
        })

    df = pd.DataFrame(data).sort_values(metric)
    return df


def plot_calibration_by_end_reason(
    df: pd.DataFrame,
    end_reason_col: str = 'end_reason',
    Q_col: str = 'Q',
    err_col: str = 'err',
    n_bins: int = 20,
    end_reasons: Optional[List[str]] = None
):
    """
    Generate comparative reliability diagrams stratified by end_reason.

    Args:
        df: DataFrame with [end_reason, Q, err] columns
        end_reason_col: Column name for end_reason
        Q_col: Column name for Q scores
        err_col: Column name for errors
        n_bins: Number of bins
        end_reasons: List of end_reasons to plot (None = all)

    Example:
        >>> plot_calibration_by_end_reason(
        ...     df,
        ...     end_reasons=['signal_positive', 'unblock_mux_change']
        ... )
        >>> plt.show()
    """
    if end_reasons is None:
        end_reasons = df[end_reason_col].unique()

    n_plots = len(end_reasons)
    fig, axes = plt.subplots(1, n_plots, figsize=(6*n_plots, 6))

    if n_plots == 1:
        axes = [axes]

    for ax, end_reason in zip(axes, end_reasons):
        subset = df[df[end_reason_col] == end_reason]

        if len(subset) < 100:
            ax.text(0.5, 0.5, f'Insufficient data\n({len(subset)} bases)',
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(end_reason)
            continue

        Q = subset[Q_col].values
        err = subset[err_col].values

        metrics = analyze_calibration(Q, err, n_bins=n_bins, plot=False)
        plot_reliability_diagram(
            metrics.bin_stats,
            title=f"{end_reason}\n({metrics.n_bases:,} bases)",
            ece=metrics.ece,
            mce=metrics.mce,
            ax=ax
        )

    plt.tight_layout()
    return fig, axes


def recalibrate_isotonic(
    Q_train: np.ndarray,
    err_train: np.ndarray,
    Q_test: np.ndarray
) -> np.ndarray:
    """
    Recalibrate quality scores using isotonic regression.

    Fits a monotonic mapping from predicted error to observed error,
    then applies to test set.

    Args:
        Q_train: Training Phred scores
        err_train: Training observed errors (0/1)
        Q_test: Test Phred scores to recalibrate

    Returns:
        Q_calibrated: Recalibrated Phred scores for test set

    Example:
        >>> # Train calibration on plasmid standards
        >>> Q_cal = recalibrate_isotonic(Q_plasmid, err_plasmid, Q_clinical)
        >>> # Use Q_cal for downstream classification
    """
    p_pred_train = phred_to_error_prob(Q_train)
    p_pred_test = phred_to_error_prob(Q_test)

    # Fit isotonic regression
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(p_pred_train, err_train)

    # Apply to test set
    p_calibrated = iso.predict(p_pred_test)
    Q_calibrated = error_prob_to_phred(p_calibrated)

    return Q_calibrated


def recalibrate_platt(
    Q_train: np.ndarray,
    err_train: np.ndarray,
    Q_test: np.ndarray
) -> np.ndarray:
    """
    Recalibrate quality scores using Platt scaling (logistic regression).

    Fits a parametric sigmoid mapping from predicted error to observed error.

    Args:
        Q_train: Training Phred scores
        err_train: Training observed errors (0/1)
        Q_test: Test Phred scores to recalibrate

    Returns:
        Q_calibrated: Recalibrated Phred scores for test set
    """
    p_pred_train = phred_to_error_prob(Q_train)
    p_pred_test = phred_to_error_prob(Q_test)

    # Fit logistic regression
    lr = LogisticRegression()
    lr.fit(p_pred_train.reshape(-1, 1), err_train)

    # Apply to test set
    p_calibrated = lr.predict_proba(p_pred_test.reshape(-1, 1))[:, 1]
    Q_calibrated = error_prob_to_phred(p_calibrated)

    return Q_calibrated


# ============================================================================
# Example usage for SMA-seq plasmid standards
# ============================================================================

def example_plasmid_calibration():
    """
    Example workflow for basecaller calibration using plasmid truth sets.

    Assumes you have:
    - Aligned BAM files with per-base Q scores
    - Ground truth plasmid sequences
    - end_reason metadata extracted from POD5 files

    See Chapter 11, Section 7.5 for POD5 → BAM annotation workflow.
    """
    print("=" * 70)
    print("Basecaller Calibration Example: SMA-seq Plasmid Standards")
    print("=" * 70)

    # ========================================================================
    # Step 1: Simulate per-base data (replace with real alignment data)
    # ========================================================================
    print("\nStep 1: Loading per-base alignment data...")

    np.random.seed(42)
    n_bases = 100000

    # Simulate basecaller Q scores (typical range for Dorado/Guppy)
    Q = np.random.uniform(5, 35, n_bases)

    # Simulate ground truth errors with some miscalibration
    # (real basecaller is over-confident → predicted p < true p)
    p_pred = phred_to_error_prob(Q)
    p_true = p_pred * 1.5  # Simulated 50% overconfidence
    p_true = np.clip(p_true, 0, 1)
    err = (np.random.rand(n_bases) < p_true).astype(int)

    # Simulate end_reason metadata
    end_reason = np.random.choice(
        ['signal_positive', 'unblock_mux_change', 'signal_negative'],
        size=n_bases,
        p=[0.85, 0.12, 0.03]  # Typical distribution
    )

    df = pd.DataFrame({'Q': Q, 'err': err, 'end_reason': end_reason})

    print(f"  Loaded {n_bases:,} bases")
    print(f"  Mean Q: {Q.mean():.2f}")
    print(f"  Observed error rate: {err.mean():.4f}")
    print(f"  Predicted error rate: {p_pred.mean():.4f}")

    # ========================================================================
    # Step 2: Overall calibration analysis
    # ========================================================================
    print("\nStep 2: Computing overall calibration metrics...")

    metrics_all = analyze_calibration(Q, err, n_bins=20, plot=True)
    plt.savefig('/tmp/calibration_overall.png', dpi=150, bbox_inches='tight')
    print(f"  ECE: {metrics_all.ece:.4f}")
    print(f"  MCE: {metrics_all.mce:.4f}")
    print(f"  Brier: {metrics_all.brier:.4f}")

    # ========================================================================
    # Step 3: Stratify by end_reason
    # ========================================================================
    print("\nStep 3: Stratifying calibration by end_reason...")

    results_by_er = stratify_by_end_reason(df, n_bins=20)

    comparison = compare_end_reasons(results_by_er)
    print("\nEnd reason comparison:")
    print(comparison.to_string(index=False))

    # ========================================================================
    # Step 4: Plot calibration by end_reason
    # ========================================================================
    print("\nStep 4: Generating calibration diagrams by end_reason...")

    fig, axes = plot_calibration_by_end_reason(
        df,
        end_reasons=['signal_positive', 'unblock_mux_change']
    )
    plt.savefig('/tmp/calibration_by_end_reason.png', dpi=150, bbox_inches='tight')

    # ========================================================================
    # Step 5: Recalibration
    # ========================================================================
    print("\nStep 5: Testing recalibration methods...")

    # Split into train/test
    mask_train = np.random.rand(n_bases) < 0.7
    Q_train, err_train = Q[mask_train], err[mask_train]
    Q_test, err_test = Q[~mask_train], err[~mask_train]

    # Isotonic recalibration
    Q_iso = recalibrate_isotonic(Q_train, err_train, Q_test)
    metrics_iso = analyze_calibration(Q_iso, err_test, n_bins=20, plot=False)

    print(f"  Original ECE: {analyze_calibration(Q_test, err_test, plot=False).ece:.4f}")
    print(f"  Isotonic ECE: {metrics_iso.ece:.4f}")
    print(f"  Improvement: {(1 - metrics_iso.ece/analyze_calibration(Q_test, err_test, plot=False).ece)*100:.1f}%")

    # ========================================================================
    # Step 6: Per-read aggregation (optional)
    # ========================================================================
    print("\nStep 6: Per-read calibration metrics...")

    # Simulate read assignments
    read_ids = np.random.randint(0, 1000, n_bases)
    df['read_id'] = read_ids

    # Aggregate to per-read
    per_read = df.groupby('read_id').agg(
        Q_mean=('Q', 'mean'),
        err_rate=('err', 'mean'),
        n_bases=('err', 'size'),
        end_reason=('end_reason', lambda x: x.mode()[0] if len(x) > 0 else 'unknown')
    )

    # Classify reads as error/no-error (threshold = any error)
    per_read['has_error'] = (per_read['err_rate'] > 0).astype(int)

    metrics_read = analyze_calibration(
        per_read['Q_mean'].values,
        per_read['has_error'].values,
        n_bins=15,
        plot=True
    )
    plt.savefig('/tmp/calibration_per_read.png', dpi=150, bbox_inches='tight')

    print(f"  Per-read ECE: {metrics_read.ece:.4f}")
    print(f"  Per-read MCE: {metrics_read.mce:.4f}")

    print("\n" + "=" * 70)
    print("Calibration analysis complete!")
    print("Saved plots:")
    print("  /tmp/calibration_overall.png")
    print("  /tmp/calibration_by_end_reason.png")
    print("  /tmp/calibration_per_read.png")
    print("=" * 70)


if __name__ == "__main__":
    # Run example workflow
    example_plasmid_calibration()

    # Display plots
    plt.show()
