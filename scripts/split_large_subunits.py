#!/usr/bin/env python3
"""
Split large protein sequences into domains for CombFold processing.

CombFold requires pairwise AlphaFold-Multimer predictions, which have a size limit
(typically 1800 residues combined). For large proteins, this script splits sequences
into smaller domains that can be predicted within the size limit.

The script can be used:
1. Standalone: python3 split_large_subunits.py input.json -o output.json
2. As a module: from split_large_subunits import split_subunits_for_af_size

Domain splitting strategy:
- Calculates the maximum domain size based on max_af_size / 2
- Splits sequences evenly into domains of approximately equal size
- Preserves chain_names (stoichiometry) for each domain
- Updates start_res to maintain correct residue numbering
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def calculate_domain_size(sequence_length: int, max_af_size: int) -> Tuple[int, int]:
    """
    Calculate optimal domain size and number of domains.

    For pairwise predictions, max combined size is max_af_size.
    So each domain should be at most max_af_size / 2.

    Args:
        sequence_length: Length of the sequence to split
        max_af_size: Maximum combined size for AFM predictions

    Returns:
        Tuple of (domain_size, num_domains)
    """
    max_domain_size = max_af_size // 2

    if sequence_length <= max_domain_size:
        return sequence_length, 1

    # Calculate minimum number of domains needed
    num_domains = math.ceil(sequence_length / max_domain_size)

    # Calculate even domain size (may be slightly smaller than max)
    domain_size = math.ceil(sequence_length / num_domains)

    return domain_size, num_domains


def split_sequence(sequence: str, domain_size: int, overlap: int = 0) -> List[Tuple[int, str]]:
    """
    Split a sequence into domains of specified size.

    Args:
        sequence: The amino acid sequence
        domain_size: Target size for each domain
        overlap: Number of overlapping residues between domains (default: 0)

    Returns:
        List of (start_res, domain_sequence) tuples (1-indexed start)
    """
    domains = []
    seq_len = len(sequence)

    if seq_len <= domain_size:
        return [(1, sequence)]

    pos = 0
    domain_num = 0

    while pos < seq_len:
        # Calculate end position for this domain
        end = min(pos + domain_size, seq_len)

        # Extract domain sequence
        domain_seq = sequence[pos:end]

        # Start residue is 1-indexed
        start_res = pos + 1

        domains.append((start_res, domain_seq))

        # Move to next domain (with potential overlap)
        pos = end - overlap
        domain_num += 1

        # Safety check to prevent infinite loop
        if overlap >= domain_size:
            break

    return domains


def split_subunit(subunit: dict, max_af_size: int, overlap: int = 0) -> List[dict]:
    """
    Split a single subunit into multiple domain subunits if needed.

    Args:
        subunit: Subunit dictionary with name, chain_names, start_res, sequence
        max_af_size: Maximum combined size for AFM predictions

    Returns:
        List of subunit dictionaries (1 if no split needed, multiple if split)
    """
    sequence = subunit["sequence"]
    seq_len = len(sequence)
    original_start = subunit.get("start_res", 1)

    # Calculate domain size
    domain_size, num_domains = calculate_domain_size(seq_len, max_af_size)

    if num_domains == 1:
        # No split needed
        return [subunit]

    # Split the sequence
    domains = split_sequence(sequence, domain_size, overlap)

    # Create new subunits for each domain
    split_subunits = []
    base_name = subunit["name"]

    for i, (rel_start, domain_seq) in enumerate(domains):
        # Calculate absolute start residue
        abs_start = original_start + rel_start - 1

        domain_subunit = {
            "name": f"{base_name}_d{i+1}",
            "chain_names": subunit["chain_names"].copy(),
            "start_res": abs_start,
            "sequence": domain_seq
        }
        split_subunits.append(domain_subunit)

    return split_subunits


def split_subunits_for_af_size(subunits: dict, max_af_size: int = 1800,
                                overlap: int = 0, verbose: bool = True) -> dict:
    """
    Split all subunits that exceed the maximum AFM prediction size.

    This is the main function to call from other scripts.

    Args:
        subunits: Dictionary of subunits (name -> subunit dict)
        max_af_size: Maximum combined size for AFM predictions (default: 1800)
        overlap: Number of overlapping residues between domains (default: 0)
        verbose: Print splitting information

    Returns:
        New dictionary with split subunits
    """
    result = {}
    max_domain_size = max_af_size // 2

    for name, subunit in subunits.items():
        seq_len = len(subunit["sequence"])

        if seq_len > max_domain_size:
            if verbose:
                domain_size, num_domains = calculate_domain_size(seq_len, max_af_size)
                print(f"  Splitting {name}: {seq_len}aa -> {num_domains} domains of ~{domain_size}aa")

            split_subs = split_subunit(subunit, max_af_size, overlap)
            for sub in split_subs:
                result[sub["name"]] = sub
        else:
            result[name] = subunit

    return result


def needs_splitting(subunits: dict, max_af_size: int = 1800) -> bool:
    """
    Check if any subunit needs splitting.

    Args:
        subunits: Dictionary of subunits
        max_af_size: Maximum combined size for AFM predictions

    Returns:
        True if any subunit exceeds max_af_size / 2
    """
    max_domain_size = max_af_size // 2

    for subunit in subunits.values():
        if len(subunit["sequence"]) > max_domain_size:
            return True

    return False


def get_splitting_summary(subunits: dict, max_af_size: int = 1800) -> Dict[str, dict]:
    """
    Get a summary of what would be split without actually splitting.

    Args:
        subunits: Dictionary of subunits
        max_af_size: Maximum combined size for AFM predictions

    Returns:
        Dictionary mapping subunit names to split info
    """
    max_domain_size = max_af_size // 2
    summary = {}

    for name, subunit in subunits.items():
        seq_len = len(subunit["sequence"])

        if seq_len > max_domain_size:
            domain_size, num_domains = calculate_domain_size(seq_len, max_af_size)
            summary[name] = {
                "original_length": seq_len,
                "num_domains": num_domains,
                "domain_size": domain_size,
                "exceeds_by": seq_len - max_domain_size
            }

    return summary


def process_subunits_file(input_path: str, output_path: str = None,
                          max_af_size: int = 1800, overlap: int = 0) -> dict:
    """
    Process a subunits.json file and split large sequences.

    Args:
        input_path: Path to input subunits.json
        output_path: Path to output file (optional, prints to stdout if None)
        max_af_size: Maximum combined size for AFM predictions
        overlap: Residue overlap between domains

    Returns:
        Processed subunits dictionary
    """
    # Load input
    with open(input_path, 'r') as f:
        subunits = json.load(f)

    print(f"Loaded {len(subunits)} subunit(s) from {input_path}")

    # Check if splitting is needed
    summary = get_splitting_summary(subunits, max_af_size)

    if not summary:
        print(f"No subunits exceed max domain size ({max_af_size // 2}aa). No splitting needed.")
        result = subunits
    else:
        print(f"\nSubunits to split (max domain size: {max_af_size // 2}aa):")
        for name, info in summary.items():
            print(f"  {name}: {info['original_length']}aa -> {info['num_domains']} domains")

        # Perform splitting
        print("\nSplitting...")
        result = split_subunits_for_af_size(subunits, max_af_size, overlap)
        print(f"\nResult: {len(result)} subunit(s)")

    # Output
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to: {output_path}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Split large protein sequences into domains for CombFold",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s subunits.json -o subunits_split.json
      Split large sequences and save to new file

  %(prog)s subunits.json --max-af-size 1500
      Use smaller max size (for GPUs with less memory)

  %(prog)s subunits.json --check
      Only check which subunits would be split (no output)

  %(prog)s subunits.json --overlap 50
      Add 50 residue overlap between domains

Domain splitting strategy:
  - Max domain size = max_af_size / 2 (for pairwise predictions)
  - Sequences are split into approximately equal-sized domains
  - Each domain inherits the chain_names (stoichiometry) from parent
  - start_res is updated to maintain correct residue numbering
  - Domain names follow pattern: {original_name}_d1, _d2, etc.
"""
    )
    parser.add_argument(
        "input_file",
        help="Input subunits.json file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: print to stdout)"
    )
    parser.add_argument(
        "--max-af-size", type=int, default=1800,
        help="Maximum combined size for AFM predictions (default: 1800)"
    )
    parser.add_argument(
        "--overlap", type=int, default=0,
        help="Residue overlap between domains (default: 0)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Only check what would be split, don't generate output"
    )
    parser.add_argument(
        "--in-place", action="store_true",
        help="Modify input file in place"
    )

    args = parser.parse_args()

    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    if args.check:
        # Just show what would be split
        with open(args.input_file, 'r') as f:
            subunits = json.load(f)

        summary = get_splitting_summary(subunits, args.max_af_size)

        if not summary:
            print(f"No subunits need splitting (max domain size: {args.max_af_size // 2}aa)")
        else:
            print(f"Subunits that would be split (max domain size: {args.max_af_size // 2}aa):\n")
            for name, info in summary.items():
                print(f"  {name}:")
                print(f"    Original length: {info['original_length']}aa")
                print(f"    Exceeds by: {info['exceeds_by']}aa")
                print(f"    Would split into: {info['num_domains']} domains of ~{info['domain_size']}aa")
                print()
        return

    # Determine output path
    output_path = args.output
    if args.in_place:
        output_path = args.input_file

    # Process the file
    result = process_subunits_file(
        args.input_file,
        output_path,
        args.max_af_size,
        args.overlap
    )

    # If no output file specified, print to stdout
    if not output_path:
        print("\n--- Result (JSON) ---")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
