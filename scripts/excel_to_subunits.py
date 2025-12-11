#!/usr/bin/env python3
"""
Convert an Excel file with protein sequences to CombFold subunits.json format.

Expected Excel format:
- Complex_ID: Protein/complex name
- Chain_A, Chain_B, Chain_C, ...: Sequences for each chain

The script automatically detects:
- Homo-oligomers: identical sequences are grouped into one subunit with multiple chains
- Hetero-oligomers: different sequences become separate subunits

Large sequences can be automatically split into domains using --max-af-size.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

# Import splitting functionality
from split_large_subunits import split_subunits_for_af_size, needs_splitting


def sanitize_name(name: str) -> str:
    """Convert a name to a valid subunit identifier (alphanumeric + underscores)."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)


def row_to_subunits(complex_id: str, sequences: Dict[str, str]) -> dict:
    """
    Convert a single row's data to subunits.json format.

    This function is used by batch_runner.py for per-job subunits.json generation.

    Args:
        complex_id: The Complex_ID (will be sanitized)
        sequences: Dict mapping chain letters to sequences {'A': 'MKD...', 'B': 'MVL...'}

    Returns:
        Dictionary in subunits.json format
    """
    complex_id = sanitize_name(complex_id)

    # Normalize sequences to uppercase
    chains_data = {k: v.strip().upper() for k, v in sequences.items() if v and v.strip()}

    if not chains_data:
        raise ValueError(f"No valid sequences provided for {complex_id}")

    # Group chains by unique sequences (for homo-oligomer detection)
    seq_to_chains: Dict[str, List[str]] = {}
    for chain_letter, seq in chains_data.items():
        if seq not in seq_to_chains:
            seq_to_chains[seq] = []
        seq_to_chains[seq].append(chain_letter)

    # Create subunits
    subunits = {}

    if len(seq_to_chains) == 1:
        # Homo-oligomer: all chains have the same sequence
        seq = list(seq_to_chains.keys())[0]
        chain_names = sorted(seq_to_chains[seq])

        subunit_name = f"{complex_id}"
        subunits[subunit_name] = {
            "name": subunit_name,
            "chain_names": chain_names,
            "start_res": 1,
            "sequence": seq
        }
    else:
        # Hetero-oligomer: different sequences
        for i, (seq, chain_names) in enumerate(seq_to_chains.items()):
            chain_names = sorted(chain_names)

            # Name subunit by first chain letter
            if len(seq_to_chains) <= 26:
                subunit_name = f"{complex_id}_{chain_names[0]}"
            else:
                subunit_name = f"{complex_id}_sub{i}"

            subunits[subunit_name] = {
                "name": subunit_name,
                "chain_names": chain_names,
                "start_res": 1,
                "sequence": seq
            }

    return subunits


def sequences_list_to_dict(sequences: List[str]) -> Dict[str, str]:
    """
    Convert a list of sequences to a dict with chain letters.

    Args:
        sequences: List of sequences in order [seq_A, seq_B, seq_C, ...]

    Returns:
        Dict mapping chain letters to sequences {'A': seq_A, 'B': seq_B, ...}
    """
    return {chr(65 + i): seq for i, seq in enumerate(sequences) if seq and seq.strip()}


def excel_to_subunits(excel_path: str, output_path: str = None, split: bool = False,
                      max_af_size: int = None) -> dict:
    """
    Convert Excel file to subunits.json format.

    Args:
        excel_path: Path to the Excel file
        output_path: Optional output path for the JSON file (or directory if split=True)
        split: If True, create separate subunits.json per complex in output_path directory
        max_af_size: If set, split large sequences into domains (max combined size for AFM)

    Returns:
        Dictionary mapping complex_id to subunits dict (if split=True)
        or single merged subunits dict (if split=False, only valid for single complex)
    """
    df = pd.read_excel(excel_path)

    # Find chain columns (columns starting with "Chain_")
    chain_cols = [col for col in df.columns if col.startswith("Chain_")]

    if not chain_cols:
        raise ValueError("No chain columns found. Expected columns like 'Chain_A', 'Chain_B', etc.")

    if "Complex_ID" not in df.columns:
        raise ValueError("'Complex_ID' column not found in Excel file.")

    all_complexes = {}  # complex_id -> subunits dict

    for idx, row in df.iterrows():
        complex_id = sanitize_name(str(row["Complex_ID"]))

        # Collect all chains and their sequences (skip empty/NaN)
        chains_data = {}
        for col in chain_cols:
            seq = row[col]
            if pd.notna(seq) and str(seq).strip():
                chain_letter = col.replace("Chain_", "")
                chains_data[chain_letter] = str(seq).strip().upper()

        if not chains_data:
            print(f"Warning: No sequences found for {complex_id}, skipping.")
            continue

        # Use the shared row_to_subunits function
        subunits = row_to_subunits(complex_id, chains_data)

        # Split large sequences into domains if max_af_size is set
        if max_af_size and needs_splitting(subunits, max_af_size):
            print(f"  {complex_id}: Splitting large sequences (max_af_size={max_af_size})...")
            subunits = split_subunits_for_af_size(subunits, max_af_size, verbose=True)

        all_complexes[complex_id] = subunits

    # Handle output
    if output_path:
        if split:
            # Create separate files per complex in output directory
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            for complex_id, subunits in all_complexes.items():
                complex_dir = output_dir / complex_id
                complex_dir.mkdir(parents=True, exist_ok=True)
                out_file = complex_dir / "subunits.json"
                with open(out_file, "w") as f:
                    json.dump(subunits, f, indent=2)
                print(f"Saved: {out_file}")

            print(f"\nTotal complexes: {len(all_complexes)}")
        else:
            # Merge all into single file (only works for single complex)
            if len(all_complexes) > 1:
                print("WARNING: Multiple complexes found. Use --split to create separate files.")
                print("         Merging will cause chain conflicts in CombFold!")

            merged = {}
            for subunits in all_complexes.values():
                merged.update(subunits)

            with open(output_path, "w") as f:
                json.dump(merged, f, indent=2)
            print(f"Saved subunits.json to: {output_path}")
            print(f"Total subunits: {len(merged)}")

            return merged

    return all_complexes


def main():
    parser = argparse.ArgumentParser(
        description="Convert Excel file with sequences to CombFold subunits.json format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sequences.xlsx
      Convert sequences.xlsx to subunits.json (single complex only)

  %(prog)s sequences.xlsx --split -o output_dir/
      Create separate subunits.json per complex in output_dir/<complex_id>/

  %(prog)s sequences.xlsx --split -o output_dir/ --max-af-size 1800
      Same as above, but split large sequences into domains

  %(prog)s sequences.xlsx -o output/subunits.json
      Convert and save to specific output path (single complex only)

Expected Excel format:
  - Complex_ID column: Protein/complex name
  - Chain_A, Chain_B, Chain_C, ... columns: Amino acid sequences

The script automatically detects homo-oligomers (identical sequences grouped
into one subunit) and hetero-oligomers (different sequences as separate subunits).

IMPORTANT: For multiple complexes, use --split to create separate directories.
CombFold requires one subunits.json per complex (chains cannot overlap).

Large sequences: Use --max-af-size to automatically split sequences that exceed
the AFM prediction limit. Sequences longer than max_af_size/2 will be split
into domains.
"""
    )
    parser.add_argument(
        "excel_file",
        help="Path to the Excel file with Complex_ID and Chain_* columns"
    )
    parser.add_argument(
        "-o", "--output",
        default="subunits.json",
        help="Output path: file path (default) or directory (with --split)"
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Create separate subunits.json per complex in output/<complex_id>/ directories"
    )
    parser.add_argument(
        "--max-af-size", type=int, default=None,
        help="Split large sequences into domains (max combined size for AFM, e.g., 1800)"
    )

    args = parser.parse_args()

    if not Path(args.excel_file).exists():
        print(f"Error: Excel file not found: {args.excel_file}")
        sys.exit(1)

    try:
        result = excel_to_subunits(args.excel_file, args.output, split=args.split,
                                   max_af_size=args.max_af_size)

        # Print summary
        print("\n--- Summary ---")
        if args.split:
            for complex_id, subunits in result.items():
                print(f"\n  {complex_id}:")
                for name, info in subunits.items():
                    chains = ", ".join(info["chain_names"])
                    seq_len = len(info["sequence"])
                    print(f"    {name}: chains=[{chains}], seq_length={seq_len}")
        else:
            for name, info in result.items():
                chains = ", ".join(info["chain_names"])
                seq_len = len(info["sequence"])
                print(f"  {name}: chains=[{chains}], seq_length={seq_len}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
