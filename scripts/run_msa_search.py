#!/usr/bin/env python3
"""
Run local MSA search using MMseqs2/ColabFold databases.

This script generates Multiple Sequence Alignments (MSAs) from local databases
using colabfold_search, producing A3M files that can be used by colabfold_batch.

Usage:
    python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db

This is part of the CombFold clean pipeline architecture:
    1. run_msa_search.py    → Generate MSAs (this script, optional)
    2. run_afm_predictions.py → Structure prediction
    3. run_on_pdbs.py        → Combinatorial assembly
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Default database location
DEFAULT_DB_PATH = os.environ.get("COLABFOLD_DB", "/cache/colabfold_db")


def get_msa_status(fasta_name: str, output_folder: str) -> str:
    """
    Check MSA generation status for a FASTA file.

    Args:
        fasta_name: FASTA filename (without extension)
        output_folder: Output folder containing MSAs

    Returns:
        'completed': A3M file exists
        'not_started': No MSA found
    """
    if not os.path.exists(output_folder):
        return 'not_started'

    # Check for A3M file (ColabFold search output)
    a3m_patterns = [
        os.path.join(output_folder, f"{fasta_name}.a3m"),
        os.path.join(output_folder, fasta_name, f"{fasta_name}.a3m"),
        os.path.join(output_folder, f"{fasta_name}_env.a3m"),
    ]

    for pattern in a3m_patterns:
        if os.path.exists(pattern):
            return 'completed'

    return 'not_started'


def check_database(db_path: str) -> Tuple[bool, str]:
    """
    Verify that the MMseqs2 database exists and is valid.

    Args:
        db_path: Path to database directory

    Returns:
        Tuple of (is_valid, message)
    """
    if not os.path.exists(db_path):
        return False, f"Database directory not found: {db_path}"

    # Check for UniRef30 index files
    uniref_patterns = [
        "uniref30_*_db.idx",
        "uniref30_*.idx",
    ]

    found_uniref = False
    for pattern in uniref_patterns:
        matches = glob.glob(os.path.join(db_path, pattern))
        if matches:
            found_uniref = True
            break

    if not found_uniref:
        return False, f"UniRef30 database not found in {db_path}. Run download_weights.sh --db-uniref first."

    return True, "Database OK"


def run_colabfold_search(
    fasta_path: str,
    output_folder: str,
    db_path: str,
    use_env: bool = True,
    use_templates: bool = False,
    threads: int = 4
) -> Tuple[bool, str]:
    """
    Run colabfold_search on a single FASTA file.

    Args:
        fasta_path: Path to FASTA file
        output_folder: Output folder for A3M files
        db_path: Path to MMseqs2 database
        use_env: Include environmental sequences (ColabFoldDB)
        use_templates: Search for templates (PDB70)
        threads: Number of CPU threads

    Returns:
        Tuple of (success, message)
    """
    fasta_name = Path(fasta_path).stem

    # Check if already completed
    status = get_msa_status(fasta_name, output_folder)
    if status == 'completed':
        return True, "Already completed (A3M exists)"

    os.makedirs(output_folder, exist_ok=True)

    # Build colabfold_search command
    cmd = [
        "colabfold_search",
        fasta_path,
        db_path,
        output_folder,
        "--threads", str(threads),
    ]

    if not use_env:
        cmd.append("--db1")  # UniRef30 only
    if use_templates:
        cmd.append("--use-templates")

    print(f"      Command: {' '.join(cmd[:4])} ...", flush=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per search
        )

        if result.returncode == 0:
            return True, "Success"
        else:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            return False, f"Failed: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "Timeout (exceeded 1 hour)"
    except FileNotFoundError:
        return False, "colabfold_search not found. Is MMseqs2 installed?"
    except Exception as e:
        return False, f"Exception: {str(e)}"


def process_all_fastas(
    fastas_folder: str,
    output_folder: str,
    db_path: str,
    use_env: bool = True,
    use_templates: bool = False,
    threads: int = 4
) -> Tuple[int, int, int]:
    """
    Process all FASTA files in a folder.

    Args:
        fastas_folder: Folder containing FASTA files
        output_folder: Output folder for A3M files
        db_path: Path to MMseqs2 database
        use_env: Include environmental sequences
        use_templates: Search for templates
        threads: Number of CPU threads

    Returns:
        Tuple of (completed, failed, skipped)
    """
    # Find all FASTA files
    fasta_files = sorted(glob.glob(os.path.join(fastas_folder, "*.fasta")))

    if not fasta_files:
        print(f"   No FASTA files found in {fastas_folder}", flush=True)
        return 0, 0, 0

    print(f"   Found {len(fasta_files)} FASTA file(s)", flush=True)

    completed = 0
    failed = 0
    skipped = 0

    for i, fasta_path in enumerate(fasta_files, 1):
        fasta_name = Path(fasta_path).stem
        print(f"\n   [{i}/{len(fasta_files)}] Searching MSA for {fasta_name}...", flush=True)

        # Check if already processed
        status = get_msa_status(fasta_name, output_folder)
        if status == 'completed':
            print(f"      Skipping (A3M already exists)", flush=True)
            skipped += 1
            continue

        # Run search
        success, message = run_colabfold_search(
            fasta_path,
            output_folder,
            db_path,
            use_env,
            use_templates,
            threads
        )

        if success:
            print(f"      Completed: {message}", flush=True)
            completed += 1
        else:
            print(f"      Failed: {message}", flush=True)
            failed += 1

    return completed, failed, skipped


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run local MSA search using MMseqs2/ColabFold databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db

  # UniRef30 only (faster, smaller database)
  python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db --no-env

  # With template search
  python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db --templates
        """
    )
    parser.add_argument(
        "fastas_folder",
        help="Folder containing FASTA files"
    )
    parser.add_argument(
        "output_folder",
        help="Output folder for A3M files"
    )
    parser.add_argument(
        "--db", type=str, default=DEFAULT_DB_PATH,
        help=f"Path to MMseqs2 database (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--no-env", action="store_true",
        help="Don't use environmental sequences (UniRef30 only)"
    )
    parser.add_argument(
        "--templates", action="store_true",
        help="Search for templates (requires PDB70)"
    )
    parser.add_argument(
        "--threads", type=int, default=4,
        help="Number of CPU threads (default: 4)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'='*60}", flush=True)
    print(f"ColabFold MSA Search (Local Database)", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"   Input:     {args.fastas_folder}", flush=True)
    print(f"   Output:    {args.output_folder}", flush=True)
    print(f"   Database:  {args.db}", flush=True)
    print(f"   Use Env:   {not args.no_env}", flush=True)
    print(f"   Templates: {args.templates}", flush=True)
    print(f"   Threads:   {args.threads}", flush=True)

    # Validate inputs
    if not os.path.exists(args.fastas_folder):
        print(f"\n   ERROR: FASTA folder not found: {args.fastas_folder}", flush=True)
        sys.exit(1)

    # Check database
    db_valid, db_message = check_database(args.db)
    if not db_valid:
        print(f"\n   ERROR: {db_message}", flush=True)
        print(f"\n   To download databases, run:", flush=True)
        print(f"   /app/docker/scripts/download_weights.sh --db-uniref", flush=True)
        sys.exit(1)

    print(f"   DB Status: {db_message}", flush=True)

    os.makedirs(args.output_folder, exist_ok=True)

    completed, failed, skipped = process_all_fastas(
        args.fastas_folder,
        args.output_folder,
        args.db,
        use_env=not args.no_env,
        use_templates=args.templates,
        threads=args.threads
    )

    print(f"\n{'='*60}", flush=True)
    print(f"Summary: {completed} completed, {failed} failed, {skipped} skipped", flush=True)
    print(f"{'='*60}", flush=True)

    if completed > 0 or skipped > 0:
        print(f"\nMSA files are in: {args.output_folder}", flush=True)
        print(f"Next step: run_afm_predictions.py {args.output_folder} pdbs/", flush=True)

    # Exit with error if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
