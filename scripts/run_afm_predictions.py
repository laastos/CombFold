#!/usr/bin/env python3
"""
Run ColabFold predictions on FASTA files for CombFold batch processing.

This script processes all FASTA files in an input directory and runs
ColabFold batch predictions, placing output PDBs in the specified folder.

Usage:
    python3 run_afm_predictions.py fastas/ pdbs/ --num-models 5

Inside Docker:
    The script automatically activates the ColabFold conda environment.

Outside Docker (LocalColabFold):
    Assumes colabfold_batch is available in PATH.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def is_inside_docker() -> bool:
    """Check if running inside Docker container."""
    return os.path.exists("/.dockerenv") or os.path.exists("/app/scripts")


def get_colabfold_command() -> List[str]:
    """
    Get the command prefix for running ColabFold.

    Returns:
        Command prefix as list
    """
    # ColabFold is installed via pip in system Python (both Docker and local)
    return ["colabfold_batch"]


def get_prediction_status(fasta_name: str, output_folder: str, num_models: int) -> str:
    """
    Check prediction status for a FASTA file.

    Args:
        fasta_name: FASTA filename (without extension)
        output_folder: Output folder containing predictions
        num_models: Expected number of models

    Returns:
        'completed': All expected PDBs exist
        'partial': Some but not all PDBs exist
        'not_started': No predictions found
    """
    if not os.path.exists(output_folder):
        return 'not_started'

    # ColabFold output naming: {name}_unrelaxed_rank_{rank}_model_{model}.pdb
    # or: {name}_relaxed_rank_{rank}_model_{model}.pdb
    pattern = os.path.join(output_folder, f"{fasta_name}*_rank_*.pdb")
    pdb_files = glob.glob(pattern)

    if len(pdb_files) == 0:
        return 'not_started'
    elif len(pdb_files) >= num_models:
        return 'completed'
    else:
        return 'partial'


def run_colabfold(fasta_path: str, output_folder: str, num_models: int = 5,
                  use_gpu: bool = True, amber_relax: bool = False) -> Tuple[bool, str]:
    """
    Run ColabFold batch on a single FASTA file.

    Args:
        fasta_path: Path to FASTA file
        output_folder: Output folder for predictions
        num_models: Number of models to predict
        use_gpu: Use GPU acceleration
        amber_relax: Apply AMBER relaxation

    Returns:
        Tuple of (success, message)
    """
    fasta_name = Path(fasta_path).stem

    # Check if already completed
    status = get_prediction_status(fasta_name, output_folder, num_models)
    if status == 'completed':
        return True, f"Already completed ({num_models} models exist)"

    os.makedirs(output_folder, exist_ok=True)

    # Build command - ColabFold is installed via pip in system Python
    cmd = [
        "colabfold_batch",
        fasta_path,
        output_folder,
        "--num-models", str(num_models),
        "--model-type", "alphafold2_multimer_v3",
    ]
    if not use_gpu:
        cmd.append("--cpu")
    if amber_relax:
        cmd.append("--amber")

    print(f"      Command: colabfold_batch {fasta_path} {output_folder} ...", flush=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200  # 2 hour timeout per prediction
        )

        if result.returncode == 0:
            return True, "Success"
        else:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            return False, f"Failed: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "Timeout (exceeded 2 hours)"
    except FileNotFoundError:
        return False, "colabfold_batch not found in PATH"
    except Exception as e:
        return False, f"Exception: {str(e)}"


def copy_pdbs_to_output(colabfold_output: str, pdbs_folder: str, fasta_name: str) -> int:
    """
    Copy relevant PDB files from ColabFold output to pdbs folder.

    ColabFold creates output in: {output_folder}/{fasta_name}/
    We copy PDBs to: {pdbs_folder}/{fasta_name}_*.pdb

    Args:
        colabfold_output: ColabFold output folder
        pdbs_folder: Target pdbs folder
        fasta_name: Base name of the FASTA file

    Returns:
        Number of PDB files copied
    """
    # ColabFold may put results in a subdirectory
    search_paths = [
        os.path.join(colabfold_output, "*.pdb"),
        os.path.join(colabfold_output, fasta_name, "*.pdb"),
    ]

    copied = 0
    for pattern in search_paths:
        for pdb_path in glob.glob(pattern):
            pdb_name = os.path.basename(pdb_path)
            dest_path = os.path.join(pdbs_folder, pdb_name)

            # Only copy if not already there
            if not os.path.exists(dest_path):
                shutil.copy2(pdb_path, dest_path)
                copied += 1

    return copied


def process_all_fastas(fastas_folder: str, pdbs_folder: str, num_models: int = 5,
                       use_gpu: bool = True, amber_relax: bool = False) -> Tuple[int, int, int]:
    """
    Process all FASTA files in a folder.

    Args:
        fastas_folder: Folder containing FASTA files
        pdbs_folder: Output folder for PDBs
        num_models: Number of models per prediction
        use_gpu: Use GPU acceleration
        amber_relax: Apply AMBER relaxation

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

    # Create temporary output folder for ColabFold
    temp_output = os.path.join(pdbs_folder, "_colabfold_output")
    os.makedirs(temp_output, exist_ok=True)

    for i, fasta_path in enumerate(fasta_files, 1):
        fasta_name = Path(fasta_path).stem
        print(f"\n   [{i}/{len(fasta_files)}] Processing {fasta_name}...", flush=True)

        # Check if already processed
        status = get_prediction_status(fasta_name, pdbs_folder, num_models)
        if status == 'completed':
            print(f"      Skipping (already completed)", flush=True)
            skipped += 1
            continue

        # Run prediction
        success, message = run_colabfold(
            fasta_path,
            temp_output,
            num_models,
            use_gpu,
            amber_relax
        )

        if success:
            # Copy PDBs to output folder
            copied = copy_pdbs_to_output(temp_output, pdbs_folder, fasta_name)
            print(f"      Completed: {copied} PDB(s) copied", flush=True)
            completed += 1
        else:
            print(f"      Failed: {message}", flush=True)
            failed += 1

    # Cleanup temp folder (but keep if there were failures for debugging)
    if failed == 0 and os.path.exists(temp_output):
        try:
            shutil.rmtree(temp_output)
        except Exception:
            pass

    return completed, failed, skipped


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run ColabFold predictions on FASTA files"
    )
    parser.add_argument(
        "fastas_folder",
        help="Folder containing FASTA files"
    )
    parser.add_argument(
        "pdbs_folder",
        help="Output folder for PDB predictions"
    )
    parser.add_argument(
        "--num-models", type=int, default=5,
        help="Number of models per prediction (default: 5)"
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Use CPU only (no GPU)"
    )
    parser.add_argument(
        "--amber", action="store_true",
        help="Apply AMBER relaxation to predictions"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'='*60}", flush=True)
    print(f"ColabFold Batch Predictions", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"   Input:  {args.fastas_folder}", flush=True)
    print(f"   Output: {args.pdbs_folder}", flush=True)
    print(f"   Models: {args.num_models}", flush=True)
    print(f"   Docker: {is_inside_docker()}", flush=True)
    print(f"   GPU:    {not args.cpu}", flush=True)

    if not os.path.exists(args.fastas_folder):
        print(f"\n   ERROR: FASTA folder not found: {args.fastas_folder}", flush=True)
        sys.exit(1)

    os.makedirs(args.pdbs_folder, exist_ok=True)

    completed, failed, skipped = process_all_fastas(
        args.fastas_folder,
        args.pdbs_folder,
        args.num_models,
        use_gpu=not args.cpu,
        amber_relax=args.amber
    )

    print(f"\n{'='*60}", flush=True)
    print(f"Summary: {completed} completed, {failed} failed, {skipped} skipped", flush=True)
    print(f"{'='*60}", flush=True)

    # Exit with error if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
