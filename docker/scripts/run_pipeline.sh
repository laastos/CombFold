#!/bin/bash
# Full CombFold pipeline: generate FASTAs, run AFM predictions, assemble
#
# Usage: run_pipeline.sh <subunits.json> <output_dir> [--max-af-size SIZE] [--num-models N]
#
# Example:
#   run_pipeline.sh /data/input/subunits.json /data/output/my_complex

set -e

# Parse arguments
SUBUNITS_JSON="$1"
OUTPUT_DIR="$2"
MAX_AF_SIZE="${3:-1800}"
NUM_MODELS="${4:-5}"

if [ -z "$SUBUNITS_JSON" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: run_pipeline.sh <subunits.json> <output_dir> [max_af_size] [num_models]"
    echo ""
    echo "Arguments:"
    echo "  subunits.json  - Path to subunits definition file"
    echo "  output_dir     - Output directory for all results"
    echo "  max_af_size    - Maximum residues per AFM prediction (default: 1800)"
    echo "  num_models     - Number of AFM models per prediction (default: 5)"
    exit 1
fi

echo "=========================================="
echo "CombFold Full Pipeline"
echo "=========================================="
echo "Subunits: $SUBUNITS_JSON"
echo "Output:   $OUTPUT_DIR"
echo "Max AF size: $MAX_AF_SIZE"
echo "Num models:  $NUM_MODELS"
echo "=========================================="
echo ""

# Create output directories
mkdir -p "$OUTPUT_DIR/fasta_pairs"
mkdir -p "$OUTPUT_DIR/fasta_groups"
mkdir -p "$OUTPUT_DIR/afm_predictions"
mkdir -p "$OUTPUT_DIR/assembly"

# Activate colabfold environment
source /opt/conda/etc/profile.d/conda.sh
conda activate colabfold

# Stage 2: Generate pair FASTAs
echo ""
echo "=== Stage 2: Generating pair FASTA files ==="
python3 /app/scripts/prepare_fastas.py \
    "$SUBUNITS_JSON" \
    --stage pairs \
    --output-fasta-folder "$OUTPUT_DIR/fasta_pairs" \
    --max-af-size "$MAX_AF_SIZE"

# Count FASTA files
FASTA_COUNT=$(ls -1 "$OUTPUT_DIR/fasta_pairs"/*.fasta 2>/dev/null | wc -l)
echo "Generated $FASTA_COUNT FASTA files for pairs"

# Stage 2: Run AFM predictions on pairs
echo ""
echo "=== Stage 2: Running AlphaFold-Multimer on pairs ==="
for fasta in "$OUTPUT_DIR/fasta_pairs"/*.fasta; do
    if [ -f "$fasta" ]; then
        basename=$(basename "$fasta" .fasta)
        echo "Predicting: $basename"
        colabfold_batch "$fasta" "$OUTPUT_DIR/afm_predictions" \
            --num-models "$NUM_MODELS" \
            --amber \
            --use-gpu-relax
    fi
done

# Stage 3 (optional): Generate group FASTAs based on pair results
echo ""
echo "=== Stage 3: Generating group FASTA files ==="
python3 /app/scripts/prepare_fastas.py \
    "$SUBUNITS_JSON" \
    --stage groups \
    --output-fasta-folder "$OUTPUT_DIR/fasta_groups" \
    --max-af-size "$MAX_AF_SIZE" \
    --input-pairs-results "$OUTPUT_DIR/afm_predictions" || echo "No groups generated (may be expected for small complexes)"

# Run AFM on groups if any were generated
GROUP_COUNT=$(ls -1 "$OUTPUT_DIR/fasta_groups"/*.fasta 2>/dev/null | wc -l)
if [ "$GROUP_COUNT" -gt 0 ]; then
    echo ""
    echo "=== Stage 3: Running AlphaFold-Multimer on groups ==="
    for fasta in "$OUTPUT_DIR/fasta_groups"/*.fasta; do
        if [ -f "$fasta" ]; then
            basename=$(basename "$fasta" .fasta)
            echo "Predicting: $basename"
            colabfold_batch "$fasta" "$OUTPUT_DIR/afm_predictions" \
                --num-models "$NUM_MODELS" \
                --amber \
                --use-gpu-relax
        fi
    done
fi

# Stage 4: Run CombFold assembly
echo ""
echo "=== Stage 4: Running CombFold Assembly ==="
python3 /app/scripts/run_on_pdbs.py \
    "$SUBUNITS_JSON" \
    "$OUTPUT_DIR/afm_predictions" \
    "$OUTPUT_DIR/assembly"

echo ""
echo "=========================================="
echo "Pipeline Complete!"
echo "=========================================="
echo ""
echo "Results:"
echo "  AFM Predictions: $OUTPUT_DIR/afm_predictions/"
echo "  Assembled Models: $OUTPUT_DIR/assembly/assembled_results/"
echo ""
echo "Best model: $OUTPUT_DIR/assembly/assembled_results/output_clustered_0.pdb"
