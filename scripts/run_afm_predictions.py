#!/usr/bin/env python3
"""
Run ColabFold predictions on FASTA or A3M files for CombFold batch processing.

This script processes all FASTA/A3M files in an input directory and runs
ColabFold batch predictions, placing output PDBs in the specified folder.

This is part of the CombFold clean pipeline architecture:
    1. run_msa_search.py     → Generate MSAs (optional, for local mode)
    2. run_afm_predictions.py → Structure prediction (this script)
    3. run_on_pdbs.py         → Combinatorial assembly

Usage:
    # Online mode (uses ColabFold server for MSA)
    python3 run_afm_predictions.py fastas/ pdbs/ --num-models 5

    # Local mode (uses pre-computed A3M files)
    python3 run_afm_predictions.py msas/ pdbs/ --num-models 5 --msa-mode local

    # Offline mode (no MSA, single sequence)
    python3 run_afm_predictions.py fastas/ pdbs/ --msa-mode single_sequence
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
                  use_gpu: bool = True, amber_relax: bool = False,
                  msa_mode: str = "mmseqs2_uniref_env") -> Tuple[bool, str]:
    """
    Run ColabFold batch on a single FASTA file.

    Args:
        fasta_path: Path to FASTA file
        output_folder: Output folder for predictions
        num_models: Number of models to predict
        use_gpu: Use GPU acceleration
        amber_relax: Apply AMBER relaxation
        msa_mode: MSA generation mode:
            - 'mmseqs2_uniref_env': Use ColabFold server (requires internet)
            - 'single_sequence': No MSA, use input sequence only (offline, less accurate)
            - 'mmseqs2_uniref': Use local MMseqs2 with UniRef30 database

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
        "--msa-mode", msa_mode,
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


def find_input_files(input_folder: str, msa_mode: str) -> List[str]:
    """
    Find input files based on MSA mode.

    Args:
        input_folder: Folder containing input files
        msa_mode: MSA generation mode

    Returns:
        List of input file paths
    """
    if msa_mode == "local":
        # Local mode uses pre-computed A3M files
        a3m_files = sorted(glob.glob(os.path.join(input_folder, "*.a3m")))
        if a3m_files:
            return a3m_files
        # Also check subdirectories (colabfold_search output structure)
        a3m_files = sorted(glob.glob(os.path.join(input_folder, "*", "*.a3m")))
        if a3m_files:
            return a3m_files

    # Default: FASTA files
    return sorted(glob.glob(os.path.join(input_folder, "*.fasta")))


def process_all_fastas(input_folder: str, pdbs_folder: str, num_models: int = 5,
                       use_gpu: bool = True, amber_relax: bool = False,
                       msa_mode: str = "mmseqs2_uniref_env") -> Tuple[int, int, int]:
    """
    Process all FASTA/A3M files in a folder.

    Args:
        input_folder: Folder containing FASTA or A3M files
        pdbs_folder: Output folder for PDBs
        num_models: Number of models per prediction
        use_gpu: Use GPU acceleration
        amber_relax: Apply AMBER relaxation
        msa_mode: MSA generation mode

    Returns:
        Tuple of (completed, failed, skipped)
    """
    # Find input files based on mode
    input_files = find_input_files(input_folder, msa_mode)

    if not input_files:
        file_type = "A3M" if msa_mode == "local" else "FASTA"
        print(f"   No {file_type} files found in {input_folder}", flush=True)
        return 0, 0, 0

    file_type = "A3M" if msa_mode == "local" else "FASTA"
    print(f"   Found {len(input_files)} {file_type} file(s)", flush=True)

    completed = 0
    failed = 0
    skipped = 0

    # Create temporary output folder for ColabFold
    temp_output = os.path.join(pdbs_folder, "_colabfold_output")
    os.makedirs(temp_output, exist_ok=True)

    # Determine effective MSA mode for colabfold_batch
    # When using local A3M files, colabfold_batch doesn't need MSA mode flag
    effective_msa_mode = msa_mode if msa_mode != "local" else "mmseqs2_uniref_env"

    for i, input_path in enumerate(input_files, 1):
        input_name = Path(input_path).stem
        print(f"\n   [{i}/{len(input_files)}] Processing {input_name}...", flush=True)

        # Check if already processed
        status = get_prediction_status(input_name, pdbs_folder, num_models)
        if status == 'completed':
            print(f"      Skipping (already completed)", flush=True)
            skipped += 1
            continue

        # Run prediction
        success, message = run_colabfold(
            input_path,
            temp_output,
            num_models,
            use_gpu,
            amber_relax,
            effective_msa_mode
        )

        if success:
            # Copy PDBs to output folder
            copied = copy_pdbs_to_output(temp_output, pdbs_folder, input_name)
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
    parser.add_argument(
        "--msa-mode", type=str, default="mmseqs2_uniref_env",
        choices=["mmseqs2_uniref_env", "single_sequence", "mmseqs2_uniref", "local"],
        help="MSA generation mode: mmseqs2_uniref_env (default, requires internet), "
             "single_sequence (offline, no MSA), mmseqs2_uniref (local server), "
             "local (use pre-computed A3M files from run_msa_search.py)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_type = "A3M (pre-computed MSA)" if args.msa_mode == "local" else "FASTA"

    print(f"\n{'='*60}", flush=True)
    print(f"ColabFold Batch Predictions", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"   Input:    {args.fastas_folder} ({input_type})", flush=True)
    print(f"   Output:   {args.pdbs_folder}", flush=True)
    print(f"   Models:   {args.num_models}", flush=True)
    print(f"   MSA Mode: {args.msa_mode}", flush=True)
    print(f"   Docker:   {is_inside_docker()}", flush=True)
    print(f"   GPU:      {not args.cpu}", flush=True)

    if args.msa_mode == "single_sequence":
        print(f"\n   WARNING: Using single_sequence mode (no MSA).", flush=True)
        print(f"            Predictions may be less accurate.", flush=True)
    elif args.msa_mode == "local":
        print(f"\n   INFO: Using pre-computed A3M files (local mode).", flush=True)

    if not os.path.exists(args.fastas_folder):
        folder_type = "A3M" if args.msa_mode == "local" else "FASTA"
        print(f"\n   ERROR: {folder_type} folder not found: {args.fastas_folder}", flush=True)
        sys.exit(1)

    os.makedirs(args.pdbs_folder, exist_ok=True)

    completed, failed, skipped = process_all_fastas(
        args.fastas_folder,
        args.pdbs_folder,
        args.num_models,
        use_gpu=not args.cpu,
        amber_relax=args.amber,
        msa_mode=args.msa_mode
    )

    print(f"\n{'='*60}", flush=True)
    print(f"Summary: {completed} completed, {failed} failed, {skipped} skipped", flush=True)
    print(f"{'='*60}", flush=True)

    # Exit with error if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
