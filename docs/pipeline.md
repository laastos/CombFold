# CombFold Pipeline Guide

This document provides a comprehensive guide to the CombFold pipeline, covering all four stages in detail.

## Table of Contents

- [Pipeline Overview](#pipeline-overview)
- [Stage 1: Defining Subunits](#stage-1-defining-subunits)
- [Stage 2: Predicting Pairs](#stage-2-predicting-pairs)
- [Stage 3: Predicting Groups (Optional)](#stage-3-predicting-groups-optional)
- [Stage 4: Combinatorial Assembly](#stage-4-combinatorial-assembly)
- [Data Flow Diagram](#data-flow-diagram)
- [Batch Processing](#batch-processing)

## Pipeline Overview

CombFold predicts structures of large protein complexes through a divide-and-conquer approach:

1. **Divide**: Break the complex into smaller subunits
2. **Predict**: Use AlphaFold-Multimer to predict structures of subunit pairs/groups
3. **Assemble**: Combine predictions into a complete complex using hierarchical assembly

This approach enables structure prediction for complexes that are too large for direct AFM prediction.

```
                    ┌──────────────────┐
                    │  Input Sequences │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
        Stage 1 →   │  Define Subunits │ → subunits.json
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
        Stage 2 →   │  Generate Pairs  │ → FASTA files
                    │  Run AFM         │ → PDB predictions
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
        Stage 3 →   │  Generate Groups │ → FASTA files (optional)
                    │  Run AFM         │ → PDB predictions
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
        Stage 4 →   │  Assembly        │ → Final complex PDBs
                    └──────────────────┘
```

## Stage 1: Defining Subunits

### Purpose

Define the composition of your target complex: which proteins are present, their sequences, stoichiometry, and how chains relate to each other.

### The subunits.json File

Create a JSON file defining each unique subunit:

```json
{
  "SubunitName": {
    "name": "SubunitName",
    "chain_names": ["A", "B", "C"],
    "start_res": 1,
    "sequence": "MKDILEKLEERRAQARLGGG..."
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the subunit (must match the key) |
| `chain_names` | array | Chain IDs in the final complex (defines stoichiometry) |
| `start_res` | integer | Starting residue number (usually 1) |
| `sequence` | string | Amino acid sequence (one-letter codes) |

### Stoichiometry

The number of entries in `chain_names` defines the stoichiometry:

```json
{
  "ProteinA": {
    "name": "ProteinA",
    "chain_names": ["A", "B", "C"],  // 3 copies (A₃)
    "start_res": 1,
    "sequence": "MKTAYIAK..."
  }
}
```

### Guidelines for Defining Subunits

#### Basic Rule
Each unique sequence should be one subunit. Identical chains share the same subunit definition.

#### When to Split a Chain

Split a chain into multiple subunits when:

1. **Chain is too long**: If combined with other subunits, it exceeds your GPU's AFM limit (typically 1800 residues)

2. **Multi-domain proteins**: Separate structured domains that might fold independently

3. **Disordered regions**: Use tools like [IUPred3](https://iupred3.elte.hu/) to identify and remove disordered regions, splitting on these boundaries

#### Example: Multi-domain Protein

```json
{
  "ProteinE_N": {
    "name": "ProteinE_N",
    "chain_names": ["E"],
    "start_res": 1,
    "sequence": "MGDKIESKKAAAAAEVSTVPGFLGVIESPEHAVTIADEIGYPVMIKASAGA"
  },
  "ProteinE_C": {
    "name": "ProteinE_C",
    "chain_names": ["E"],
    "start_res": 51,
    "sequence": "GGGKGMRIAESADEVAEGFARAKSEASSSFGDDRVFVEKFITDPRHIEIQ"
  }
}
```

Note: Both subunits share chain "E" and `start_res` indicates where each subunit begins in the full chain.

### Complete Example

A complex with 12 chains from 2 unique proteins:

```json
{
  "Alpha": {
    "name": "Alpha",
    "chain_names": ["A", "B", "C", "D", "E", "F"],
    "start_res": 1,
    "sequence": "MKDILEKLEERRAQARLGGGEKRLEAQHKRGKLTARERIELLLDHGSFEE..."
  },
  "Beta": {
    "name": "Beta",
    "chain_names": ["G", "H", "I", "J", "K", "L"],
    "start_res": 1,
    "sequence": "MFDKILIANRGEIACRIIKTAQKMGIKTVAVYSDADRDAVHVAMADEAV..."
  }
}
```

This defines:
- Alpha: 6 copies (chains A-F)
- Beta: 6 copies (chains G-L)
- Total: 12 chains in an A₆B₆ complex

## Stage 2: Predicting Pairs

### Purpose

Generate AlphaFold-Multimer predictions for all pairwise combinations of subunits.

### Generate FASTA Files

```bash
python3 scripts/prepare_fastas.py \
    subunits.json \
    --stage pairs \
    --output-fasta-folder fasta_pairs/ \
    --max-af-size 1800
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `subunits.json` | Yes | - | Path to subunits definition |
| `--stage` | Yes | - | Set to `pairs` for this stage |
| `--output-fasta-folder` | Yes | - | Output directory for FASTA files |
| `--max-af-size` | No | 1800 | Maximum total residues per prediction |

### Output

For N unique subunits, generates up to `((N+1)*N)/2` FASTA files:

```
fasta_pairs/
├── Alpha_Alpha.fasta    # Homodimer
├── Alpha_Beta.fasta     # Heterodimer
└── Beta_Beta.fasta      # Homodimer
```

### FASTA Format

```
>Alpha_Beta
MKDILEKLEERRAQARLGGG...:MFDKILIANRGEIACRIIK...
```

Sequences are separated by `:` (ColabFold format).

### Running AlphaFold-Multimer

#### Option A: ColabFold (Google Colab)

Upload FASTA files and run using the ColabFold notebook.

#### Option B: LocalColabFold (Online)

```bash
for fasta in fasta_pairs/*.fasta; do
    colabfold_batch "$fasta" afm_results/ --num-models 5
done
```

#### Option C: Local MSA + ColabFold (Offline)

For fully offline operation with local databases:

```bash
# Step 1: Generate MSAs from local database
python3 scripts/run_msa_search.py fasta_pairs/ msas/ --db /cache/colabfold_db

# Step 2: Run predictions on A3M files
python3 scripts/run_afm_predictions.py msas/ afm_results/ --msa-mode local
```

This requires downloading the MMseqs2 databases first:

```bash
./docker/scripts/download_weights.sh --db-uniref  # ~100GB, UniRef30 only
```

#### Option D: Single Sequence (Offline, No MSA)

```bash
python3 scripts/run_afm_predictions.py fasta_pairs/ afm_results/ --msa-mode single_sequence
```

Note: This mode doesn't use MSA and produces less accurate predictions.

#### Option E: AlphaPullDown

```bash
# Follow AlphaPullDown documentation
```

### Expected AFM Output

For each FASTA file, AFM generates multiple models:

```
afm_results/
├── Alpha_Alpha_unrelaxed_rank_001_model_3.pdb
├── Alpha_Alpha_unrelaxed_rank_002_model_1.pdb
├── Alpha_Beta_unrelaxed_rank_001_model_2.pdb
└── ...
```

## Stage 3: Predicting Groups (Optional)

### Purpose

Generate predictions for larger groups of subunits (3-6 subunits) to improve assembly accuracy. This stage uses pair prediction scores to intelligently select promising combinations.

### When to Use

- **Recommended**: Always improves accuracy
- **Required**: For challenging complexes with many subunits
- **Skip**: If computational resources are very limited

### Generate Group FASTA Files

```bash
python3 scripts/prepare_fastas.py \
    subunits.json \
    --stage groups \
    --output-fasta-folder fasta_groups/ \
    --max-af-size 1800 \
    --input-pairs-results afm_results/
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stage groups` | Yes | Enables group generation |
| `--input-pairs-results` | Yes | Path to Stage 2 PDB results |
| `--output-fasta-folder` | Yes | Output directory |
| `--max-af-size` | No | Maximum residues per prediction |

### Selection Algorithm

The script selects groups based on:

1. **Interface quality**: Pairs with high interface-pLDDT scores
2. **Connectivity**: Groups that form connected subgraphs
3. **Size constraints**: Groups that fit within `--max-af-size`

### Manual Group Additions

Add biological knowledge by manually creating FASTA files for known subcomplexes:

```bash
# If you know Alpha and Beta form a specific trimer
echo ">Alpha_Alpha_Beta
SEQUENCE1:SEQUENCE1:SEQUENCE2" > fasta_groups/Alpha_Alpha_Beta.fasta
```

### Running AFM on Groups

Same as Stage 2:

```bash
for fasta in fasta_groups/*.fasta; do
    colabfold_batch "$fasta" afm_results/ --num-models 5
done
```

## Stage 4: Combinatorial Assembly

### Purpose

Combine all AFM predictions into a complete complex structure using the hierarchical assembly algorithm.

### Running Assembly

#### Basic Usage

```bash
python3 scripts/run_on_pdbs.py \
    subunits.json \
    path/to/all/pdbs/ \
    output_folder/
```

#### With Crosslinks

```bash
python3 scripts/run_on_pdbs.py \
    subunits.json \
    path/to/all/pdbs/ \
    output_folder/ \
    crosslinks.txt
```

### Assembly Process

The assembly consists of four sub-stages:

#### 4a. Extract Representative Subunits

For each unique subunit, select the best-quality structure (highest average pLDDT):

```
--- Extracting representative subunits...
rep Alpha has plddt score 85.2
rep Beta has plddt score 82.1
```

#### 4b. Extract Pairwise Transformations

From each PDB containing 2+ subunits, extract the rigid-body transformation:

```
--- Extracting pairwise transformations...
found 15 transformations between Alpha and Alpha
found 23 transformations between Alpha and Beta
found 12 transformations between Beta and Beta
```

#### 4c. Hierarchical Assembly

The C++ algorithm builds the complex incrementally:

1. Start with individual subunits
2. Combine pairs with best-scoring transformations
3. Progressively build larger assemblies
4. Filter by collision detection and constraints
5. Cluster and rank final models

```
--- Running combinatorial assembly algorithm...
Starting HierarchicalFold
...
Overall time 45.2 s
```

#### 4d. Generate Output Models

Apply transformations to create final PDB/CIF files:

```
--- Finished combinatorial assembly, writing output models
--- Assembled 5 complexes, confidence: 72.5-89.3
```

### Output Structure

```
output_folder/
├── assembled_results/
│   ├── output_clustered_0.pdb     # Best model
│   ├── output_clustered_1.pdb     # 2nd best
│   ├── output_clustered_2.pdb     # 3rd best
│   ├── output_clustered_3.pdb     # 4th best
│   ├── output_clustered_4.pdb     # 5th best
│   └── confidence.txt              # Scores for each model
└── _unified_representation/
    ├── assembly_output/
    │   ├── chain.list              # Subunit list
    │   ├── output.res              # Raw results
    │   ├── output_clustered.res    # Clustered results
    │   ├── output.log              # Assembly log
    │   └── *.pdb                   # Representative subunits
    └── transformations/
        └── SubunitA_plus_SubunitB  # Transformation files
```

### Understanding Confidence Scores

The `confidence.txt` file contains:

```
output_clustered_0.pdb 89.3
output_clustered_1.pdb 85.7
output_clustered_2.pdb 82.1
output_clustered_3.pdb 78.4
output_clustered_4.pdb 72.5
```

Scores are based on:
- Interface pLDDT values (B-factors)
- Crosslink constraint satisfaction (if provided)
- Transformation quality (RMSD from representative)

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CombFold Data Flow                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT                                                                  │
│  ─────                                                                  │
│  Protein sequences                                                      │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────┐                                                        │
│  │ subunits.json│ ◄── Stage 1: Manual creation                          │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │ prepare_fastas.py│                                                   │
│  │ --stage pairs   │ ◄── Stage 2                                        │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐     ┌──────────────┐                               │
│  │ FASTA files     │────▶│ AFM (external)│                               │
│  │ (pairs)         │     └──────┬───────┘                               │
│  └─────────────────┘            │                                       │
│                                 ▼                                       │
│                        ┌──────────────┐                                 │
│                        │ PDB files    │                                 │
│                        │ (pairs)      │                                 │
│                        └──────┬───────┘                                 │
│                               │                                         │
│         ┌─────────────────────┼─────────────────────┐                   │
│         │                     │                     │                   │
│         ▼                     ▼                     ▼                   │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐        │
│  │ prepare_fastas.py│   │                 │   │                 │        │
│  │ --stage groups  │   │   (optional)    │   │                 │        │
│  └────────┬────────┘   └─────────────────┘   └─────────────────┘        │
│           │ ◄── Stage 3 (optional)                                      │
│           ▼                                                             │
│  ┌─────────────────┐     ┌──────────────┐                               │
│  │ FASTA files     │────▶│ AFM (external)│                               │
│  │ (groups)        │     └──────┬───────┘                               │
│  └─────────────────┘            │                                       │
│                                 ▼                                       │
│                        ┌──────────────┐                                 │
│                        │ PDB files    │                                 │
│                        │ (groups)     │                                 │
│                        └──────┬───────┘                                 │
│                               │                                         │
│                               ▼                                         │
│         ┌─────────────────────────────────────────────────┐             │
│         │              All PDB files                      │             │
│         │         (pairs + groups combined)               │             │
│         └──────────────────────┬──────────────────────────┘             │
│                                │                                        │
│                                ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐          │
│  │                    run_on_pdbs.py                         │◄─ Stage 4│
│  │  ┌───────────────────────────────────────────────────┐    │          │
│  │  │ 4a. Extract representative subunits               │    │          │
│  │  │     (best pLDDT per subunit type)                 │    │          │
│  │  └───────────────────────┬───────────────────────────┘    │          │
│  │                          ▼                                │          │
│  │  ┌───────────────────────────────────────────────────┐    │          │
│  │  │ 4b. Extract transformations (via AF2trans.out)    │    │          │
│  │  │     (rigid-body transforms between subunits)      │    │          │
│  │  └───────────────────────┬───────────────────────────┘    │          │
│  │                          ▼                                │          │
│  │  ┌───────────────────────────────────────────────────┐    │          │
│  │  │ 4c. CombinatorialAssembler.out                    │    │          │
│  │  │     (hierarchical assembly algorithm)             │    │          │
│  │  └───────────────────────┬───────────────────────────┘    │          │
│  │                          ▼                                │          │
│  │  ┌───────────────────────────────────────────────────┐    │          │
│  │  │ 4d. prepare_complex.py                            │    │          │
│  │  │     (apply transforms, generate final PDBs)       │    │          │
│  │  └───────────────────────────────────────────────────┘    │          │
│  └────────────────────────────┬──────────────────────────────┘          │
│                               │                                         │
│                               ▼                                         │
│  OUTPUT                                                                 │
│  ──────                                                                 │
│  ┌─────────────────────────────────────────┐                            │
│  │ assembled_results/                      │                            │
│  │   ├── output_clustered_0.pdb (best)     │                            │
│  │   ├── output_clustered_1.pdb            │                            │
│  │   ├── ...                               │                            │
│  │   └── confidence.txt                    │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Batch Processing

For processing multiple complexes efficiently, CombFold provides a batch processing system that automates the entire pipeline and distributes jobs across multiple GPUs.

### Batch Processing Components

| Script | Purpose |
|--------|---------|
| `batch_runner.py` | Multi-GPU job orchestrator |
| `run_combfold_job.py` | Single job pipeline executor |
| `run_msa_search.py` | Local MSA generation (offline mode) |
| `run_afm_predictions.py` | ColabFold prediction runner |
| `excel_to_subunits.py` | Excel to subunits.json converter |
| `split_large_subunits.py` | Large sequence domain splitter |

### Excel Input Format

Define multiple complexes in an Excel file (`batch_jobs.xlsx`):

| Complex_ID | Chain_A | Chain_B | Chain_C |
|------------|---------|---------|---------|
| Complex_001 | MKTAYIAK... | MVLSPAD... | |
| Complex_002 | MDKLEQK... | MFDKILI... | MGDKIES... |

### Running Batch Jobs

```bash
# Basic batch run (auto-detects GPUs, uses ColabFold server for MSA)
python3 scripts/batch_runner.py --excel batch_jobs.xlsx

# With options
python3 scripts/batch_runner.py \
    --excel batch_jobs.xlsx \
    --output-dir results/ \
    --max-af-size 1800 \
    --num-models 5

# Fully offline with local MSA databases (recommended for HPC)
python3 scripts/batch_runner.py --excel batch_jobs.xlsx --msa-mode local

# Offline without MSA (faster but less accurate)
python3 scripts/batch_runner.py --excel batch_jobs.xlsx --msa-mode single_sequence

# Force re-run completed jobs
python3 scripts/batch_runner.py --excel batch_jobs.xlsx --force

# Skip AFM predictions (use existing PDBs)
python3 scripts/batch_runner.py --excel batch_jobs.xlsx --skip-afm
```

### Batch Output Structure

```
results/
├── Complex_001/
│   ├── subunits.json
│   ├── fastas/
│   ├── msas/           # Only when using --msa-mode local
│   ├── pdbs/
│   └── output/
│       └── assembled_results/
│           ├── output_clustered_0.pdb
│           └── confidence.txt
├── Complex_002/
│   └── ...
```

### Large Sequence Handling

For sequences exceeding the AFM size limit, use the domain splitter:

```bash
# Check what would be split
python3 scripts/split_large_subunits.py subunits.json --check

# Split large sequences
python3 scripts/split_large_subunits.py subunits.json -o subunits_split.json --max-af-size 1800

# With overlap between domains
python3 scripts/split_large_subunits.py subunits.json -o subunits_split.json --overlap 50
```

The batch runner automatically handles large sequences when `--max-af-size` is specified.

### Converting Excel to Subunits

```bash
# Single complex
python3 scripts/excel_to_subunits.py sequences.xlsx -o subunits.json

# Multiple complexes (separate directories)
python3 scripts/excel_to_subunits.py sequences.xlsx --split -o output_dir/

# With automatic sequence splitting
python3 scripts/excel_to_subunits.py sequences.xlsx --split -o output_dir/ --max-af-size 1800
```

## See Also

- [Examples](examples.md) - Complete worked examples
- [Configuration Reference](configuration.md) - Tuning parameters
- [Python API](python-api.md) - Programmatic usage
- [C++ Architecture](cpp-architecture.md) - Algorithm details
