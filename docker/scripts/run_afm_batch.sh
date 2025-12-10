#!/bin/bash
# Run ColabFold batch predictions on FASTA files
#
# Usage: run_afm_batch.sh <fasta_dir> <output_dir> [--num-models N]
#
# Example:
#   run_afm_batch.sh /data/fastas /data/predictions

set -e

FASTA_DIR="$1"
OUTPUT_DIR="$2"
NUM_MODELS="${3:-5}"

if [ -z "$FASTA_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: run_afm_batch.sh <fasta_dir> <output_dir> [num_models]"
    echo ""
    echo "Arguments:"
    echo "  fasta_dir   - Directory containing FASTA files"
    echo "  output_dir  - Output directory for predictions"
    echo "  num_models  - Number of models per prediction (default: 5)"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Activate colabfold environment
source /opt/conda/etc/profile.d/conda.sh
conda activate colabfold

echo "=========================================="
echo "ColabFold Batch Predictions"
echo "=========================================="
echo "Input:  $FASTA_DIR"
echo "Output: $OUTPUT_DIR"
echo "Models: $NUM_MODELS"
echo "=========================================="
echo ""

# Count FASTA files
FASTA_COUNT=$(ls -1 "$FASTA_DIR"/*.fasta 2>/dev/null | wc -l)
if [ "$FASTA_COUNT" -eq 0 ]; then
    echo "No FASTA files found in $FASTA_DIR"
    exit 1
fi

echo "Found $FASTA_COUNT FASTA files to process"
echo ""

# Process each FASTA file
CURRENT=0
for fasta in "$FASTA_DIR"/*.fasta; do
    if [ -f "$fasta" ]; then
        CURRENT=$((CURRENT + 1))
        basename=$(basename "$fasta" .fasta)
        echo "[$CURRENT/$FASTA_COUNT] Predicting: $basename"

        colabfold_batch "$fasta" "$OUTPUT_DIR" \
            --num-models "$NUM_MODELS" \
            --amber \
            --use-gpu-relax

        echo ""
    fi
done

echo "=========================================="
echo "Batch predictions complete!"
echo "Results in: $OUTPUT_DIR"
echo "=========================================="
