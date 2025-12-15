# Quick Start Guide

Get CombFold running in 10 minutes with this guide.

## Prerequisites

Before starting, ensure you have:

- Git installed
- C++ compiler (g++) with C++17 support
- Python 3.7+
- Boost libraries installed

See [Installation Guide](installation.md) for detailed setup instructions.

## Step 1: Clone and Build

```bash
# Clone the repository
git clone https://github.com/dina-lab3D/CombFold.git
cd CombFold

# Build C++ components
cd CombinatorialAssembler
make

# Install Python dependencies
pip install numpy biopython scipy
```

## Step 2: Run the Example

CombFold includes a complete example in the `example/` folder.

```bash
# Return to CombFold root
cd ..

# Run assembly on the example
python3 scripts/run_on_pdbs.py \
    example/subunits.json \
    example/pdbs \
    my_output/
```

### Expected Output

```
--- Searching for subunits in supplied PDB files
found full A0 in A0_A0_unrelaxed_rank_001.pdb chain A
found full A0 in A0_A0_unrelaxed_rank_001.pdb chain B
...
--- Extracting representative subunits...
rep A0 has plddt score 85.2
rep G0 has plddt score 82.1
...
--- Extracting pairwise transformations...
--- Running combinatorial assembly algorithm...
--- Finished combinatorial assembly, writing output models
--- Assembled 5 complexes, confidence: 72.5-89.3
```

### Output Files

```
my_output/
├── assembled_results/
│   ├── output_clustered_0.pdb    # Best model
│   ├── output_clustered_1.pdb    # Second best
│   ├── output_clustered_2.pdb    # ...
│   ├── output_clustered_3.pdb
│   ├── output_clustered_4.pdb
│   └── confidence.txt            # Confidence scores
└── _unified_representation/
    ├── assembly_output/          # Assembly working files
    └── transformations/          # Extracted transformations
```

## Step 3: View Results

Open the generated PDB files in your favorite molecular viewer:

```bash
# Using PyMOL
pymol my_output/assembled_results/output_clustered_0.pdb

# Using ChimeraX
chimerax my_output/assembled_results/output_clustered_0.pdb
```

## Running Your Own Complex

### A. Prepare Your Data

1. **Create `subunits.json`**:

```json
{
  "SubunitA": {
    "name": "SubunitA",
    "chain_names": ["A", "B"],
    "start_res": 1,
    "sequence": "MKTAYIAKQRQISFVK..."
  },
  "SubunitB": {
    "name": "SubunitB",
    "chain_names": ["C"],
    "start_res": 1,
    "sequence": "MVLSPADKTNVKAAWG..."
  }
}
```

2. **Generate pair FASTA files**:

```bash
python3 scripts/prepare_fastas.py \
    subunits.json \
    --stage pairs \
    --output-fasta-folder fasta_pairs/ \
    --max-af-size 1800
```

3. **Run AlphaFold-Multimer** on each FASTA file:

```bash
# Using localcolabfold
for fasta in fasta_pairs/*.fasta; do
    colabfold_batch "$fasta" afm_predictions/ --num-models 5
done
```

4. **Run CombFold assembly**:

```bash
python3 scripts/run_on_pdbs.py \
    subunits.json \
    afm_predictions/ \
    final_output/
```

### B. With Crosslinks (Optional)

If you have XL-MS data:

1. **Create `crosslinks.txt`**:

```
# Format: res1 chain1 res2 chain2 min_dist max_dist weight
94 A 651 B 0 30 0.85
149 A 196 C 0 30 0.92
```

2. **Run with crosslinks**:

```bash
python3 scripts/run_on_pdbs.py \
    subunits.json \
    afm_predictions/ \
    final_output/ \
    crosslinks.txt
```

## Google Colab Option

Don't want to install locally? Use the Colab notebook:

1. Open [CombFold Demo Notebook](https://colab.research.google.com/github/dina-lab3D/CombFold/blob/master/CombFold.ipynb)
2. Upload your `subunits.json` and PDB files to Google Drive
3. Follow the notebook instructions

## Common Quick Start Issues

### "Binary not found"

```bash
# Ensure you built the C++ components
cd CombinatorialAssembler
make
```

### "ImportError: No module named 'Bio'"

```bash
pip install biopython
```

### "Output folder not empty"

```bash
# CombFold won't overwrite existing output
rm -rf my_output/
# Then run again
```

### "Missing rep subunits"

Your PDB files don't contain all subunits defined in `subunits.json`. Ensure:
- All sequences in `subunits.json` match sequences in your PDB files
- At least one PDB file contains each subunit

## Batch Processing (Multiple Complexes)

For processing multiple complexes efficiently, use the batch runner:

### A. Create an Excel File

Create `batch_jobs.xlsx` with your sequences:

| Complex_ID | Chain_A | Chain_B | Chain_C |
|------------|---------|---------|---------|
| Complex_001 | MKTAYIAK... | MVLSPAD... | |
| Complex_002 | MDKLEQK... | MFDKILI... | MGDKIES... |

### B. Run Batch Processing

```bash
# Basic batch run (auto-detects GPUs)
python3 scripts/batch_runner.py --excel batch_jobs.xlsx

# With Docker
docker run --gpus all --ipc=host \
    -v combfold_cache:/cache \
    -v $(pwd)/batch_jobs.xlsx:/data/batch_jobs.xlsx:ro \
    -v $(pwd)/results:/data/results \
    combfold:latest \
    python3 /app/scripts/batch_runner.py \
    --excel /data/batch_jobs.xlsx \
    --output-dir /data/results
```

### C. Results

Results are organized per complex:

```
results/
├── Complex_001/
│   ├── subunits.json
│   ├── fastas/
│   ├── pdbs/
│   └── output/assembled_results/
│       ├── output_clustered_0.pdb
│       └── confidence.txt
└── Complex_002/
    └── ...
```

## Next Steps

- [Pipeline Guide](pipeline.md) - Understand all 4 stages in detail
- [Examples](examples.md) - More complex use cases
- [Configuration Reference](configuration.md) - Tune assembly parameters
- [Python API](python-api.md) - Programmatic usage
