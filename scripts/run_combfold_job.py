#!/usr/bin/env python3
"""
Run the complete CombFold pipeline for a single job on a specific GPU.

This script is called by batch_runner.py to execute the full pipeline:
1. Create subunits.json from sequences
2. Generate FASTA files for pairwise predictions
3. Run ColabFold predictions
4. Run combinatorial assembly

Usage:
    python3 run_combfold_job.py --gpu 0 --job_id Complex_001 --sequences SEQ1 SEQ2
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add the scripts directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from excel_to_subunits import row_to_subunits, sequences_list_to_dict
from split_large_subunits import split_subunits_for_af_size, needs_splitting


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run CombFold pipeline for a single job"
    )
    parser.add_argument(
        "--gpu", type=int, required=True,
        help="GPU device ID to use"
    )
    parser.add_argument(
        "--job_id", type=str, required=True,
        help="Complex_ID (job identifier)"
    )
    parser.add_argument(
        "--sequences", type=str, nargs="+", required=True,
        help="Amino acid sequences for each chain (Chain_A, Chain_B, ...)"
    )
    parser.add_argument(
        "--output_dir", type=str, default="results",
        help="Base output directory (default: results)"
    )
    parser.add_argument(
        "--skip_afm", action="store_true",
        help="Skip AlphaFold-Multimer predictions (use existing PDBs)"
    )
    parser.add_argument(
        "--max_af_size", type=int, default=1800,
        help="Max combined sequence length for AFM (default: 1800)"
    )
    parser.add_argument(
        "--num_models", type=int, default=5,
        help="Number of AFM models to predict (default: 5)"
    )
    parser.add_argument(
        "--msa_mode", type=str, default="mmseqs2_uniref_env",
        help="MSA generation mode: mmseqs2_uniref_env (default), single_sequence (offline), mmseqs2_uniref (local db)"
    )
    return parser.parse_args()


def create_subunits_json(job_id: str, sequences: List[str], output_path: str,
                         max_af_size: int = 1800) -> dict:
    """
    Create subunits.json from sequences, splitting large sequences if needed.

    Args:
        job_id: Complex ID
        sequences: List of sequences [seq_A, seq_B, ...]
        output_path: Path to save subunits.json
        max_af_size: Max combined sequence length for AFM (sequences > max_af_size/2 will be split)

    Returns:
        Subunits dictionary
    """
    # Convert list to dict with chain letters
    seq_dict = sequences_list_to_dict(sequences)

    # Generate subunits
    subunits = row_to_subunits(job_id, seq_dict)

    # Split large sequences into domains if needed
    if needs_splitting(subunits, max_af_size):
        print(f"   Splitting large sequences (max_af_size={max_af_size})...", flush=True)
        subunits = split_subunits_for_af_size(subunits, max_af_size, verbose=True)

    # Save to file
    with open(output_path, "w") as f:
        json.dump(subunits, f, indent=2)

    return subunits


def run_prepare_fastas(subunits_json: str, fastas_folder: str, max_af_size: int) -> bool:
    """
    Run prepare_fastas.py to generate FASTA files.

    Args:
        subunits_json: Path to subunits.json
        fastas_folder: Output folder for FASTAs
        max_af_size: Max sequence length for AFM

    Returns:
        True if successful
    """
    prepare_fastas_script = os.path.join(SCRIPT_DIR, "prepare_fastas.py")

    cmd = [
        sys.executable, "-u", prepare_fastas_script,
        subunits_json,
        "--stage", "pairs",
        "--output-fasta-folder", fastas_folder,
        "--max-af-size", str(max_af_size)
    ]

    print(f"   Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=False)

    return result.returncode == 0


def run_afm_predictions(fastas_folder: str, pdbs_folder: str, num_models: int = 5,
                        msa_mode: str = "mmseqs2_uniref_env") -> bool:
    """
    Run ColabFold predictions on all FASTA files.

    Args:
        fastas_folder: Folder containing FASTA files
        pdbs_folder: Output folder for PDB predictions
        num_models: Number of models per prediction
        msa_mode: MSA generation mode

    Returns:
        True if successful
    """
    run_afm_script = os.path.join(SCRIPT_DIR, "run_afm_predictions.py")

    cmd = [
        sys.executable, "-u", run_afm_script,
        fastas_folder,
        pdbs_folder,
        "--num-models", str(num_models),
        "--msa-mode", msa_mode
    ]

    print(f"   Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=False)

    return result.returncode == 0


def run_assembly(subunits_json: str, pdbs_folder: str, output_folder: str) -> bool:
    """
    Run combinatorial assembly.

    Args:
        subunits_json: Path to subunits.json
        pdbs_folder: Folder containing PDB predictions
        output_folder: Output folder for assembly results

    Returns:
        True if successful
    """
    run_on_pdbs_script = os.path.join(SCRIPT_DIR, "run_on_pdbs.py")

    cmd = [
        sys.executable, "-u", run_on_pdbs_script,
        subunits_json,
        pdbs_folder,
        output_folder
    ]

    print(f"   Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=False)

    return result.returncode == 0


def run_pipeline(job_id: str, sequences: List[str], output_dir: str,
                 gpu_id: int, skip_afm: bool = False,
                 max_af_size: int = 1800, num_models: int = 5,
                 msa_mode: str = "mmseqs2_uniref_env") -> bool:
    """
    Run the complete CombFold pipeline for a single job.

    Args:
        job_id: Complex ID
        sequences: List of sequences
        output_dir: Base output directory
        gpu_id: GPU device ID
        skip_afm: Skip AFM predictions
        max_af_size: Max sequence length for AFM
        num_models: Number of AFM models
        msa_mode: MSA generation mode

    Returns:
        True if successful
    """
    # Set GPU environment
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    # Create job directory structure
    job_dir = os.path.join(output_dir, job_id)
    subunits_json_path = os.path.join(job_dir, "subunits.json")
    fastas_folder = os.path.join(job_dir, "fastas")
    pdbs_folder = os.path.join(job_dir, "pdbs")
    assembly_output = os.path.join(job_dir, "output")

    os.makedirs(job_dir, exist_ok=True)

    print(f"\n{'='*60}", flush=True)
    print(f"CombFold Pipeline: {job_id}", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"   GPU: {gpu_id}", flush=True)
    print(f"   Sequences: {len(sequences)}", flush=True)
    print(f"   Output: {job_dir}", flush=True)

    start_time = time.time()

    # Stage 1: Create subunits.json
    print(f"\n[Stage 1] Creating subunits.json...", flush=True)
    if not os.path.exists(subunits_json_path):
        try:
            subunits = create_subunits_json(job_id, sequences, subunits_json_path, max_af_size)
            print(f"   Created {len(subunits)} subunit(s)", flush=True)
            for name, info in subunits.items():
                chains = ", ".join(info["chain_names"])
                seq_len = len(info["sequence"])
                print(f"   - {name}: chains=[{chains}], length={seq_len}", flush=True)
        except Exception as e:
            print(f"   ERROR: Failed to create subunits.json: {e}", flush=True)
            return False
    else:
        print(f"   Using existing subunits.json", flush=True)

    # Stage 2: Generate FASTAs
    print(f"\n[Stage 2] Generating FASTA files...", flush=True)
    if not os.path.exists(fastas_folder) or not os.listdir(fastas_folder):
        if not run_prepare_fastas(subunits_json_path, fastas_folder, max_af_size):
            print(f"   ERROR: Failed to generate FASTAs", flush=True)
            return False
        fasta_count = len([f for f in os.listdir(fastas_folder) if f.endswith('.fasta')])
        print(f"   Generated {fasta_count} FASTA file(s)", flush=True)
    else:
        fasta_count = len([f for f in os.listdir(fastas_folder) if f.endswith('.fasta')])
        print(f"   Using existing {fasta_count} FASTA file(s)", flush=True)

    # Stage 3: AFM Predictions
    if not skip_afm:
        print(f"\n[Stage 3] Running AlphaFold-Multimer predictions...", flush=True)
        os.makedirs(pdbs_folder, exist_ok=True)

        # Check if predictions already exist
        existing_pdbs = len([f for f in os.listdir(pdbs_folder) if f.endswith('.pdb')]) if os.path.exists(pdbs_folder) else 0
        if existing_pdbs > 0:
            print(f"   Found {existing_pdbs} existing PDB(s), checking for completeness...", flush=True)

        if not run_afm_predictions(fastas_folder, pdbs_folder, num_models, msa_mode):
            print(f"   ERROR: Failed to run AFM predictions", flush=True)
            return False

        pdb_count = len([f for f in os.listdir(pdbs_folder) if f.endswith('.pdb')])
        print(f"   Total: {pdb_count} PDB file(s)", flush=True)
    else:
        print(f"\n[Stage 3] Skipping AFM predictions (--skip_afm)", flush=True)
        if not os.path.exists(pdbs_folder):
            print(f"   ERROR: pdbs folder does not exist: {pdbs_folder}", flush=True)
            return False

    # Stage 4: Assembly
    print(f"\n[Stage 4] Running combinatorial assembly...", flush=True)
    if not run_assembly(subunits_json_path, pdbs_folder, assembly_output):
        print(f"   ERROR: Failed to run assembly", flush=True)
        return False

    # Check for results
    assembled_results = os.path.join(assembly_output, "assembled_results")
    if os.path.exists(assembled_results):
        result_pdbs = [f for f in os.listdir(assembled_results) if f.endswith('.pdb')]
        print(f"   Generated {len(result_pdbs)} assembled model(s)", flush=True)
    else:
        print(f"   Warning: No assembled_results folder found", flush=True)

    elapsed = time.time() - start_time
    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        elapsed_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        elapsed_str = f"{minutes}m {seconds}s"
    else:
        elapsed_str = f"{seconds}s"

    print(f"\n{'='*60}", flush=True)
    print(f"Pipeline completed in {elapsed_str}", flush=True)
    print(f"{'='*60}", flush=True)

    return True


def main():
    args = parse_args()

    print(f"\n{'#'*60}", flush=True)
    print(f"# CombFold Job: {args.job_id}", flush=True)
    print(f"# GPU: {args.gpu}", flush=True)
    print(f"# Sequences: {len(args.sequences)}", flush=True)
    print(f"# MSA Mode: {args.msa_mode}", flush=True)
    print(f"{'#'*60}", flush=True)

    if args.msa_mode == "single_sequence":
        print(f"\nWARNING: Using single_sequence mode (no MSA) - predictions may be less accurate", flush=True)

    success = run_pipeline(
        job_id=args.job_id,
        sequences=args.sequences,
        output_dir=args.output_dir,
        gpu_id=args.gpu,
        skip_afm=args.skip_afm,
        max_af_size=args.max_af_size,
        num_models=args.num_models,
        msa_mode=args.msa_mode
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
