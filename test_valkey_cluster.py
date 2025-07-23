#!/usr/bin/env python
"""
Benchmark tool for the local Valkey cluster (ports 6000-6005).

Performs several benchmarks on the cluster:
- Write performance (single and batch)
- Read performance (single and batch)
- Prime number storage and retrieval
- Cleanup after benchmarking

Uses the cluster setup from start_valkey_cluster.sh and can be run
after test_valkey_cluster.py confirms the cluster is healthy.
"""

from __future__ import annotations

import logging
import time
import random
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple
import sys
from datetime import datetime
import os

import redis
from redis.cluster import ClusterNode
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    RedisClusterException,
    ClusterDownError,
)
from tenacity import (
    retry,
    wait_exponential,
    stop_after_delay,
    retry_if_exception_type,
)

# ───────────────────────── logging ──────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger("ValkeyBenchmark")

# ─────────────────────── retry helper ───────────────────────
RETRY_EXC = (
    ConnectionError,
    TimeoutError,
    RedisClusterException,
    ClusterDownError,
)

# ─────────────────────── constants ────────────────────────
# Test key prefix to ensure we can easily identify and clean up
TEST_PREFIX = "benchmark:test:"
# Number of operations for each test
SMALL_OPS = 1000
MEDIUM_OPS = 5000
LARGE_OPS = 10000
# Prime numbers limit
PRIME_LIMIT = 10000
# Benchmark results directory
BENCHMARK_DIR = "benchmarks"


def startup_nodes() -> List[ClusterNode]:
    """Return ClusterNode list for ports 6000-6005 on localhost."""
    return [ClusterNode("127.0.0.1", p) for p in range(6000, 6006)]


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_delay(30),
    retry=retry_if_exception_type(RETRY_EXC),
    reraise=True,
)
def connect_to_cluster() -> redis.RedisCluster:
    """Connect to the Valkey cluster and return client."""
    log.info("Connecting to Valkey cluster...")

    rc = redis.RedisCluster(
        startup_nodes=startup_nodes(),
        decode_responses=True,
        require_full_coverage=False,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=100,
        socket_keepalive=True,
        health_check_interval=15,
    )

    info = rc.cluster_info()
    if info.get("cluster_state") != "ok" or int(info.get("cluster_slots_assigned", 0)) != 16384:
        raise ClusterDownError("Cluster not healthy for benchmarking")

    log.info("Connected to cluster successfully")
    return rc


def generate_large_object(size_mb: int = 50) -> str:
    """Generate a large string object of approximately the specified size in MB."""
    log.info(f"Generating a {size_mb}MB test object...")

    # Calculate bytes needed (1MB = 1,048,576 bytes)
    size_bytes = size_mb * 1024 * 1024

    # Create a base pattern with some variation to avoid extreme compression
    # This creates a somewhat random string that won't compress too efficiently
    base_pattern = ""
    for i in range(1000):
        base_pattern += f"data-block-{i}-{random.randint(1000, 9999)}-"

    # Repeat the pattern to reach desired size
    repeats = size_bytes // len(base_pattern) + 1
    large_object = base_pattern * repeats

    # Trim to exact size
    large_object = large_object[:size_bytes]

    log.info(f"Generated object of size: {len(large_object) / 1024 / 1024:.2f}MB")
    return large_object


def benchmark_single_writes(rc: redis.RedisCluster, n_ops: int) -> float:
    """Benchmark individual SET operations."""
    log.info(f"Benchmarking {n_ops} individual SET operations...")

    start_time = time.time()
    for i in range(n_ops):
        key = f"{TEST_PREFIX}single:{i}"
        value = f"test-value-{i}-{random.randint(1000, 9999)}"
        rc.set(key, value, ex=300)  # 5-minute expiry for safety

    elapsed = time.time() - start_time
    ops_per_sec = n_ops / elapsed

    log.info(f"Single writes: {ops_per_sec:.2f} ops/sec ({elapsed:.2f}s for {n_ops} operations)")
    return ops_per_sec


def benchmark_pipeline_writes(rc: redis.RedisCluster, n_ops: int, batch_size: int = 100) -> float:
    """Benchmark pipelined SET operations."""
    log.info(f"Benchmarking {n_ops} pipelined SET operations (batch size: {batch_size})...")

    start_time = time.time()
    for batch_start in range(0, n_ops, batch_size):
        batch_end = min(batch_start + batch_size, n_ops)
        pipe = rc.pipeline(transaction=False)

        for i in range(batch_start, batch_end):
            key = f"{TEST_PREFIX}batch:{i}"
            value = f"test-batch-value-{i}-{random.randint(1000, 9999)}"
            pipe.set(key, value, ex=300)  # 5-minute expiry for safety

        pipe.execute()

    elapsed = time.time() - start_time
    ops_per_sec = n_ops / elapsed

    log.info(f"Pipelined writes: {ops_per_sec:.2f} ops/sec ({elapsed:.2f}s for {n_ops} operations)")
    return ops_per_sec


def benchmark_single_reads(rc: redis.RedisCluster, n_ops: int) -> float:
    """Benchmark individual GET operations."""
    log.info(f"Benchmarking {n_ops} individual GET operations...")

    # First ensure the keys exist
    for i in range(n_ops):
        key = f"{TEST_PREFIX}read:{i}"
        rc.set(key, f"read-value-{i}", ex=300)

    # Now benchmark reading them
    start_time = time.time()
    for i in range(n_ops):
        key = f"{TEST_PREFIX}read:{i}"
        value = rc.get(key)
        if not value:
            log.warning(f"Failed to read key {key}")

    elapsed = time.time() - start_time
    ops_per_sec = n_ops / elapsed

    log.info(f"Single reads: {ops_per_sec:.2f} ops/sec ({elapsed:.2f}s for {n_ops} operations)")
    return ops_per_sec


def benchmark_pipeline_reads(rc: redis.RedisCluster, n_ops: int, batch_size: int = 100) -> float:
    """Benchmark pipelined GET operations."""
    log.info(f"Benchmarking {n_ops} pipelined GET operations (batch size: {batch_size})...")

    # First ensure the keys exist
    pipe = rc.pipeline(transaction=False)
    for i in range(n_ops):
        key = f"{TEST_PREFIX}batch-read:{i}"
        pipe.set(key, f"batch-read-value-{i}", ex=300)
    pipe.execute()

    # Now benchmark reading them
    start_time = time.time()
    for batch_start in range(0, n_ops, batch_size):
        batch_end = min(batch_start + batch_size, n_ops)
        pipe = rc.pipeline(transaction=False)

        for i in range(batch_start, batch_end):
            key = f"{TEST_PREFIX}batch-read:{i}"
            pipe.get(key)

        pipe.execute()

    elapsed = time.time() - start_time
    ops_per_sec = n_ops / elapsed

    log.info(f"Pipelined reads: {ops_per_sec:.2f} ops/sec ({elapsed:.2f}s for {n_ops} operations)")
    return ops_per_sec


def benchmark_large_object(rc: redis.RedisCluster, size_mb: int = 50, chunks: int = 5) -> Tuple[float, float]:
    """Benchmark storing and retrieving a large object, optionally in chunks."""
    log.info(f"Starting large object benchmark ({size_mb}MB)...")

    # Generate the large object
    large_object = generate_large_object(size_mb)
    total_size = len(large_object)

    # Option 1: Store as a single value
    key_single = f"{TEST_PREFIX}large_object:single"
    start_time = time.time()
    rc.set(key_single, large_object, ex=300)  # 5-minute expiry for safety
    single_write_time = time.time() - start_time

    # Calculate MB/sec for single value write
    single_write_speed = size_mb / single_write_time
    log.info(f"Large object single write: {single_write_speed:.2f} MB/sec ({single_write_time:.2f}s for {size_mb}MB)")

    # Option 2: Split and store in chunks
    chunk_size = total_size // chunks
    start_time = time.time()

    pipe = rc.pipeline(transaction=False)
    for i in range(chunks):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < chunks - 1 else total_size
        chunk = large_object[start_idx:end_idx]
        key = f"{TEST_PREFIX}large_object:chunk:{i}"
        pipe.set(key, chunk, ex=300)
    pipe.execute()

    chunked_write_time = time.time() - start_time
    chunked_write_speed = size_mb / chunked_write_time
    log.info(
        f"Large object chunked write ({chunks} chunks): {chunked_write_speed:.2f} MB/sec ({chunked_write_time:.2f}s)")

    # Read back the single value
    start_time = time.time()
    retrieved_single = rc.get(key_single)
    single_read_time = time.time() - start_time
    single_read_speed = size_mb / single_read_time
    log.info(f"Large object single read: {single_read_speed:.2f} MB/sec ({single_read_time:.2f}s)")

    # Verify single value retrieval
    if len(retrieved_single) != total_size:
        log.error(f"Data size mismatch on single read: expected {total_size}, got {len(retrieved_single)}")

    # Read back the chunks
    start_time = time.time()
    pipe = rc.pipeline(transaction=False)
    for i in range(chunks):
        key = f"{TEST_PREFIX}large_object:chunk:{i}"
        pipe.get(key)
    retrieved_chunks = pipe.execute()

    chunked_read_time = time.time() - start_time
    chunked_read_speed = size_mb / chunked_read_time
    log.info(f"Large object chunked read ({chunks} chunks): {chunked_read_speed:.2f} MB/sec ({chunked_read_time:.2f}s)")

    # Verify chunks
    reconstructed = ''.join(retrieved_chunks)
    if len(reconstructed) != total_size:
        log.error(f"Data size mismatch on chunked read: expected {total_size}, got {len(reconstructed)}")

    # Return write and read speeds for the most efficient method
    write_speed = max(single_write_speed, chunked_write_speed)
    read_speed = max(single_read_speed, chunked_read_speed)

    return write_speed, read_speed


def plot_results(results: Dict[str, float], title: str, filename: str) -> None:
    """Generate a bar chart of benchmark results."""
    fig, ax = plt.subplots(figsize=(10, 6))

    operations = list(results.keys())
    values = [results[op] for op in operations]

    colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']

    bars = ax.bar(operations, values, color=colors[:len(operations)])

    # Add labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1 * max(values),
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9)

    # Set y-label based on title
    y_label = "Operations per second" if "ops/sec" in title else "MB per second"
    ax.set_ylabel(y_label)
    ax.set_title(f'Valkey Cluster Benchmark: {title}')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=30, ha='right')

    # Add timestamp to the plot
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plt.figtext(0.95, 0.01, f'Generated: {timestamp}',
                horizontalalignment='right', fontsize=8)

    plt.tight_layout()

    # Ensure benchmarks directory exists
    os.makedirs(BENCHMARK_DIR, exist_ok=True)

    # Save to benchmarks directory with full path
    filepath = os.path.join(BENCHMARK_DIR, filename)
    plt.savefig(filepath)
    log.info(f"Benchmark results chart saved to {filepath}")


def cleanup_test_keys(rc: redis.RedisCluster) -> int:
    """Remove all benchmark keys from the cluster."""
    log.info("Cleaning up test keys...")

    # Find all keys with our test prefix
    cursor = '0'
    deleted_count = 0

    try:
        while True:
            cursor, keys = rc.scan(cursor=cursor, match=f"{TEST_PREFIX}*", count=1000)

            if keys:
                pipe = rc.pipeline(transaction=False)
                for key in keys:
                    pipe.delete(key)
                    deleted_count += 1
                pipe.execute()

            if cursor == '0':
                break

        log.info(f"Cleanup complete. Deleted {deleted_count} keys.")
    except Exception as e:
        log.error(f"Error during cleanup: {e}")
        log.info("Attempting alternative cleanup method...")

        # Alternative method: delete keys one by one
        try:
            all_keys = []
            cursor = '0'
            while True:
                cursor, keys = rc.scan(cursor=cursor, match=f"{TEST_PREFIX}*", count=1000)
                all_keys.extend(keys)
                if cursor == '0':
                    break

            for key in all_keys:
                rc.delete(key)
                deleted_count += 1

            log.info(f"Alternative cleanup complete. Deleted {deleted_count} keys.")
        except Exception as e2:
            log.error(f"Alternative cleanup also failed: {e2}")

    return deleted_count


def run_benchmarks() -> None:
    """Run all benchmarks against the Valkey cluster."""
    try:
        rc = connect_to_cluster()

        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure benchmarks directory exists
        os.makedirs(BENCHMARK_DIR, exist_ok=True)

        # Run benchmarks
        results = {
            "SET (single)": benchmark_single_writes(rc, SMALL_OPS),
            "SET (pipeline)": benchmark_pipeline_writes(rc, MEDIUM_OPS),
            "GET (single)": benchmark_single_reads(rc, SMALL_OPS),
            "GET (pipeline)": benchmark_pipeline_reads(rc, MEDIUM_OPS),
        }

        try:
            # Large object benchmark (instead of prime numbers)
            write_speed, read_speed = benchmark_large_object(rc, size_mb=50, chunks=5)
            results["Large Write (MB/s)"] = write_speed
            results["Large Read (MB/s)"] = read_speed
        except Exception as e:
            log.error(f"Large object benchmark failed: {e}")
            log.info("Continuing with other benchmarks...")

        # Generate chart
        try:
            # Split results into ops/sec and MB/sec for better visualization
            ops_results = {k: v for k, v in results.items() if "MB/s" not in k}
            mb_results = {k: v for k, v in results.items() if "MB/s" in k}

            if ops_results:
                plot_results(ops_results, "Operation Performance (ops/sec)",
                             f"valkey_benchmark_ops_{timestamp}.png")

            if mb_results:
                plot_results(mb_results, "Large Object Performance (MB/sec)",
                             f"valkey_benchmark_mb_{timestamp}.png")

            # Also save results in JSON format
            try:
                import json
                results_file = os.path.join(BENCHMARK_DIR, f"valkey_benchmark_results_{timestamp}.json")
                with open(results_file, 'w') as f:
                    json.dump({k: float(f"{v:.2f}") for k, v in results.items()}, f, indent=2)
                log.info(f"Benchmark results saved to {results_file}")
            except Exception as e:
                log.error(f"Failed to save results JSON: {e}")

        except Exception as e:
            log.error(f"Failed to generate chart: {e}")

        # Clean up all test keys
        cleanup_test_keys(rc)

        # Print summary
        log.info("Benchmark complete!")
        for op, value in results.items():
            if "MB/s" in op:
                log.info(f"  • {op}: {value:.2f} MB/sec")
            else:
                log.info(f"  • {op}: {value:.2f} ops/sec")

        log.info(f"All benchmark results saved to '{BENCHMARK_DIR}/' directory")

    except Exception as e:
        log.error(f"Benchmark failed: {e}")
    finally:
        # Ensure we always try to clean up, even if benchmarks fail
        try:
            if 'rc' in locals() and rc:
                cleanup_test_keys(rc)
                rc.close()
                log.info("Connection closed and resources cleaned up")
        except Exception as e:
            log.error(f"Error during final cleanup: {e}")


if __name__ == "__main__":
    log.info("Starting Valkey cluster benchmarks...")
    run_benchmarks()