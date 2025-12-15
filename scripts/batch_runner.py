#!/usr/bin/env python3
"""
Batch job orchestrator for CombFold multi-GPU processing.

This script reads job specifications from an Excel file and distributes them
across available GPUs. It monitors GPU availability by checking running processes
and automatically schedules new jobs when GPUs become free.

The scheduler uses a simple polling mechanism to detect free GPUs rather than
a queuing system like SLURM, making it suitable for standalone workstations.

Usage:
    python3 batch_runner.py
    python3 batch_runner.py --excel my_jobs.xlsx
    python3 batch_runner.py --force  # Re-run all jobs

Configuration:
    - EXCEL_FILE: Path to Excel file containing job specifications
    - GPU_COUNT: Number of GPUs available (auto-detected or env var)
    - SLEEP_INTERVAL: Seconds between GPU availability checks
"""

import argparse
import glob
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# Configuration constants
EXCEL_FILE = "batch_jobs.xlsx"
SLEEP_INTERVAL = int(os.environ.get("SLEEP_INTERVAL", "10"))  # Seconds between GPU checks
MESSAGE_INTERVAL = int(os.environ.get("MESSAGE_INTERVAL", "300"))  # Seconds between status messages
GPU_LOCK_DIR = "/tmp/combfold_gpu_locks"  # Directory for GPU lock files

# Script paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_JOB_SCRIPT = os.path.join(SCRIPT_DIR, "run_combfold_job.py")

# Docker configuration
DOCKER_IMAGE = os.environ.get("COMBFOLD_DOCKER_IMAGE", "combfold:latest")


def detect_gpu_count() -> int:
    """
    Auto-detect the number of available GPUs using nvidia-smi.

    Falls back to GPU_COUNT environment variable or default of 1
    if detection fails.

    Returns:
        int: Number of available GPUs
    """
    # First check environment variable override
    env_count = os.environ.get("GPU_COUNT")
    if env_count:
        return int(env_count)

    # Try auto-detection with nvidia-smi
    try:
        result = subprocess.run(
            ['nvidia-smi', '-L'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            gpu_lines = [l for l in result.stdout.strip().split('\n') if l.startswith('GPU')]
            if gpu_lines:
                return len(gpu_lines)
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    # Default fallback
    return 1


GPU_COUNT = detect_gpu_count()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CombFold Batch Runner - Multi-GPU protein complex assembly"
    )
    parser.add_argument(
        "--excel", type=str, default=EXCEL_FILE,
        help=f"Path to Excel file (default: {EXCEL_FILE})"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run all jobs even if already completed"
    )
    parser.add_argument(
        "--skip-afm", action="store_true",
        help="Skip AlphaFold-Multimer predictions (use existing PDBs)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="results",
        help="Base output directory (default: results)"
    )
    parser.add_argument(
        "--max-af-size", type=int, default=1800,
        help="Max combined sequence length for AFM (default: 1800)"
    )
    parser.add_argument(
        "--num-models", type=int, default=5,
        help="Number of AFM models per prediction (default: 5)"
    )
    parser.add_argument(
        "--msa-mode", type=str, default="mmseqs2_uniref_env",
        choices=["mmseqs2_uniref_env", "single_sequence", "mmseqs2_uniref"],
        help="MSA generation mode: mmseqs2_uniref_env (default, requires internet), "
             "single_sequence (offline, no MSA), mmseqs2_uniref (local database)"
    )
    return parser.parse_args()


def get_job_status(job_id: str, output_dir: str = "results") -> str:
    """
    Check the completion status of a job.

    Status levels:
    - 'completed': Has assembled_results/*.pdb files
    - 'predictions_done': Has PDBs but no assembly
    - 'fastas_created': Has FASTAs but no predictions
    - 'subunits_created': Has subunits.json only
    - 'incomplete': Job started but partial
    - 'not_started': No job directory

    Args:
        job_id: Complex_ID of the job
        output_dir: Base output directory

    Returns:
        Status string
    """
    job_dir = os.path.join(output_dir, job_id)

    if not os.path.exists(job_dir):
        return 'not_started'

    # Check for subunits.json
    subunits_path = os.path.join(job_dir, "subunits.json")
    if not os.path.exists(subunits_path):
        return 'incomplete'

    # Check for FASTAs
    fastas_dir = os.path.join(job_dir, "fastas")
    has_fastas = os.path.exists(fastas_dir) and len(glob.glob(os.path.join(fastas_dir, "*.fasta"))) > 0

    if not has_fastas:
        return 'subunits_created'

    # Check for PDBs
    pdbs_dir = os.path.join(job_dir, "pdbs")
    has_pdbs = os.path.exists(pdbs_dir) and len(glob.glob(os.path.join(pdbs_dir, "*.pdb"))) > 0

    if not has_pdbs:
        return 'fastas_created'

    # Check for assembly results
    assembled_dir = os.path.join(job_dir, "output", "assembled_results")
    has_results = os.path.exists(assembled_dir) and len(glob.glob(os.path.join(assembled_dir, "*.pdb"))) > 0

    if has_results:
        return 'completed'

    return 'predictions_done'


# Cache for completed jobs
_completed_jobs_cache: Set[str] = set()


def is_job_completed(job_id: str, output_dir: str = "results") -> bool:
    """Check if job is completed (with caching)."""
    if job_id in _completed_jobs_cache:
        return True

    status = get_job_status(job_id, output_dir)
    if status == 'completed':
        _completed_jobs_cache.add(job_id)
        return True
    return False


def ensure_lock_dir():
    """Ensure the GPU lock directory exists."""
    os.makedirs(GPU_LOCK_DIR, exist_ok=True)


def get_gpu_lock_file(gpu_id: int) -> str:
    """Get the path to a GPU lock file."""
    return os.path.join(GPU_LOCK_DIR, f"gpu_{gpu_id}.lock")


# Track active subprocesses for reaping zombies
_active_processes: Dict[int, subprocess.Popen] = {}  # gpu_id -> subprocess.Popen

# Track job info for timing reports
_job_info: Dict[int, Tuple[str, float]] = {}  # gpu_id -> (job_id, start_time)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def reap_finished_processes():
    """
    Reap any finished child processes to prevent zombies.

    Also prints job completion time when a job finishes.
    """
    finished = []
    for gpu_id, proc in _active_processes.items():
        if proc.poll() is not None:  # Process has finished
            finished.append(gpu_id)

    for gpu_id in finished:
        # Print completion time if we have job info
        if gpu_id in _job_info:
            job_id, start_time = _job_info[gpu_id]
            elapsed = time.time() - start_time
            print(f"   GPU{gpu_id} completed: {job_id} ({format_duration(elapsed)})", flush=True)
            del _job_info[gpu_id]

        del _active_processes[gpu_id]

        # Clean up the lock file
        lock_file = get_gpu_lock_file(gpu_id)
        try:
            os.remove(lock_file)
        except FileNotFoundError:
            pass


def get_running_jobs() -> Set[int]:
    """
    Check which GPUs are currently running jobs.

    Returns:
        set: GPU IDs currently in use
    """
    # First, reap any finished processes
    reap_finished_processes()

    ensure_lock_dir()
    busy_gpus: Set[int] = set()

    for gpu_id in range(GPU_COUNT):
        lock_file = get_gpu_lock_file(gpu_id)
        if os.path.exists(lock_file):
            # Check if the lock is stale
            try:
                with open(lock_file, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process is still running
                os.kill(pid, 0)  # Raises OSError if process doesn't exist
                busy_gpus.add(gpu_id)
            except (ValueError, OSError, FileNotFoundError):
                # Lock is stale, remove it
                try:
                    os.remove(lock_file)
                except FileNotFoundError:
                    pass

    return busy_gpus


def find_free_gpu() -> Optional[int]:
    """
    Find an available GPU that is not currently running a job.

    Returns:
        int or None: GPU ID if available, None if all GPUs are busy
    """
    busy = get_running_jobs()
    for gpu_id in range(GPU_COUNT):
        if gpu_id not in busy:
            return gpu_id
    return None


def acquire_gpu_lock(gpu_id: int, pid: int):
    """
    Acquire a lock for a GPU.

    Args:
        gpu_id: GPU ID to lock
        pid: Process ID holding the lock
    """
    ensure_lock_dir()
    lock_file = get_gpu_lock_file(gpu_id)
    with open(lock_file, 'w') as f:
        f.write(str(pid))


def is_inside_docker() -> bool:
    """Check if running inside Docker container."""
    return os.path.exists("/.dockerenv") or os.path.exists("/app/scripts")


def launch_in_docker(args):
    """
    Relaunch this script inside Docker with correct volume mounts.

    Args:
        args: Parsed command-line arguments
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # CombFold root
    excel_path = os.path.abspath(args.excel)

    cmd = [
        "docker", "run",
        "-t",  # Allocate pseudo-TTY for real-time output
        "--gpus", "all",
        "--ipc=host",
        "-e", "PYTHONUNBUFFERED=1",
        "-e", f"CF_FORCE_RERUN={'1' if args.force else '0'}",
        "-v", f"{script_dir}/results:/data/results",
        "-v", f"{excel_path}:/data/batch_jobs.xlsx:ro",
        "-v", f"{script_dir}/scripts:/app/scripts:ro",
        "-v", "combfold_cache:/cache",
        "-w", "/data",
        DOCKER_IMAGE,
        "python3", "-u", "/app/scripts/batch_runner.py",
        "--excel", "/data/batch_jobs.xlsx",
        "--output-dir", "/data/results"
    ]

    if args.force:
        cmd.append("--force")
    if args.skip_afm:
        cmd.append("--skip-afm")

    print(f"   Docker image: {DOCKER_IMAGE}")
    print(f"   Excel mount: {excel_path} -> /data/batch_jobs.xlsx")
    print(f"   Results mount: {script_dir}/results -> /data/results")

    os.execvp("docker", cmd)


def main():
    """
    Main orchestration loop that processes all jobs from the Excel file.

    Reads job specifications from EXCEL_FILE where:
    - 'Complex_ID' column: Job identifier (required)
    - 'Chain_*' columns: Amino acid sequences for each subunit (e.g., Chain_A, Chain_B)

    Jobs are launched asynchronously on available GPUs.
    """
    args = parse_args()

    # Get force rerun from environment (for Docker mode)
    force_rerun = args.force or os.environ.get("CF_FORCE_RERUN", "0") == "1"

    # Load job specifications from Excel
    if not os.path.exists(args.excel):
        print(f"ERROR: Excel file not found: {args.excel}")
        sys.exit(1)

    df = pd.read_excel(args.excel)

    if "Complex_ID" not in df.columns:
        raise ValueError("Excel file must contain 'Complex_ID' column")

    # Identify Chain columns by name pattern
    chain_columns = [col for col in df.columns if col.startswith("Chain_")]
    if not chain_columns:
        raise ValueError("Excel file must contain at least one 'Chain_*' column (e.g., Chain_A)")

    total_jobs = len(df)

    # Pre-scan and validate all jobs
    completed_count = 0
    incomplete_count = 0
    skipped_count = 0
    pending_jobs: List[Tuple[str, List[str], str]] = []  # (job_id, sequences, status)

    for idx, row in df.iterrows():
        job_id = str(row["Complex_ID"]).strip()
        status = get_job_status(job_id, args.output_dir)

        if status == 'completed' and not force_rerun:
            completed_count += 1
            continue

        # Extract sequences
        seqs = [
            str(row[col]).strip()
            for col in chain_columns
            if pd.notna(row[col]) and str(row[col]).strip()
        ]

        if not seqs:
            skipped_count += 1
            continue

        if status in ['predictions_done', 'fastas_created', 'subunits_created']:
            incomplete_count += 1

        pending_jobs.append((job_id, seqs, status))

    # Show startup summary
    print("=" * 60)
    print("CombFold Batch Runner")
    print("=" * 60)
    print(f"   Excel file:        {args.excel}")
    print(f"   Output directory:  {args.output_dir}")
    print(f"   Total in Excel:    {total_jobs}")
    print(f"   Already completed: {completed_count}")
    print(f"   Incomplete/retry:  {incomplete_count}")
    if skipped_count > 0:
        print(f"   Skipped (no seq):  {skipped_count}")
    print(f"   Jobs to process:   {len(pending_jobs)}")
    print(f"   GPUs available:    {GPU_COUNT} (auto-detected)")
    print(f"   Poll interval:     {SLEEP_INTERVAL}s")
    print(f"   Chain columns:     {chain_columns}")
    print(f"   Skip AFM:          {args.skip_afm}")
    print(f"   MSA Mode:          {args.msa_mode}")
    if args.msa_mode == "single_sequence":
        print(f"   WARNING:           No MSA - predictions may be less accurate")
    if force_rerun:
        print(f"   Mode:              FORCE (re-running all jobs)")
    print("=" * 60)

    if not pending_jobs:
        print("\nAll jobs already completed! Use --force to re-run.")
        return

    # Process pending jobs
    for job_num, (job_id, seqs, status) in enumerate(pending_jobs, 1):
        # Wait for an available GPU
        wait_time = 0
        printed_initial = False

        while True:
            gpu_id = find_free_gpu()
            if gpu_id is not None:
                busy = get_running_jobs()
                free_count = GPU_COUNT - len(busy)

                # Show status message
                if status != 'not_started':
                    print(f"\n[{job_num}/{len(pending_jobs)}] {job_id} -> GPU{gpu_id} (resuming from {status})", flush=True)
                else:
                    print(f"\n[{job_num}/{len(pending_jobs)}] {job_id} -> GPU{gpu_id} (free: {free_count}/{GPU_COUNT})", flush=True)

                # Build command
                cmd = [
                    sys.executable, "-u", RUN_JOB_SCRIPT,
                    "--gpu", str(gpu_id),
                    "--job_id", job_id,
                    "--output_dir", args.output_dir,
                    "--max_af_size", str(args.max_af_size),
                    "--num_models", str(args.num_models),
                    "--msa_mode", args.msa_mode,
                    "--sequences", *seqs
                ]
                if args.skip_afm:
                    cmd.append("--skip_afm")

                # Launch job asynchronously
                proc = subprocess.Popen(cmd)

                # Track process
                _active_processes[gpu_id] = proc
                _job_info[gpu_id] = (job_id, time.time())

                # Acquire GPU lock
                acquire_gpu_lock(gpu_id, proc.pid)
                break
            else:
                # All GPUs busy
                busy = get_running_jobs()
                if not printed_initial:
                    print(f"\n[{job_num}/{len(pending_jobs)}] {job_id} waiting for GPU... (busy: {sorted(busy)})", flush=True)
                    printed_initial = True
                elif wait_time > 0 and wait_time % MESSAGE_INTERVAL == 0:
                    print(f"   ... still waiting ({wait_time}s, busy: {sorted(busy)})", flush=True)
                wait_time += SLEEP_INTERVAL
                time.sleep(SLEEP_INTERVAL)

    print("\nAll jobs have been submitted")

    # Wait for all jobs to complete
    print("\nWaiting for all jobs to complete...")
    while _active_processes:
        reap_finished_processes()

        remaining = list(_active_processes.keys())
        if remaining:
            remaining_jobs = [_job_info.get(gpu, (f"GPU{gpu}", 0))[0] for gpu in remaining]
            print(f"   Running: {', '.join(remaining_jobs)} (GPUs: {remaining})", flush=True)
            time.sleep(SLEEP_INTERVAL)

    print("\n" + "=" * 60)
    print("All jobs completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Check if running outside Docker and auto-launch not disabled
    if not is_inside_docker() and os.environ.get("COMBFOLD_NO_DOCKER") != "1":
        args = parse_args()
        print("=" * 60)
        print("CombFold Batch Runner")
        print("=" * 60)
        print("NOTE: Running outside Docker.")
        print("      For full pipeline (including AFM predictions), use Docker.")
        print("      Set COMBFOLD_NO_DOCKER=1 to suppress this message.")
        print("=" * 60)
        print()

    main()
