#!/bin/bash
# Download ColabFold model weights
# Run this once after building the container

set -e

echo "=========================================="
echo "Downloading ColabFold/AlphaFold2 weights"
echo "=========================================="
echo ""
echo "This will download approximately 5GB of model weights."
echo "Weights will be cached in /cache for future use."
echo ""

# Activate colabfold environment and download
source /opt/conda/etc/profile.d/conda.sh
conda activate colabfold

python -m colabfold.download

echo ""
echo "=========================================="
echo "Download complete!"
echo "=========================================="
