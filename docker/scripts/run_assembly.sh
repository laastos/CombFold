#!/bin/bash
# Run CombFold assembly on pre-computed AFM predictions
#
# Usage: run_assembly.sh <subunits.json> <pdbs_dir> <output_dir> [crosslinks.txt]
#
# Example:
#   run_assembly.sh /data/input/subunits.json /data/pdbs /data/output
#   run_assembly.sh /data/input/subunits.json /data/pdbs /data/output /data/input/crosslinks.txt

set -e

SUBUNITS_JSON="$1"
PDBS_DIR="$2"
OUTPUT_DIR="$3"
CROSSLINKS="$4"

if [ -z "$SUBUNITS_JSON" ] || [ -z "$PDBS_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: run_assembly.sh <subunits.json> <pdbs_dir> <output_dir> [crosslinks.txt]"
    echo ""
    echo "Arguments:"
    echo "  subunits.json  - Path to subunits definition file"
    echo "  pdbs_dir       - Directory containing AFM PDB predictions"
    echo "  output_dir     - Output directory for assembly results"
    echo "  crosslinks.txt - Optional crosslink constraints file"
    exit 1
fi

echo "=========================================="
echo "CombFold Assembly"
echo "=========================================="
echo "Subunits: $SUBUNITS_JSON"
echo "PDBs:     $PDBS_DIR"
echo "Output:   $OUTPUT_DIR"
if [ -n "$CROSSLINKS" ]; then
    echo "Crosslinks: $CROSSLINKS"
fi
echo "=========================================="
echo ""

# Count PDB files
PDB_COUNT=$(ls -1 "$PDBS_DIR"/*.pdb 2>/dev/null | wc -l)
echo "Found $PDB_COUNT PDB files"
echo ""

# Run assembly
if [ -n "$CROSSLINKS" ]; then
    python3 /app/scripts/run_on_pdbs.py \
        "$SUBUNITS_JSON" \
        "$PDBS_DIR" \
        "$OUTPUT_DIR" \
        "$CROSSLINKS"
else
    python3 /app/scripts/run_on_pdbs.py \
        "$SUBUNITS_JSON" \
        "$PDBS_DIR" \
        "$OUTPUT_DIR"
fi

echo ""
echo "=========================================="
echo "Assembly complete!"
echo "=========================================="
echo ""
echo "Results in: $OUTPUT_DIR/assembled_results/"
echo ""

# Show confidence scores if available
if [ -f "$OUTPUT_DIR/assembled_results/confidence.txt" ]; then
    echo "Confidence scores:"
    cat "$OUTPUT_DIR/assembled_results/confidence.txt"
fi
