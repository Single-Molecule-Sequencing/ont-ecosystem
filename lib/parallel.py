"""
ONT Ecosystem Parallel Processing Utilities

Thread and process pool utilities for parallel file processing,
batch operations, and concurrent task execution.

Usage:
    from lib.parallel import (
        parallel_map, parallel_process_files,
        ThreadPool, ProcessPool, TaskQueue
    )

    # Simple parallel map
    results = parallel_map(process_file, file_list, workers=4)

    # Process files in parallel with progress
    results = parallel_process_files(
        files=glob.glob("*.bam"),
        processor=analyze_bam,
        workers=8,
        progress=True
    )

    # Task queue for producer-consumer pattern
    with TaskQueue(workers=4) as queue:
        for item in items:
            queue.submit(process_item, item)
        results = queue.results()
"""

import os
import sys
import time
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, TypeVar, Union

T = TypeVar("T")
R = TypeVar("R")


# =============================================================================
# Configuration
# =============================================================================

def get_default_workers() -> int:
    """Get default number of workers based on CPU count."""
    cpu_count = os.cpu_count() or 1
    # Leave some cores free for system
    return max(1, cpu_count - 1)


def get_optimal_workers(task_type: str = "io") -> int:
    """
    Get optimal worker count for task type.

    Args:
        task_type: "io" for I/O bound, "cpu" for CPU bound

    Returns:
        Recommended worker count
    """
    cpu_count = os.cpu_count() or 1

    if task_type == "io":
        # I/O bound tasks can use more workers
        return min(32, cpu_count * 4)
    else:
        # CPU bound tasks should match core count
        return cpu_count


# =============================================================================
# Result Types
# =============================================================================

@dataclass
class TaskResult:
    """Result of a parallel task execution."""
    task_id: Any
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.success


@dataclass
class BatchResult:
    """Result of a batch parallel operation."""
    total: int
    succeeded: int
    failed: int
    results: List[TaskResult]
    duration: float

    @property
    def success_rate(self) -> float:
        return self.succeeded / self.total if self.total > 0 else 0.0

    def failures(self) -> List[TaskResult]:
        return [r for r in self.results if not r.success]

    def successes(self) -> List[TaskResult]:
        return [r for r in self.results if r.success]


# =============================================================================
# Simple Parallel Map
# =============================================================================

def parallel_map(
    func: Callable[[T], R],
    items: Iterable[T],
    workers: Optional[int] = None,
    use_processes: bool = False,
    timeout: Optional[float] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[R]:
    """
    Apply function to items in parallel.

    Args:
        func: Function to apply
        items: Items to process
        workers: Number of workers (default: auto)
        use_processes: Use processes instead of threads
        timeout: Timeout per task in seconds
        progress_callback: Called with (completed, total)

    Returns:
        List of results in order
    """
    items_list = list(items)
    total = len(items_list)

    if total == 0:
        return []

    workers = workers or get_default_workers()
    workers = min(workers, total)

    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

    results = [None] * total
    completed = 0

    with executor_class(max_workers=workers) as executor:
        # Submit all tasks
        future_to_idx = {
            executor.submit(func, item): idx
            for idx, item in enumerate(items_list)
        }

        # Collect results
        for future in as_completed(future_to_idx, timeout=timeout):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                raise RuntimeError(f"Task {idx} failed: {e}") from e

            completed += 1
            if progress_callback:
                progress_callback(completed, total)

    return results


def parallel_map_unordered(
    func: Callable[[T], R],
    items: Iterable[T],
    workers: Optional[int] = None,
    use_processes: bool = False,
) -> Generator[R, None, None]:
    """
    Apply function to items in parallel, yielding results as they complete.

    Results may not be in the same order as inputs.

    Args:
        func: Function to apply
        items: Items to process
        workers: Number of workers
        use_processes: Use processes instead of threads

    Yields:
        Results as they complete
    """
    items_list = list(items)
    workers = workers or get_default_workers()
    workers = min(workers, len(items_list))

    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

    with executor_class(max_workers=workers) as executor:
        futures = [executor.submit(func, item) for item in items_list]
        for future in as_completed(futures):
            yield future.result()


# =============================================================================
# File Processing
# =============================================================================

def parallel_process_files(
    files: List[Union[str, Path]],
    processor: Callable[[Path], R],
    workers: Optional[int] = None,
    use_processes: bool = False,
    progress: bool = False,
    continue_on_error: bool = True,
) -> BatchResult:
    """
    Process files in parallel.

    Args:
        files: List of file paths
        processor: Function to process each file
        workers: Number of workers
        use_processes: Use processes instead of threads
        progress: Show progress
        continue_on_error: Continue processing if one file fails

    Returns:
        BatchResult with all results
    """
    files = [Path(f) for f in files]
    total = len(files)
    workers = workers or get_default_workers()
    workers = min(workers, total)

    results: List[TaskResult] = []
    start_time = time.time()

    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

    with executor_class(max_workers=workers) as executor:
        future_to_file = {
            executor.submit(_process_file_wrapper, processor, f): f
            for f in files
        }

        completed = 0
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            task_result = future.result()
            task_result.task_id = str(file_path)
            results.append(task_result)

            completed += 1
            if progress:
                _print_progress(completed, total, file_path.name)

            if not task_result.success and not continue_on_error:
                # Cancel remaining tasks
                for f in future_to_file:
                    f.cancel()
                break

    if progress:
        print()  # Newline after progress

    duration = time.time() - start_time
    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded

    return BatchResult(
        total=total,
        succeeded=succeeded,
        failed=failed,
        results=results,
        duration=duration
    )


def _process_file_wrapper(processor: Callable, file_path: Path) -> TaskResult:
    """Wrapper to catch exceptions and measure timing."""
    start = time.time()
    try:
        result = processor(file_path)
        return TaskResult(
            task_id=str(file_path),
            success=True,
            result=result,
            duration=time.time() - start
        )
    except Exception as e:
        return TaskResult(
            task_id=str(file_path),
            success=False,
            error=e,
            duration=time.time() - start
        )


def _print_progress(completed: int, total: int, current: str) -> None:
    """Print progress bar."""
    percent = completed / total * 100
    bar_len = 30
    filled = int(bar_len * completed / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    current_short = current[:20] + "..." if len(current) > 20 else current
    print(f"\r[{bar}] {percent:5.1f}% ({completed}/{total}) {current_short:<25}", end="", flush=True)


# =============================================================================
# Task Queue
# =============================================================================

class TaskQueue:
    """
    Thread-safe task queue for producer-consumer pattern.

    Usage:
        with TaskQueue(workers=4) as queue:
            for item in items:
                queue.submit(process, item)
            results = queue.results()
    """

    def __init__(
        self,
        workers: Optional[int] = None,
        use_processes: bool = False,
        max_queue_size: int = 0,
    ):
        self.workers = workers or get_default_workers()
        self.use_processes = use_processes
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._results: List[TaskResult] = []
        self._results_lock = Lock()
        self._shutdown = Event()
        self._executor = None
        self._futures: List = []

    def __enter__(self):
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        self._executor = executor_class(max_workers=self.workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def submit(self, func: Callable, *args, **kwargs) -> None:
        """Submit a task to the queue."""
        if self._executor is None:
            raise RuntimeError("TaskQueue not started. Use 'with' statement.")

        future = self._executor.submit(self._execute_task, func, args, kwargs)
        self._futures.append(future)

    def _execute_task(self, func: Callable, args: tuple, kwargs: dict) -> TaskResult:
        """Execute a task and wrap result."""
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return TaskResult(
                task_id=id(func),
                success=True,
                result=result,
                duration=time.time() - start
            )
        except Exception as e:
            return TaskResult(
                task_id=id(func),
                success=False,
                error=e,
                duration=time.time() - start
            )

    def results(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """Wait for all tasks and return results."""
        results = []
        for future in as_completed(self._futures, timeout=timeout):
            results.append(future.result())
        return results

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None


# =============================================================================
# Chunked Processing
# =============================================================================

def chunked(
    items: List[T],
    chunk_size: int
) -> Generator[List[T], None, None]:
    """
    Split items into chunks.

    Args:
        items: List to split
        chunk_size: Size of each chunk

    Yields:
        Chunks of items
    """
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def parallel_chunked_process(
    items: List[T],
    processor: Callable[[List[T]], R],
    chunk_size: int,
    workers: Optional[int] = None,
    use_processes: bool = False,
) -> List[R]:
    """
    Process items in chunks in parallel.

    Useful when processing overhead is high relative to per-item work.

    Args:
        items: Items to process
        processor: Function to process a chunk of items
        chunk_size: Items per chunk
        workers: Number of workers

    Returns:
        List of results (one per chunk)
    """
    chunks = list(chunked(items, chunk_size))
    return parallel_map(processor, chunks, workers=workers, use_processes=use_processes)


# =============================================================================
# Rate-Limited Processing
# =============================================================================

def rate_limited_map(
    func: Callable[[T], R],
    items: Iterable[T],
    rate_limit: float,
    workers: int = 1,
) -> Generator[R, None, None]:
    """
    Apply function to items with rate limiting.

    Args:
        func: Function to apply
        items: Items to process
        rate_limit: Maximum calls per second
        workers: Number of workers

    Yields:
        Results as they complete
    """
    min_interval = 1.0 / rate_limit
    last_call = 0.0
    lock = Lock()

    def rate_limited_func(item: T) -> R:
        nonlocal last_call
        with lock:
            now = time.time()
            wait_time = last_call + min_interval - now
            if wait_time > 0:
                time.sleep(wait_time)
            last_call = time.time()
        return func(item)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(rate_limited_func, item) for item in items]
        for future in as_completed(futures):
            yield future.result()


# =============================================================================
# Retry Wrapper
# =============================================================================

def with_retry(
    func: Callable[..., R],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[..., R]:
    """
    Wrap function with retry logic.

    Args:
        func: Function to wrap
        max_retries: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Delay multiplier for each retry
        exceptions: Exceptions to catch and retry

    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs) -> R:
        last_exception = None
        current_delay = delay

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(current_delay)
                    current_delay *= backoff

        raise last_exception

    return wrapper
