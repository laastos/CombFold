# CombFold Documentation

## Overview

**CombFold** is a computational pipeline for predicting the structures of large protein complexes (up to 18,000+ amino acids and 32 subunits) by combining AlphaFold-Multimer (AFM) predictions with a novel Combinatorial Assembly algorithm.

The pipeline addresses a fundamental limitation in current protein structure prediction: while AlphaFold-Multimer excels at predicting structures of small to medium-sized complexes, it struggles with large protein assemblies due to computational and memory constraints. CombFold overcomes this by using a hierarchical approach that predicts structures for pairs and small groups of subunits, then intelligently assembles these predictions into a complete complex structure.

**Publication:** [Nature Methods (2024)](https://www.nature.com/articles/s41592-024-02174-0)

## Key Features

- **Hierarchical Assembly**: Builds complexes incrementally from pairs to larger assemblies
- **Crosslink Support**: Integrates XL-MS (cross-linking mass spectrometry) distance constraints
- **Collision Detection**: Spatial hashing with backbone collision filtering
- **Multi-Model Output**: Generates ranked models with confidence scores
- **Flexible Input**: Works with ColabFold, localcolabfold, or AlphaPullDown predictions

## Documentation Contents

| Document | Description |
|----------|-------------|
| [Installation Guide](installation.md) | System requirements, dependencies, and setup instructions |
| [Quick Start Guide](quickstart.md) | Get running with CombFold in 10 minutes |
| [Docker Guide](docker.md) | Run CombFold + LocalColabFold in Docker containers |
| [Pipeline Guide](pipeline.md) | Detailed walkthrough of all 4 pipeline stages |
| [Python API Reference](python-api.md) | Documentation for all Python scripts and modules |
| [C++ Architecture](cpp-architecture.md) | Technical details of the core assembly engine |
| [Configuration Reference](configuration.md) | All configuration options and parameters |
| [Examples & Tutorials](examples.md) | Step-by-step examples including crosslinks |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |
| [Contributing](contributing.md) | Guidelines for contributing to CombFold |

## Pipeline Overview

The CombFold pipeline consists of 4 stages:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CombFold Pipeline                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Stage 1: Define Subunits                                          │
│  ├── Create subunits.json                                          │
│  └── Define sequences, chain names, stoichiometry                  │
│                         ↓                                          │
│  Stage 2: Predict Pairs                                            │
│  ├── Generate FASTA files for all subunit pairs                    │
│  └── Run AlphaFold-Multimer predictions                            │
│                         ↓                                          │
│  Stage 3: Predict Groups (Optional)                                │
│  ├── Generate FASTA files for promising larger groups              │
│  └── Run AlphaFold-Multimer predictions                            │
│                         ↓                                          │
│  Stage 4: Combinatorial Assembly                                   │
│  ├── Extract representative subunits                               │
│  ├── Extract pairwise transformations                              │
│  ├── Run hierarchical assembly algorithm                           │
│  └── Generate final complex models                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone and build
git clone https://github.com/dina-lab3D/CombFold.git
cd CombFold/CombinatorialAssembler
make

# Install Python dependencies
pip install numpy biopython scipy

# Run assembly on example data
cd ..
python3 scripts/run_on_pdbs.py example/subunits.json example/pdbs output/
```

## Repository Structure

```
CombFold/
├── CombinatorialAssembler/     # C++ core assembly engine
│   ├── *.cc, *.h               # Main assembly algorithm
│   ├── libs_gamb/              # Geometry/molecular libraries
│   ├── libs_DockingLib/        # Docking/chemistry libraries
│   ├── AF2trans/               # Transform extraction
│   └── Makefile                # Build system
├── scripts/                     # Python pipeline scripts
│   ├── run_on_pdbs.py          # Main assembly orchestrator
│   ├── prepare_fastas.py       # FASTA generation
│   └── libs/                   # Support libraries
├── example/                    # Demo data and expected outputs
├── CombFold.ipynb              # Demo Jupyter notebook
└── README.md                   # Original documentation
```

## Getting Help

- **Issues**: Report bugs and request features at [GitHub Issues](https://github.com/dina-lab3D/CombFold/issues)
- **Demo**: Try the [Google Colab notebook](https://colab.research.google.com/github/dina-lab3D/CombFold/blob/master/CombFold.ipynb)
- **Paper**: Read the full methodology in [Nature Methods](https://www.nature.com/articles/s41592-024-02174-0)

## Citation

If you use CombFold in your research, please cite:

```bibtex
@article{combfold2024,
  title={Prediction of large protein complexes using combinatorial assembly},
  journal={Nature Methods},
  year={2024},
  doi={10.1038/s41592-024-02174-0}
}
```

## License

CombFold is released under the MIT License. See the LICENSE file for details.
