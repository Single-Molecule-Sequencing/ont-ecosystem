"""Tests for utility scripts: ont_stats.py, ont_check.py, ont_help.py"""

import sys
from pathlib import Path

# Add bin to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'bin'))


# =============================================================================
# VERSION file Tests
# =============================================================================

def test_version_file_exists():
    """Test that VERSION file exists"""
    version_file = Path(__file__).parent.parent / 'VERSION'
    assert version_file.exists(), "VERSION file should exist"


def test_version_file_matches_lib():
    """Test that VERSION file matches lib/__init__.py version"""
    version_file = Path(__file__).parent.parent / 'VERSION'
    version = version_file.read_text().strip()

    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert version == lib.__version__, f"VERSION ({version}) should match lib ({lib.__version__})"


# =============================================================================
# ont_stats.py Tests
# =============================================================================

def test_stats_imports():
    """Test that ont_stats.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_stats",
        bin_dir / "ont_stats.py"
    )
    ont_stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_stats)

    assert hasattr(ont_stats, 'get_experiment_stats')
    assert hasattr(ont_stats, 'get_equation_stats')
    assert hasattr(ont_stats, 'get_generator_stats')
    assert hasattr(ont_stats, 'get_skill_stats')
    assert hasattr(ont_stats, 'get_test_stats')


def test_stats_experiment_stats():
    """Test get_experiment_stats returns valid data"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_stats",
        bin_dir / "ont_stats.py"
    )
    ont_stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_stats)

    stats = ont_stats.get_experiment_stats()
    if stats is not None:  # Registry may not exist in all environments
        assert 'total_experiments' in stats
        assert 'total_reads' in stats
        assert 'total_bases' in stats


def test_stats_skill_stats():
    """Test get_skill_stats returns valid data"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_stats",
        bin_dir / "ont_stats.py"
    )
    ont_stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_stats)

    stats = ont_stats.get_skill_stats()
    assert stats is not None
    assert 'total_skills' in stats
    assert 'skill_names' in stats
    assert stats['total_skills'] >= 7


def test_stats_generator_stats():
    """Test get_generator_stats returns valid data"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_stats",
        bin_dir / "ont_stats.py"
    )
    ont_stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_stats)

    stats = ont_stats.get_generator_stats()
    assert stats is not None
    assert 'total_generators' in stats
    assert 'figure_generators' in stats
    assert 'table_generators' in stats
    assert stats['total_generators'] >= 5


def test_stats_format_number():
    """Test number formatting function"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_stats",
        bin_dir / "ont_stats.py"
    )
    ont_stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_stats)

    assert ont_stats.format_number(500) == "500"
    assert ont_stats.format_number(1500) == "1.5K"
    assert ont_stats.format_number(1500000) == "1.5M"
    assert ont_stats.format_number(1500000000) == "1.5G"
    assert ont_stats.format_number(1500000000000) == "1.5T"


# =============================================================================
# ont_check.py Tests
# =============================================================================

def test_check_imports():
    """Test that ont_check.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    assert hasattr(ont_check, 'check_python_version')
    assert hasattr(ont_check, 'check_required_modules')
    assert hasattr(ont_check, 'check_optional_modules')
    assert hasattr(ont_check, 'check_external_tools')
    assert hasattr(ont_check, 'check_directories')
    assert hasattr(ont_check, 'check_skills')
    assert hasattr(ont_check, 'run_health_check')


def test_check_python_version():
    """Test Python version check"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    status, msg = ont_check.check_python_version()
    # Should pass since we're running on Python 3.9+
    assert status in [ont_check.PASS, ont_check.WARN]
    assert 'Python' in msg


def test_check_required_modules():
    """Test required modules check"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    results = ont_check.check_required_modules()
    assert len(results) >= 2  # pyyaml and jsonschema

    # Each result should be a tuple of (status, name, message)
    for status, name, msg in results:
        assert status in [ont_check.PASS, ont_check.FAIL]
        assert isinstance(name, str)
        assert isinstance(msg, str)


def test_check_optional_modules():
    """Test optional modules check"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    results = ont_check.check_optional_modules()
    assert len(results) >= 5  # numpy, pandas, matplotlib, pysam, etc.

    # Optional modules return PASS or INFO
    for status, name, msg in results:
        assert status in [ont_check.PASS, ont_check.INFO]


def test_check_skills():
    """Test skills check"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    status, msg = ont_check.check_skills()
    assert status == ont_check.PASS
    assert 'skills installed' in msg


def test_check_generators():
    """Test generators check"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    status, msg = ont_check.check_generators()
    assert status == ont_check.PASS
    assert 'generators available' in msg


def test_run_health_check():
    """Test full health check run"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_check",
        bin_dir / "ont_check.py"
    )
    ont_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_check)

    results = ont_check.run_health_check()

    assert 'status' in results
    assert 'checks' in results
    assert results['status'] in ['healthy', 'degraded', 'unhealthy']
    assert len(results['checks']) > 0

    # Verify check structure
    for check in results['checks']:
        assert 'category' in check
        assert 'status' in check
        assert 'message' in check


# =============================================================================
# ont_help.py Tests
# =============================================================================

def test_help_imports():
    """Test that ont_help.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_help",
        bin_dir / "ont_help.py"
    )
    ont_help = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_help)

    assert hasattr(ont_help, 'COMMANDS')
    assert hasattr(ont_help, 'EXAMPLES')
    assert hasattr(ont_help, 'print_all_commands')
    assert hasattr(ont_help, 'print_command_help')
    assert hasattr(ont_help, 'print_examples')


def test_help_commands_registry():
    """Test that COMMANDS registry is properly structured"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_help",
        bin_dir / "ont_help.py"
    )
    ont_help = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_help)

    # Should have multiple categories
    assert len(ont_help.COMMANDS) >= 3

    # Each category should have commands
    for category, commands in ont_help.COMMANDS.items():
        assert isinstance(category, str)
        assert len(commands) >= 1

        # Each command should have description and examples
        for cmd, info in commands.items():
            assert 'description' in info
            assert 'examples' in info
            assert len(info['examples']) >= 1


def test_help_core_commands_exist():
    """Test that core commands are in the registry"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_help",
        bin_dir / "ont_help.py"
    )
    ont_help = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_help)

    # Flatten command names
    all_commands = []
    for commands in ont_help.COMMANDS.values():
        all_commands.extend(commands.keys())

    # Check for essential commands
    assert 'ont_experiments.py' in all_commands
    assert 'ont_stats.py' in all_commands
    assert 'ont_check.py' in all_commands
    assert 'end_reason.py' in all_commands


# =============================================================================
# lib/logging_config.py Tests
# =============================================================================

def test_logging_config_imports():
    """Test that logging_config.py can be imported"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "logging_config",
        lib_dir / "logging_config.py"
    )
    logging_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logging_config)

    assert hasattr(logging_config, 'setup_logging')
    assert hasattr(logging_config, 'get_logger')
    assert hasattr(logging_config, 'add_logging_args')
    assert hasattr(logging_config, 'LogContext')


def test_logging_get_logger():
    """Test get_logger returns a logger"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "logging_config",
        lib_dir / "logging_config.py"
    )
    logging_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logging_config)

    import logging
    logger = logging_config.get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert "ont" in logger.name


def test_logging_setup():
    """Test setup_logging configures handlers"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "logging_config",
        lib_dir / "logging_config.py"
    )
    logging_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logging_config)

    # Test verbose mode
    logger = logging_config.setup_logging(verbose=True, name="test_ont")
    assert len(logger.handlers) >= 1

    # Test quiet mode
    logger = logging_config.setup_logging(quiet=True, name="test_ont_quiet")
    assert len(logger.handlers) >= 1


def test_lib_exports_logging():
    """Test that lib exports logging functions"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'get_logger')
    assert hasattr(lib, 'setup_logging')
    assert callable(lib.get_logger)
    assert callable(lib.setup_logging)


# =============================================================================
# lib/timing.py Tests
# =============================================================================

def test_timing_imports():
    """Test that timing.py can be imported"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "timing",
        lib_dir / "timing.py"
    )
    timing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(timing)

    assert hasattr(timing, 'Timer')
    assert hasattr(timing, 'timed')
    assert hasattr(timing, 'profile_block')
    assert hasattr(timing, 'StepTimer')
    assert hasattr(timing, 'format_duration')


def test_timer_context_manager():
    """Test Timer context manager"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "timing",
        lib_dir / "timing.py"
    )
    timing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(timing)

    import time
    with timing.Timer("test_operation") as t:
        time.sleep(0.01)  # Sleep 10ms

    assert t.duration >= 0.01
    assert t.result is not None
    assert t.result.name == "test_operation"


def test_format_duration():
    """Test duration formatting"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "timing",
        lib_dir / "timing.py"
    )
    timing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(timing)

    # Test various durations
    assert "us" in timing.format_duration(0.0001)
    assert "ms" in timing.format_duration(0.1)
    assert "s" in timing.format_duration(5)
    assert "m" in timing.format_duration(90)
    assert "h" in timing.format_duration(3700)


def test_step_timer():
    """Test StepTimer for multi-step operations"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "timing",
        lib_dir / "timing.py"
    )
    timing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(timing)

    import time
    timer = timing.StepTimer("test_pipeline")
    timer.start()
    timer.step("step1")
    time.sleep(0.01)
    timer.step("step2")
    time.sleep(0.01)
    timer.finish()

    assert len(timer.steps) == 2
    assert timer.steps[0]["name"] == "step1"
    assert timer.steps[1]["name"] == "step2"


def test_lib_exports_timing():
    """Test that lib exports timing functions"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'Timer')
    assert hasattr(lib, 'timed')
    assert callable(lib.Timer)
    assert callable(lib.timed)


# =============================================================================
# ont_update.py Tests
# =============================================================================

def test_update_imports():
    """Test that ont_update.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_update",
        bin_dir / "ont_update.py"
    )
    ont_update = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_update)

    assert hasattr(ont_update, 'get_current_version')
    assert hasattr(ont_update, 'get_source_repo')
    assert hasattr(ont_update, 'check_for_updates')
    assert hasattr(ont_update, 'get_git_status')


def test_update_current_version():
    """Test get_current_version returns version string"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_update",
        bin_dir / "ont_update.py"
    )
    ont_update = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_update)

    version = ont_update.get_current_version()
    assert version is not None
    assert isinstance(version, str)
    assert "." in version  # Version should have dots


# =============================================================================
# ont_backup.py Tests
# =============================================================================

def test_backup_imports():
    """Test that ont_backup.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_backup",
        bin_dir / "ont_backup.py"
    )
    ont_backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_backup)

    assert hasattr(ont_backup, 'get_backup_dirs')
    assert hasattr(ont_backup, 'get_backup_metadata')
    assert hasattr(ont_backup, 'create_backup')
    assert hasattr(ont_backup, 'list_backups')
    assert hasattr(ont_backup, 'format_size')


def test_backup_format_size():
    """Test format_size function"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_backup",
        bin_dir / "ont_backup.py"
    )
    ont_backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_backup)

    assert "B" in ont_backup.format_size(500)
    assert "KB" in ont_backup.format_size(1500)
    assert "MB" in ont_backup.format_size(1500000)
    assert "GB" in ont_backup.format_size(1500000000)


def test_backup_metadata():
    """Test get_backup_metadata returns proper structure"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_backup",
        bin_dir / "ont_backup.py"
    )
    ont_backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_backup)

    metadata = ont_backup.get_backup_metadata()
    assert 'version' in metadata
    assert 'created_at' in metadata
    assert 'hostname' in metadata
    assert 'user' in metadata


# =============================================================================
# ont_doctor.py Tests
# =============================================================================

def test_doctor_imports():
    """Test that ont_doctor.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    assert hasattr(ont_doctor, 'Doctor')
    assert hasattr(ont_doctor, 'DiagnosticResult')
    assert hasattr(ont_doctor, 'print_results')


def test_doctor_diagnostic_result():
    """Test DiagnosticResult dataclass"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    result = ont_doctor.DiagnosticResult(
        name="Test Check",
        status="ok",
        message="Everything is fine",
        fix_available=False
    )
    assert result.name == "Test Check"
    assert result.status == "ok"
    assert result.fix_available is False


def test_doctor_python_version_check():
    """Test Python version diagnostic"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    doctor = ont_doctor.Doctor()
    doctor.check_python_version()

    assert len(doctor.results) == 1
    result = doctor.results[0]
    assert result.name == "Python Version"
    assert result.status in ["ok", "warning", "error"]


def test_doctor_required_packages_check():
    """Test required packages diagnostic"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    doctor = ont_doctor.Doctor()
    doctor.check_required_packages()

    assert len(doctor.results) == 1
    result = doctor.results[0]
    assert result.name == "Required Packages"
    assert result.status in ["ok", "error"]


def test_doctor_skills_check():
    """Test skills diagnostic"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    doctor = ont_doctor.Doctor()
    doctor.check_skills()

    assert len(doctor.results) == 1
    result = doctor.results[0]
    assert result.name == "Skills"
    assert result.status in ["ok", "warning", "error"]


def test_doctor_run_all_quick():
    """Test running all diagnostics in quick mode"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    doctor = ont_doctor.Doctor()
    results = doctor.run_all(quick=True)

    # Quick mode should run core checks only
    assert len(results) >= 3  # Python version, installation, required packages
    for result in results:
        assert result.status in ["ok", "warning", "error"]


def test_doctor_run_all_full():
    """Test running all diagnostics in full mode"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_doctor",
        bin_dir / "ont_doctor.py"
    )
    ont_doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_doctor)

    doctor = ont_doctor.Doctor()
    results = doctor.run_all(quick=False)

    # Full mode should run more checks
    assert len(results) >= 6
    check_names = [r.name for r in results]
    assert "Python Version" in check_names
    assert "Required Packages" in check_names
    assert "Skills" in check_names


# =============================================================================
# ont_report.py Tests
# =============================================================================

def test_report_imports():
    """Test that ont_report.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_report",
        bin_dir / "ont_report.py"
    )
    ont_report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_report)

    assert hasattr(ont_report, 'ReportGenerator')
    assert hasattr(ont_report, 'ReportSection')
    assert hasattr(ont_report, 'format_text')
    assert hasattr(ont_report, 'format_markdown')


def test_report_generator_generate():
    """Test ReportGenerator.generate() returns proper structure"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_report",
        bin_dir / "ont_report.py"
    )
    ont_report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_report)

    generator = ont_report.ReportGenerator()
    data = generator.generate()

    # Check required sections
    assert "metadata" in data
    assert "ecosystem" in data
    assert "experiments" in data
    assert "skills" in data
    assert "generators" in data
    assert "tests" in data
    assert "git" in data
    assert "dependencies" in data


def test_report_metadata():
    """Test report metadata section"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_report",
        bin_dir / "ont_report.py"
    )
    ont_report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_report)

    generator = ont_report.ReportGenerator()
    data = generator.generate()

    meta = data["metadata"]
    assert "generated_at" in meta
    assert "version" in meta
    assert "python_version" in meta


def test_report_format_text():
    """Test text formatting"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_report",
        bin_dir / "ont_report.py"
    )
    ont_report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_report)

    generator = ont_report.ReportGenerator()
    data = generator.generate()
    text = ont_report.format_text(data)

    assert "ONT Ecosystem Project Report" in text
    assert "Generated:" in text
    assert "Version:" in text


def test_report_format_markdown():
    """Test markdown formatting"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location(
        "ont_report",
        bin_dir / "ont_report.py"
    )
    ont_report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_report)

    generator = ont_report.ReportGenerator()
    data = generator.generate()
    md = ont_report.format_markdown(data)

    assert "# ONT Ecosystem Project Report" in md
    assert "## " in md  # Has section headers
    assert "|" in md  # Has tables
