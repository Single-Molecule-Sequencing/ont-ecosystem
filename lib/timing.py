"""
ONT Ecosystem Timing Utilities

Provides timing and profiling tools for performance measurement.

Usage:
    from lib.timing import Timer, timed, profile_block

    # Context manager
    with Timer("Processing reads"):
        process_reads()

    # Decorator
    @timed
    def my_function():
        pass

    # Profile block
    with profile_block("Analysis"):
        run_analysis()
"""

import functools
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

# Global timing registry
_timings: Dict[str, List[float]] = {}


@dataclass
class TimingResult:
    """Result of a timing operation"""
    name: str
    duration: float  # seconds
    started_at: str
    ended_at: str

    def __str__(self) -> str:
        return f"{self.name}: {self.format_duration()}"

    def format_duration(self) -> str:
        """Format duration in human-readable form"""
        if self.duration < 0.001:
            return f"{self.duration * 1000000:.1f}us"
        elif self.duration < 1:
            return f"{self.duration * 1000:.1f}ms"
        elif self.duration < 60:
            return f"{self.duration:.2f}s"
        elif self.duration < 3600:
            mins = int(self.duration // 60)
            secs = self.duration % 60
            return f"{mins}m {secs:.1f}s"
        else:
            hours = int(self.duration // 3600)
            mins = int((self.duration % 3600) // 60)
            return f"{hours}h {mins}m"


class Timer:
    """
    Context manager for timing code blocks.

    Usage:
        with Timer("Processing") as t:
            do_work()
        print(f"Took {t.duration:.2f}s")

        # Or with automatic printing
        with Timer("Processing", verbose=True):
            do_work()
    """

    def __init__(self, name: str = "Operation", verbose: bool = False):
        self.name = name
        self.verbose = verbose
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: float = 0.0
        self.result: Optional[TimingResult] = None

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        self._started_at = datetime.now().isoformat()
        if self.verbose:
            print(f"Starting: {self.name}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        self._ended_at = datetime.now().isoformat()

        self.result = TimingResult(
            name=self.name,
            duration=self.duration,
            started_at=self._started_at,
            ended_at=self._ended_at
        )

        # Register timing
        if self.name not in _timings:
            _timings[self.name] = []
        _timings[self.name].append(self.duration)

        if self.verbose:
            print(f"Completed: {self.result}")

        return False


def timed(func: Callable = None, *, name: str = None, verbose: bool = False):
    """
    Decorator for timing function execution.

    Usage:
        @timed
        def my_function():
            pass

        @timed(verbose=True)
        def my_function():
            pass

        @timed(name="CustomName")
        def my_function():
            pass
    """
    def decorator(fn: Callable) -> Callable:
        timer_name = name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with Timer(timer_name, verbose=verbose):
                return fn(*args, **kwargs)
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


@contextmanager
def profile_block(name: str, verbose: bool = True):
    """
    Context manager for profiling a block of code with detailed output.

    Usage:
        with profile_block("Data Loading"):
            load_data()
    """
    start = time.perf_counter()
    start_time = datetime.now()
    print(f"[{start_time.strftime('%H:%M:%S')}] Starting: {name}")

    try:
        yield
    finally:
        end = time.perf_counter()
        duration = end - start
        result = TimingResult(
            name=name,
            duration=duration,
            started_at=start_time.isoformat(),
            ended_at=datetime.now().isoformat()
        )
        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed: {result}")


def get_timings() -> Dict[str, List[float]]:
    """Get all recorded timings"""
    return _timings.copy()


def get_timing_stats(name: str) -> Optional[Dict[str, float]]:
    """Get statistics for a named timer"""
    if name not in _timings or not _timings[name]:
        return None

    times = _timings[name]
    return {
        "count": len(times),
        "total": sum(times),
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
    }


def clear_timings():
    """Clear all recorded timings"""
    global _timings
    _timings = {}


def print_timing_summary():
    """Print a summary of all recorded timings"""
    if not _timings:
        print("No timings recorded")
        return

    print("\n" + "=" * 60)
    print("  Timing Summary")
    print("=" * 60)

    for name, times in sorted(_timings.items()):
        stats = get_timing_stats(name)
        if stats:
            print(f"\n{name}:")
            print(f"  Count: {stats['count']}")
            print(f"  Total: {stats['total']:.3f}s")
            print(f"  Mean:  {stats['mean']:.3f}s")
            print(f"  Min:   {stats['min']:.3f}s")
            print(f"  Max:   {stats['max']:.3f}s")

    print("\n" + "=" * 60)


@dataclass
class StepTimer:
    """
    Timer for multi-step operations.

    Usage:
        timer = StepTimer("Pipeline")
        timer.start()

        timer.step("Loading data")
        load_data()

        timer.step("Processing")
        process()

        timer.finish()
        timer.print_summary()
    """
    name: str
    steps: List[Dict] = field(default_factory=list)
    _current_step: Optional[str] = None
    _step_start: Optional[float] = None
    _total_start: Optional[float] = None

    def start(self):
        """Start the timer"""
        self._total_start = time.perf_counter()
        return self

    def step(self, name: str):
        """Mark a new step"""
        now = time.perf_counter()

        # Record previous step
        if self._current_step and self._step_start:
            self.steps.append({
                "name": self._current_step,
                "duration": now - self._step_start
            })

        # Start new step
        self._current_step = name
        self._step_start = now
        return self

    def finish(self):
        """Finish timing"""
        now = time.perf_counter()

        # Record final step
        if self._current_step and self._step_start:
            self.steps.append({
                "name": self._current_step,
                "duration": now - self._step_start
            })

        self._total_duration = now - (self._total_start or now)
        return self

    def print_summary(self):
        """Print step-by-step summary"""
        print(f"\n{self.name} - Step Timing:")
        print("-" * 40)

        total = sum(s["duration"] for s in self.steps)
        for step in self.steps:
            pct = (step["duration"] / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"  {step['name']:20} {step['duration']:>8.2f}s  {bar} {pct:5.1f}%")

        print("-" * 40)
        print(f"  {'Total':20} {total:>8.2f}s")


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to human-readable form"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f}us"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {mins}m {secs:.0f}s"
