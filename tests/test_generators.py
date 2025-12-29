#!/usr/bin/env python3
"""
Unit tests for manuscript figure and table generators.

These tests verify that generators can be imported and have the expected interface.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add paths
bin_dir = Path(__file__).parent.parent / 'bin'
generators_dir = Path(__file__).parent.parent / 'skills' / 'manuscript' / 'generators'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(generators_dir))


# =============================================================================
# Generator Import Tests
# =============================================================================

def test_import_end_reason_kde():
    """Test gen_end_reason_kde imports correctly"""
    from gen_end_reason_kde import generate_kde_plot
    assert callable(generate_kde_plot)


def test_import_end_reason_pie():
    """Test gen_end_reason_pie imports correctly"""
    from gen_end_reason_pie import generate_end_reason_pie, EndReasonPieConfig
    assert callable(generate_end_reason_pie)
    assert EndReasonPieConfig is not None


def test_import_quality_distribution():
    """Test gen_quality_distribution imports correctly"""
    from gen_quality_distribution import generate_quality_plot
    assert callable(generate_quality_plot)


def test_import_read_length_distribution():
    """Test gen_read_length_distribution imports correctly"""
    from gen_read_length_distribution import generate_length_plot
    assert callable(generate_length_plot)


def test_import_yield_timeline():
    """Test gen_yield_timeline imports correctly"""
    from gen_yield_timeline import generate_yield_timeline, YieldTimelineConfig
    assert callable(generate_yield_timeline)
    assert YieldTimelineConfig is not None


def test_import_n50_barplot():
    """Test gen_n50_barplot imports correctly"""
    from gen_n50_barplot import generate_n50_barplot, N50BarPlotConfig
    assert callable(generate_n50_barplot)
    assert N50BarPlotConfig is not None


def test_import_metrics_heatmap():
    """Test gen_metrics_heatmap imports correctly"""
    from gen_metrics_heatmap import generate_metrics_heatmap, MetricsHeatmapConfig
    assert callable(generate_metrics_heatmap)
    assert MetricsHeatmapConfig is not None


def test_import_comparison_plot():
    """Test gen_comparison_plot imports correctly"""
    from gen_comparison_plot import generate_comparison_plot
    assert callable(generate_comparison_plot)


def test_import_comparison_table():
    """Test gen_comparison_table imports correctly"""
    from gen_comparison_table import generate_comparison_table
    assert callable(generate_comparison_table)


def test_import_qc_summary_table():
    """Test gen_qc_summary_table imports correctly"""
    from gen_qc_summary_table import generate_qc_table
    assert callable(generate_qc_table)


def test_import_basecalling_table():
    """Test gen_basecalling_table imports correctly"""
    from gen_basecalling_table import generate_basecalling_table
    assert callable(generate_basecalling_table)


# =============================================================================
# Config Dataclass Tests
# =============================================================================

def test_end_reason_pie_config_defaults():
    """Test EndReasonPieConfig has sensible defaults"""
    from gen_end_reason_pie import EndReasonPieConfig
    config = EndReasonPieConfig()
    assert config.title == "Read End Reason Distribution"
    assert config.style in ["pie", "donut"]
    assert config.dpi > 0
    assert len(config.colors) > 0


def test_yield_timeline_config_defaults():
    """Test YieldTimelineConfig has sensible defaults"""
    from gen_yield_timeline import YieldTimelineConfig
    config = YieldTimelineConfig()
    assert config.title == "Cumulative Sequencing Yield"
    assert config.show_reads is True
    assert config.show_bases is True
    assert config.dpi > 0


def test_n50_barplot_config_defaults():
    """Test N50BarPlotConfig has sensible defaults"""
    from gen_n50_barplot import N50BarPlotConfig
    config = N50BarPlotConfig()
    assert config.title == "Read Length N50 Comparison"
    assert config.sort_by in ["value", "name", "none"]
    assert config.dpi > 0


def test_metrics_heatmap_config_defaults():
    """Test MetricsHeatmapConfig has sensible defaults"""
    from gen_metrics_heatmap import MetricsHeatmapConfig
    config = MetricsHeatmapConfig()
    assert config.title == "QC Metrics Comparison"
    assert config.normalize is True
    assert len(config.metric_labels) > 0
    assert len(config.higher_is_better) > 0


# =============================================================================
# Generator Function Tests (with mocked matplotlib)
# =============================================================================

@pytest.mark.skipif(
    "matplotlib" not in sys.modules and True,
    reason="matplotlib not available for plot generation tests"
)
class TestGeneratorFunctions:
    """Tests that require matplotlib"""

    def test_end_reason_pie_with_data(self, tmp_path):
        """Test end_reason_pie generates output"""
        try:
            import matplotlib
            matplotlib.use('Agg')
        except ImportError:
            pytest.skip("matplotlib not available")

        from gen_end_reason_pie import generate_end_reason_pie

        test_data = {
            "signal_positive": 2500000,
            "unblock_mux_change": 1800000,
            "data_service_unblock_mux_change": 300000,
        }

        output_path = tmp_path / "test_pie"
        result = generate_end_reason_pie(
            end_reasons=test_data,
            output_path=output_path,
            format="png"
        )

        assert result["success"] is True
        assert "output_path" in result
        assert result["data_summary"]["total_reads"] == 4600000

    def test_n50_barplot_with_data(self, tmp_path):
        """Test n50_barplot generates output"""
        try:
            import matplotlib
            matplotlib.use('Agg')
        except ImportError:
            pytest.skip("matplotlib not available")

        from gen_n50_barplot import generate_n50_barplot

        test_experiments = [
            {'id': 'exp-001', 'n50': 5000},
            {'id': 'exp-002', 'n50': 7500},
            {'id': 'exp-003', 'n50': 3200},
        ]

        output_path = tmp_path / "test_n50"
        result = generate_n50_barplot(
            experiments=test_experiments,
            output_path=output_path,
            format="png"
        )

        assert result["success"] is True
        assert result["data_summary"]["num_experiments"] == 3
        assert result["data_summary"]["max_n50"] == 7500

    def test_metrics_heatmap_with_data(self, tmp_path):
        """Test metrics_heatmap generates output"""
        try:
            import matplotlib
            matplotlib.use('Agg')
        except ImportError:
            pytest.skip("matplotlib not available")

        from gen_metrics_heatmap import generate_metrics_heatmap

        test_experiments = [
            {'id': 'exp-001', 'mean_qscore': 20.5, 'n50': 5000, 'total_reads': 1000000},
            {'id': 'exp-002', 'mean_qscore': 18.2, 'n50': 7500, 'total_reads': 1500000},
            {'id': 'exp-003', 'mean_qscore': 21.0, 'n50': 3200, 'total_reads': 800000},
        ]

        output_path = tmp_path / "test_heatmap"
        result = generate_metrics_heatmap(
            experiments=test_experiments,
            output_path=output_path,
            format="png"
        )

        assert result["success"] is True
        assert result["data_summary"]["num_experiments"] == 3


# =============================================================================
# Manuscript Registry Tests
# =============================================================================

def test_figure_generators_registered():
    """Test all figure generators are in FIGURE_GENERATORS"""
    from ont_manuscript import FIGURE_GENERATORS

    expected_figures = [
        "fig_end_reason_kde",
        "fig_end_reason_pie",
        "fig_quality_dist",
        "fig_read_length",
        "fig_yield_timeline",
        "fig_n50_barplot",
        "fig_metrics_heatmap",
        "fig_comparison",
    ]

    for fig_id in expected_figures:
        assert fig_id in FIGURE_GENERATORS, f"Missing {fig_id} in FIGURE_GENERATORS"
        assert "generator" in FIGURE_GENERATORS[fig_id]
        assert "formats" in FIGURE_GENERATORS[fig_id]


def test_table_generators_registered():
    """Test all table generators are in TABLE_GENERATORS"""
    from ont_manuscript import TABLE_GENERATORS

    expected_tables = [
        "tbl_qc_summary",
        "tbl_basecalling",
        "tbl_comparison",
        "tbl_experiment_summary",
    ]

    for tbl_id in expected_tables:
        assert tbl_id in TABLE_GENERATORS, f"Missing {tbl_id} in TABLE_GENERATORS"
        assert "generator" in TABLE_GENERATORS[tbl_id]
        assert "formats" in TABLE_GENERATORS[tbl_id]


def test_manuscript_pipelines_defined():
    """Test manuscript pipelines are properly defined"""
    from ont_manuscript import MANUSCRIPT_PIPELINES

    assert len(MANUSCRIPT_PIPELINES) >= 4

    required_pipelines = ["qc-report", "full-analysis", "comparison", "summary-only"]
    for pipeline in required_pipelines:
        assert pipeline in MANUSCRIPT_PIPELINES
        assert "description" in MANUSCRIPT_PIPELINES[pipeline]
        assert "steps" in MANUSCRIPT_PIPELINES[pipeline]
