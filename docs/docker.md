# Docker Guide

This guide covers running CombFold with LocalColabFold using Docker, providing a complete environment for protein complex structure prediction.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Building the Image](#building-the-image)
- [Running Predictions](#running-predictions)
- [Full Pipeline](#full-pipeline)
- [Volume Management](#volume-management)
- [GPU Configuration](#gpu-configuration)
- [Blackwell GPU Support](#blackwell-gpu-support)
- [Troubleshooting](#troubleshooting)

## Overview

The Docker image combines:

- **CombFold** - Combinatorial assembly algorithm for large protein complexes
- **LocalColabFold** - Local installation of ColabFold for AlphaFold-Multimer predictions
- **NGC JAX 25.01** - NVIDIA NGC container with native Blackwell (CC 12.0) GPU support
- **All dependencies** - Boost, Python packages, optimized CUDA libraries

This provides a complete, reproducible environment for the entire CombFold pipeline with support for the latest NVIDIA GPUs including Blackwell architecture (RTX 50 series, RTX PRO 6000, etc.).

## Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA 12GB VRAM | NVIDIA 24GB+ VRAM (Blackwell supported) |
| RAM | 32 GB | 64 GB |
| Disk | 50 GB | 100+ GB |
| CPU | 4 cores | 8+ cores |

### Supported GPUs

| GPU Architecture | Compute Capability | Status |
|------------------|-------------------|--------|
| Blackwell (RTX 50xx, PRO 6000) | 12.0 | Fully supported via NGC JAX |
| Ada Lovelace (RTX 40xx) | 8.9 | Supported |
| Ampere (RTX 30xx, A100) | 8.0-8.6 | Supported |
| Turing (RTX 20xx) | 7.5 | Supported |

### Software

- Docker 20.10+ or Docker Engine 24+
- NVIDIA Container Toolkit (nvidia-docker2)
- NVIDIA Driver >= 580.x (for Blackwell) or >= 525.60.13 (for older GPUs)

### Installing NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Verify GPU access:

```bash
# For Blackwell GPUs
docker run --rm --gpus all nvcr.io/nvidia/jax:25.01-py3 nvidia-smi

# Check compute capability
nvidia-smi --query-gpu=name,compute_cap --format=csv
```

## Quick Start

### 1. Build the Image

```bash
cd CombFold
docker build -t combfold:latest .
```

### 2. Download Model Weights (Once)

```bash
docker run --gpus all --ipc=host \
    -v combfold_cache:/cache \
    combfold:latest \
    /app/docker/scripts/download_weights.sh
```

### 3. Run Predictions

```bash
# Prepare your data
mkdir -p data/input data/output

# Copy your subunits.json to data/input/
cp my_subunits.json data/input/

# Run the full pipeline
docker run --gpus all --ipc=host \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_pipeline.sh \
    /data/input/subunits.json \
    /data/output/my_complex
```

## Building the Image

### Standard Build (NGC JAX with Blackwell Support)

```bash
docker build -t combfold:latest .
```

The image uses `nvcr.io/nvidia/jax:25.01-py3` as the base, which includes:
- CUDA 12.x with Blackwell (CC 12.0) support
- Optimized JAX for NVIDIA GPUs
- Native bf16 support for Blackwell architecture

### Build with Docker Compose

```bash
docker-compose build
```

## Running Predictions

### Using Helper Scripts

The Docker image includes several helper scripts:

#### Full Pipeline (Recommended)

Runs all stages: FASTA generation → AFM predictions → Assembly

```bash
docker run --gpus all \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_pipeline.sh \
    /data/input/subunits.json \
    /data/output/my_complex \
    1800 \  # max_af_size (optional)
    5       # num_models (optional)
```

#### AFM Batch Predictions Only

```bash
docker run --gpus all \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_afm_batch.sh \
    /data/fastas \
    /data/predictions \
    5  # num_models
```

#### Assembly Only (Pre-computed PDBs)

```bash
docker run --gpus all \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_assembly.sh \
    /data/input/subunits.json \
    /data/pdbs \
    /data/output

# With crosslinks
docker run --gpus all \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_assembly.sh \
    /data/input/subunits.json \
    /data/pdbs \
    /data/output \
    /data/input/crosslinks.txt
```

### Using Docker Compose

```bash
# Start interactive session
docker-compose run combfold bash

# Inside container:
/app/docker/scripts/run_pipeline.sh /data/input/subunits.json /data/output/result
```

### Direct Commands

```bash
# Generate FASTA files
docker run --gpus all -v $(pwd)/data:/data combfold:latest \
    python3 /app/scripts/prepare_fastas.py \
    /data/input/subunits.json \
    --stage pairs \
    --output-fasta-folder /data/output/fastas

# Run ColabFold directly
docker run --gpus all \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    colabfold_batch /data/input/sequence.fasta /data/output/predictions

# Run assembly
docker run -v $(pwd)/data:/data combfold:latest \
    python3 /app/scripts/run_on_pdbs.py \
    /data/input/subunits.json \
    /data/pdbs \
    /data/output/assembly
```

## Full Pipeline

### Directory Structure

```
data/
├── input/
│   ├── subunits.json      # Your complex definition
│   └── crosslinks.txt     # Optional XL-MS constraints
├── output/
│   └── my_complex/
│       ├── fasta_pairs/       # Generated FASTA files
│       ├── fasta_groups/      # Group FASTA files
│       ├── afm_predictions/   # AFM PDB outputs
│       └── assembly/
│           └── assembled_results/
│               ├── output_clustered_0.pdb  # Best model
│               ├── output_clustered_1.pdb
│               └── confidence.txt
└── pdbs/                  # Pre-computed PDBs (optional)
```

### Example Workflow

```bash
# 1. Create directories
mkdir -p data/input data/output

# 2. Create subunits.json
cat > data/input/subunits.json << 'EOF'
{
  "ProteinA": {
    "name": "ProteinA",
    "chain_names": ["A", "B"],
    "start_res": 1,
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDG..."
  },
  "ProteinB": {
    "name": "ProteinB",
    "chain_names": ["C"],
    "start_res": 1,
    "sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKT..."
  }
}
EOF

# 3. Run full pipeline
docker run --gpus all \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_pipeline.sh \
    /data/input/subunits.json \
    /data/output/my_complex

# 4. View results
ls data/output/my_complex/assembly/assembled_results/
```

## Volume Management

### Cache Volume

The `combfold_cache` volume stores ColabFold/AlphaFold2 model weights (~5GB).

```bash
# Create named volume
docker volume create combfold_cache

# Download weights
docker run --gpus all -v combfold_cache:/cache combfold:latest \
    /app/docker/scripts/download_weights.sh

# List volumes
docker volume ls

# Inspect volume
docker volume inspect combfold_cache

# Remove volume (WARNING: will re-download weights)
docker volume rm combfold_cache
```

### Data Volumes

Mount local directories for input/output:

```bash
docker run --gpus all \
    -v combfold_cache:/cache \
    -v /path/to/input:/data/input:ro \
    -v /path/to/output:/data/output:rw \
    combfold:latest ...
```

## GPU Configuration

### Single GPU

```bash
docker run --gpus all ...
# or
docker run --gpus device=0 ...
```

### Specific GPU

```bash
docker run --gpus device=1 ...
```

### Multiple GPUs

ColabFold typically uses one GPU, but you can specify:

```bash
docker run --gpus '"device=0,1"' ...
```

### Memory Limits

For large sequences, you may need to limit GPU memory:

```bash
docker run --gpus all \
    -e TF_FORCE_GPU_ALLOW_GROWTH=true \
    -e XLA_PYTHON_CLIENT_MEM_FRACTION=0.8 \
    ...
```

## Blackwell GPU Support

The Docker image uses NVIDIA NGC JAX 25.01, which provides native support for Blackwell architecture GPUs (Compute Capability 12.0).

### Supported Blackwell GPUs

- NVIDIA RTX 50 series (RTX 5090, 5080, etc.)
- NVIDIA RTX PRO 6000 Blackwell
- NVIDIA B100, B200 (data center)

### Key Features for Blackwell

1. **Native bf16 support** - No workarounds needed for bfloat16 operations
2. **XLA attention** - Uses XLA instead of Triton (Triton 3.1.0 lacks CC 12.0 support)
3. **Optimized memory management** - Better GPU memory utilization

### Running on Blackwell GPUs

```bash
# Recommended flags for Blackwell
docker run --gpus all --ipc=host \
    --ulimit memlock=-1 --ulimit stack=67108864 \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    /app/docker/scripts/run_pipeline.sh \
    /data/input/subunits.json \
    /data/output/result
```

### Environment Variables for Blackwell

These are pre-configured in the image:

```bash
XLA_FLAGS="--xla_gpu_cuda_data_dir=/usr/local/cuda"
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_CPP_MIN_LOG_LEVEL=2
```

### Verifying Blackwell Support

```bash
# Check GPU compute capability
docker run --gpus all --ipc=host combfold:latest \
    python3 -c "import jax; print(jax.devices())"
```

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker GPU access (for Blackwell)
docker run --rm --gpus all nvcr.io/nvidia/jax:25.01-py3 nvidia-smi

# If nvidia-container-toolkit not installed:
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Out of GPU Memory

For large sequences (>1800 residues):

1. Use a GPU with more VRAM (24GB+ recommended)
2. Reduce `--max-af-size` parameter
3. Split large subunits into domains

```bash
# Reduce max size
/app/docker/scripts/run_pipeline.sh \
    /data/input/subunits.json \
    /data/output/result \
    1500  # Reduced from 1800
```

### Build Failures

```bash
# Clean Docker cache
docker builder prune

# Build with no cache
docker build --no-cache -t combfold:latest .
```

### Permission Issues

```bash
# Run as current user
docker run --user $(id -u):$(id -g) ...

# Fix output permissions
sudo chown -R $(id -u):$(id -g) data/output/
```

### Slow Predictions

First prediction is slower due to JIT compilation. Subsequent predictions are faster.

```bash
# Pre-compile by running a small test
docker run --gpus all -v combfold_cache:/cache combfold:latest \
    bash -c "echo '>test\nMKTAYIAK' > /tmp/test.fasta && colabfold_batch /tmp/test.fasta /tmp/out"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XDG_CACHE_HOME` | `/cache` | Cache directory for weights |
| `MPLCONFIGDIR` | `/cache` | Matplotlib config directory |
| `NVIDIA_VISIBLE_DEVICES` | `all` | GPUs to use |
| `TF_FORCE_GPU_ALLOW_GROWTH` | unset | Set to `true` for dynamic GPU memory |

## Advanced Usage

### Interactive Session

```bash
docker run -it --gpus all \
    -v combfold_cache:/cache \
    -v $(pwd)/data:/data \
    combfold:latest \
    bash
```

### Custom ColabFold Parameters

```bash
docker run --gpus all -v combfold_cache:/cache -v $(pwd)/data:/data combfold:latest \
    colabfold_batch /data/input.fasta /data/output \
    --num-models 5 \
    --num-recycle 3 \
    --amber \
    --use-gpu-relax \
    --msa-mode mmseqs2_uniref_env
```

### Singularity/Apptainer

Convert for HPC use:

```bash
singularity pull docker://combfold:latest
singularity run --nv combfold_latest.sif colabfold_batch ...
```

## See Also

- [Installation Guide](installation.md) - Native installation
- [Pipeline Guide](pipeline.md) - CombFold workflow details
- [Configuration](configuration.md) - Assembly parameters
