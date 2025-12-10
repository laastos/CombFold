# Installation Guide

This guide covers the complete installation process for CombFold, including system requirements, dependencies, and optional components.

## Table of Contents

- [System Requirements](#system-requirements)
- [Hardware Requirements](#hardware-requirements)
- [Operating System Support](#operating-system-support)
- [Installing Dependencies](#installing-dependencies)
- [Building CombFold](#building-combfold)
- [Verifying Installation](#verifying-installation)
- [Optional: AlphaFold-Multimer Setup](#optional-alphafold-multimer-setup)

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any modern x86_64 | Multi-core for faster assembly |
| RAM | 4 GB | 8+ GB for large complexes |
| Disk | 500 MB | 10+ GB (if running AFM locally) |
| GPU | Not required* | 12+ GB VRAM (for local AFM) |

*The Combinatorial Assembler itself runs on CPU only. GPU is only needed if you plan to run AlphaFold-Multimer predictions locally.

### Operating System Support

CombFold has been tested on:

| OS | Version | Status |
|----|---------|--------|
| macOS | Ventura (13.3.1)+ | Supported |
| Linux | Debian 10+ | Supported |
| Ubuntu | 20.04+ | Supported |
| Windows | WSL2 | Should work (untested) |

## Installing Dependencies

### C++ Dependencies

The Combinatorial Assembler requires **Boost** libraries (program_options and threading).

#### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y build-essential libboost-all-dev
```

#### Linux (CentOS/RHEL/Fedora)

```bash
sudo dnf install -y gcc-c++ boost-devel
# or for older systems:
sudo yum install -y gcc-c++ boost-devel
```

#### macOS

Using Homebrew:

```bash
brew install boost
```

If Boost is installed in a non-standard location, you may need to modify the Makefile:

```makefile
# Edit CombinatorialAssembler/Makefile
BOOST_INCLUDE = /path/to/boost/include
BOOST_LIB = /path/to/boost/lib
```

### Python Dependencies

CombFold requires Python 3.7+ with the following packages:

```bash
pip install numpy biopython scipy
```

Or install from requirements (if provided):

```bash
pip install -r requirements.txt
```

#### Package Details

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | >= 1.19 | Numerical operations, coordinate transformations |
| biopython | >= 1.79 | PDB/protein sequence handling |
| scipy | >= 1.6 | Distance calculations, scientific computing |

## Building CombFold

### Clone the Repository

```bash
git clone https://github.com/dina-lab3D/CombFold.git
cd CombFold
```

### Build the C++ Components

```bash
cd CombinatorialAssembler
make
```

This compiles two binaries:

| Binary | Purpose |
|--------|---------|
| `CombinatorialAssembler.out` | Main assembly algorithm |
| `AF2trans.out` | Transformation extraction from AFM predictions |

Build time is approximately 3 minutes on a modern system.

### Build Options

```bash
# Standard build
make

# Clean object files and rebuild
make clean
make

# Full clean (including static libraries)
make clean_all
make
```

### Troubleshooting Build Issues

#### Missing Boost Headers

```
fatal error: boost/program_options.hpp: No such file or directory
```

**Solution**: Install Boost or update the `BOOST_INCLUDE` path in the Makefile.

#### Linker Errors

```
undefined reference to `boost::program_options::...'
```

**Solution**: Ensure Boost libraries are installed and `BOOST_LIB` path is correct.

#### C++17 Compatibility

If your compiler doesn't support C++17:

```bash
# Check your g++ version
g++ --version

# Upgrade if needed (example for Ubuntu)
sudo apt-get install g++-9
```

## Verifying Installation

### Test C++ Binaries

```bash
cd CombinatorialAssembler

# Check binaries exist
ls -la CombinatorialAssembler.out AF2trans.out

# Test help output
./CombinatorialAssembler.out --help
```

Expected output:

```
Usage: <subunitsFileList> <transFilesPrefix> <transNumToRead> <bestKeachStep> <constraintsFile>
  -h [ --help ]                         Combinatoral Assembly help
  --version                             CombFold 1.0 2022
  -p [ --penetrationThr ] arg (=-1)     maximum allowed penetration...
  ...
```

### Test Python Environment

```bash
cd ..
python3 -c "
import numpy
import Bio
import scipy
print('All Python dependencies installed successfully!')
print(f'NumPy: {numpy.__version__}')
print(f'BioPython: {Bio.__version__}')
print(f'SciPy: {scipy.__version__}')
"
```

### Run Example

```bash
# Run the example assembly
python3 scripts/run_on_pdbs.py example/subunits.json example/pdbs test_output/

# Check output
ls test_output/assembled_results/
```

## Optional: AlphaFold-Multimer Setup

CombFold requires AlphaFold-Multimer predictions as input. You have several options:

### Comparison Table

| Feature | ColabFold (Colab) | LocalColabFold | AlphaPullDown | Pre-computed |
|---------|-------------------|----------------|---------------|--------------|
| **Cost** | Free | Hardware cost | Hardware cost | Varies |
| **GPU Required** | No (cloud) | Yes (12+ GB) | Yes (12+ GB) | No |
| **Disk Space** | None | ~500 GB | ~2 TB | None |
| **Installation** | None | Medium | Complex | None |
| **Throughput** | Low | High | High | N/A |
| **Session Limits** | Yes (12h) | No | No | No |
| **Best For** | Small projects, testing | Production, medium projects | Large-scale screens | Existing data |

### Capacity and Sequence Limits

| Capacity | ColabFold (Colab) | LocalColabFold | AlphaPullDown | Pre-computed |
|----------|-------------------|----------------|---------------|--------------|
| **Max Sequence Length** | ~1,800 residues* | ~3,000 residues** | ~4,000 residues** | N/A |
| **Max Sequences per Job** | 1 | Unlimited (batch) | Unlimited (batch) | N/A |
| **Predictions per Session** | 5-15 (depends on size) | Unlimited | Unlimited | N/A |
| **Typical Time per Prediction** | 10-30 min | 5-20 min | 5-20 min | N/A |
| **Parallel Predictions** | No | Yes (multi-GPU) | Yes (multi-GPU/nodes) | N/A |
| **Queue/Batch Support** | No | Yes | Yes (SLURM) | N/A |

*Free Colab tier with T4 GPU (16GB). Colab Pro with A100 can handle ~2,500 residues.

**Depends on GPU VRAM: 12GB GPU (~1,800 res), 24GB GPU (~3,000 res), 40GB+ GPU (~4,000 res).

### Sequence Size Guidelines by GPU

| GPU VRAM | Max Total Residues | Example Complex |
|----------|-------------------|-----------------|
| 12 GB (RTX 3080) | ~1,800 | 2 subunits × 900 res |
| 16 GB (T4, RTX 4080) | ~2,200 | 2 subunits × 1,100 res |
| 24 GB (RTX 3090/4090) | ~3,000 | 3 subunits × 1,000 res |
| 40 GB (A100-40GB) | ~4,000 | 4 subunits × 1,000 res |
| 80 GB (A100-80GB) | ~6,000 | 4 subunits × 1,500 res |

**Note:** These are approximate limits for multimer predictions. Actual limits depend on sequence composition and model version.

### Number of Predictions Required

The number of AFM predictions needed depends on your complex size:

| Unique Subunits | Stage 2 (Pairs) | Stage 3 (Groups)* | Total Predictions |
|-----------------|-----------------|-------------------|-------------------|
| 2 | 3 | 1-3 | 4-6 |
| 3 | 6 | 3-10 | 9-16 |
| 5 | 15 | 10-30 | 25-45 |
| 10 | 55 | 30-100 | 85-155 |
| 15 | 120 | 50-200 | 170-320 |
| 20 | 210 | 100-300 | 310-510 |

*Stage 3 is optional but recommended for better accuracy. Numbers are estimates.

**Formula for Stage 2 pairs:** `N × (N + 1) / 2` where N = number of unique subunits

### Which Option Should You Choose?

| Use Case | Recommended Option | Why |
|----------|-------------------|-----|
| **Testing CombFold / Learning** | ColabFold (Colab) | No setup, free, quick start |
| **Small complex (2-5 subunits)** | ColabFold (Colab) | Usually completes within session limits |
| **Medium complex (5-15 subunits)** | LocalColabFold | Faster MSA search, no session limits |
| **Large complex (15+ subunits)** | LocalColabFold or AlphaPullDown | Need many predictions, batch processing |
| **High-throughput screening** | AlphaPullDown | Designed for large-scale PPI screens |
| **Cluster/HPC environment** | AlphaPullDown | Better integration with job schedulers |
| **Already have predictions** | Pre-computed | Skip prediction step entirely |
| **No GPU access** | ColabFold (Colab) | Only option without local GPU |

### Detailed Option Descriptions

### Option 1: Google Colab (Free, No Local GPU)

Use [ColabFold](https://github.com/sokrypton/ColabFold) notebooks for free GPU access:

**Pros:**
- No installation required
- Free GPU access
- Easy to use, beginner-friendly
- Good for testing and small projects

**Cons:**
- Session time limits (~12 hours)
- Queue times during peak usage
- Manual file upload/download
- Not suitable for large-scale predictions

**Best for:** Testing, learning, small complexes (< 5 unique subunits)

### Option 2: LocalColabFold (Local GPU)

Install ColabFold locally:

```bash
# Follow instructions at:
# https://github.com/YoshitakaMo/localcolabfold

# Run predictions
colabfold_batch input.fasta output_folder --num-models 5
```

**Requirements:**
- NVIDIA GPU with 12+ GB VRAM (16+ GB recommended)
- CUDA toolkit
- ~500 GB disk space for databases

**Pros:**
- Fast MSA generation (MMseqs2)
- No session limits
- Full control over parameters
- Good balance of speed and ease of use

**Cons:**
- Requires local GPU
- Initial database download (~500 GB)
- Setup complexity

**Best for:** Regular use, medium to large complexes, production workflows

### Option 3: AlphaPullDown (Local GPU)

Alternative local runner focused on protein-protein interactions:

```bash
# Follow instructions at:
# https://github.com/KosinskiLab/AlphaPulldown
```

**Requirements:**
- NVIDIA GPU with 12+ GB VRAM
- CUDA toolkit
- ~2 TB disk space (full genetic databases)

**Pros:**
- Designed for protein-protein interaction screens
- Batch processing capabilities
- HPC/cluster integration (SLURM support)
- Uses full AlphaFold databases (potentially higher accuracy)

**Cons:**
- More complex installation
- Larger disk requirements
- Steeper learning curve

**Best for:** Large-scale screens, HPC environments, maximum accuracy needs

### Option 4: Pre-computed Predictions

If you already have AFM predictions from another source:

**Requirements:**
- PDB format files
- All predictions in a single folder
- Sequences must match subunits.json

**Pros:**
- No additional computation needed
- Use predictions from any source
- Fastest path to assembly

**Cons:**
- Must already have predictions
- Need to ensure format compatibility

**Best for:** Using existing data, combining with other workflows

### Hardware Recommendations by Option

| Option | GPU | RAM | Disk | Notes |
|--------|-----|-----|------|-------|
| ColabFold (Colab) | N/A | N/A | N/A | Cloud-based |
| LocalColabFold | RTX 3080+ (12GB) | 32 GB | 500 GB SSD | 16GB+ GPU for large predictions |
| AlphaPullDown | RTX 3090+ (24GB) | 64 GB | 2 TB SSD | A100 ideal for large complexes |
| Pre-computed | N/A | 8 GB | 10 GB | Only for assembly |

## Directory Structure After Installation

```
CombFold/
├── CombinatorialAssembler/
│   ├── CombinatorialAssembler.out    # Main binary
│   ├── AF2trans.out                   # Transform extraction binary
│   ├── libs_gamb/                     # Geometry libraries
│   ├── libs_DockingLib/               # Docking libraries
│   ├── DOCK.conf                      # Configuration
│   └── chem_params.txt                # Chemical parameters
├── scripts/
│   ├── run_on_pdbs.py
│   ├── prepare_fastas.py
│   └── libs/
├── example/
│   ├── subunits.json
│   └── pdbs/
└── docs/                              # This documentation
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first assembly
- [Pipeline Guide](pipeline.md) - Detailed usage instructions
- [Examples](examples.md) - Step-by-step tutorials
