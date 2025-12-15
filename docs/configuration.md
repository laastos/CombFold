# Configuration Reference

This document provides a comprehensive reference for all configurable parameters in CombFold.

## Table of Contents

- [Command Line Parameters](#command-line-parameters)
- [Batch Processing Configuration](#batch-processing-configuration)
- [DOCK.conf Configuration](#dockconf-configuration)
- [Crosslinks File Format](#crosslinks-file-format)
- [Subunits.json Schema](#subunitsjson-schema)
- [Environment Variables](#environment-variables)
- [Tuning Guidelines](#tuning-guidelines)

## Command Line Parameters

### run_on_pdbs.py

```bash
python3 scripts/run_on_pdbs.py <subunits.json> <pdbs_folder> <output_folder> [crosslinks.txt]
```

| Parameter | Position | Required | Description |
|-----------|----------|----------|-------------|
| subunits.json | 1 | Yes | Path to subunits definition file |
| pdbs_folder | 2 | Yes | Directory containing AFM PDB predictions |
| output_folder | 3 | Yes | Output directory (must not exist or be empty) |
| crosslinks.txt | 4 | No | Optional crosslink constraints file |

**Internal Parameters** (modifiable in code):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_cif` | False | Output CIF instead of PDB format |
| `max_results_number` | 5 | Number of final models to generate |

### prepare_fastas.py

```bash
python3 scripts/prepare_fastas.py subunits.json [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--stage` | `pairs` | Stage to run: `pairs` or `groups` |
| `--output-fasta-folder` | Required | Output directory for FASTA files |
| `--max-af-size` | 1800 | Maximum total residues per AFM prediction |
| `--input-pairs-results` | Required for groups | Directory with pair PDB results |

### CombinatorialAssembler.out

```bash
./CombinatorialAssembler.out <chain.list> <trans_prefix> <trans_num> <best_k> <constraints> [options]
```

#### Positional Arguments

| Position | Name | Description |
|----------|------|-------------|
| 1 | chain.list | File listing subunit PDB files |
| 2 | trans_prefix | Directory prefix for transformation files |
| 3 | trans_num | Maximum transformations to read per pair |
| 4 | best_k | Number of best results to keep per step |
| 5 | constraints | Crosslink constraints file |

#### Optional Arguments

| Flag | Long Form | Default | Description |
|------|-----------|---------|-------------|
| `-p` | `--penetrationThr` | -1.0 | Maximum allowed surface penetration |
| `-r` | `--restraintsRatio` | 0.1 | Maximum constraint violation ratio |
| `-c` | `--clusterRMSD` | 5.0 | RMSD threshold for clustering (Angstroms) |
| `-b` | `--maxBackboneCollisionPerChain` | 0.1 | Maximum backbone collision ratio (0-1) |
| `-t` | `--minTemperatureToConsiderCollision` | 0 | Minimum B-factor for collision detection |
| `-j` | `--maxResultPerResSet` | best_k | Results per subunit combination |
| `-o` | `--outputFileNamePrefix` | "output" | Output file name prefix |

#### Parameter Details

##### Penetration Threshold (`-p`)

Controls how much molecular surfaces can interpenetrate.

```
-p -1.0   # Default, allows slight overlap
-p -2.0   # More permissive
-p 0.0    # Strict, no penetration allowed
```

##### Backbone Collision (`-b`)

Maximum percentage of backbone atoms that can be in collision.

```
-b 0.1    # Default, 10% collision allowed
-b 0.05   # Stricter, only 5% allowed
-b 0.2    # More permissive, 20% allowed
```

##### Min Temperature (`-t`)

B-factor threshold for considering atoms in collision detection.

```
-t 0      # Default, consider all atoms
-t 50     # Only consider atoms with B-factor >= 50
-t 80     # Only high-confidence atoms (pLDDT >= 80)
```

##### Restraints Ratio (`-r`)

Maximum fraction of crosslink constraints that can be violated.

```
-r 0.1    # Default, 10% violation allowed
-r 0.0    # All constraints must be satisfied
-r 0.3    # 30% violation allowed
```

##### Cluster RMSD (`-c`)

RMSD threshold for clustering similar solutions.

```
-c 5.0    # Default, cluster within 5 Angstroms
-c 3.0    # Tighter clustering
-c 10.0   # Looser clustering, more diverse results
```

---

## Batch Processing Configuration

### batch_runner.py

```bash
python3 scripts/batch_runner.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--excel` | `batch_jobs.xlsx` | Path to Excel file with job specifications |
| `--output-dir` | `results` | Base output directory |
| `--max-af-size` | `1800` | Max combined sequence length for AFM |
| `--num-models` | `5` | Number of AFM models per prediction |
| `--force` | `False` | Re-run all jobs even if completed |
| `--skip-afm` | `False` | Skip AFM predictions (use existing PDBs) |

### Environment Variables for Batch Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_COUNT` | Auto-detected | Number of GPUs to use |
| `SLEEP_INTERVAL` | `10` | Seconds between GPU availability checks |
| `MESSAGE_INTERVAL` | `60` | Seconds between status messages |
| `COMBFOLD_DOCKER_IMAGE` | `combfold:latest` | Docker image for containerized runs |
| `COMBFOLD_NO_DOCKER` | `0` | Set to `1` to run outside Docker |

### Excel File Format

The Excel file must contain:

| Column | Required | Description |
|--------|----------|-------------|
| `Complex_ID` | Yes | Unique identifier for the complex |
| `Chain_A`, `Chain_B`, ... | Yes (at least one) | Amino acid sequences |

Example:

| Complex_ID | Chain_A | Chain_B | Chain_C |
|------------|---------|---------|---------|
| Protein_001 | MKTAYIAK... | MVLSPAD... | |
| Protein_002 | MDKLEQK... | MFDKILI... | MGDKIES... |

### split_large_subunits.py

```bash
python3 scripts/split_large_subunits.py <input.json> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o`, `--output` | stdout | Output file path |
| `--max-af-size` | `1800` | Max combined size for AFM predictions |
| `--overlap` | `0` | Residue overlap between domains |
| `--check` | `False` | Only show what would be split |
| `--in-place` | `False` | Modify input file in place |

### excel_to_subunits.py

```bash
python3 scripts/excel_to_subunits.py <excel_file> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o`, `--output` | `subunits.json` | Output path |
| `--split` | `False` | Create separate files per complex |
| `--max-af-size` | None | Split large sequences into domains |

### run_afm_predictions.py

```bash
python3 scripts/run_afm_predictions.py <fastas_folder> <pdbs_folder> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--num-models` | `5` | Number of models per prediction |
| `--cpu` | `False` | Use CPU only (no GPU) |
| `--amber` | `False` | Apply AMBER relaxation |

---

## DOCK.conf Configuration

**Location:** `CombinatorialAssembler/DOCK.conf`

This file contains geometric and algorithmic parameters used by the assembly algorithm.

### Model Parameters

```conf
MODEL_BUCKET_SIZE 0.5       # Grid bucket size for model hashing
MODEL_QUERY_RADIUS 1.5      # Query radius for model matching
```

### Hinge Parameters

```conf
HINGE_BUCKET_SIZE 0.5       # Grid bucket size for hinge detection
HINGE_QUERY_RADIUS 6.0      # Query radius for hinge search
```

### Triangle Parameters

```conf
TRIANGLE_SIZE_DIST 2.5      # Distance tolerance for triangles
TRIANGLE_SIZE_DIST_WH 4.0   # Distance tolerance (with hinge)
TRIANGLE_MAX_SEG_SIZE 12.0  # Maximum triangle segment size
TRIANGLE_MIN_SEG_SIZE 2.0   # Minimum triangle segment size
TRIANGLE_SEG_RATIO 4.0      # Segment ratio threshold
```

### Probability Parameters

```conf
PROBABILITY 0.05            # Sampling probability
PROBABILITY_WH 0.2          # Sampling probability (with hinge)
```

### Clustering Parameters

```conf
CLUSTER_RADIUS 4.0          # Clustering radius for matches
CLUSTER_RADIUS_WH 1.0       # Clustering radius (with hinge)
CLUSTER_RADIUS_RATIO 3.0    # Radius ratio for clustering
```

### Threshold Parameters

```conf
THRESHOLD 300               # Score threshold for filtering
THRESHOLD_WH -100           # Score threshold (with hinge)
```

### Grid Parameters

```conf
GRID_RESOLUTION 0.5         # Grid cell resolution (Angstroms)
GRID_MARGINS 5.0            # Extra margin around molecules
```

### Complete Default Configuration

```conf
#Model
MODEL_BUCKET_SIZE 0.5
MODEL_QUERY_RADIUS 1.5
HINGE_BUCKET_SIZE 0.5
HINGE_QUERY_RADIUS 6.0
TRIANGLE_SIZE_DIST 2.5
TRIANGLE_SIZE_DIST_WH 4.0
PROBABILITY 0.05
PROBABILITY_WH 0.2
CLUSTER_RADIUS 4.0
CLUSTER_RADIUS_WH 1.0
THRESHOLD 300
THRESHOLD_WH -100
GRID_RESOLUTION 0.5
GRID_MARGINS 5.0
#TriangleIterator
TRIANGLE_MAX_SEG_SIZE 12.0
TRIANGLE_MIN_SEG_SIZE 2.0
TRIANGLE_SEG_RATIO 4.0
#Cluster
CLUSTER_RADIUS_RATIO 3.0
```

---

## Crosslinks File Format

**Format:** Space-separated values, one crosslink per line

```
res1 chain1 res2 chain2 min_dist max_dist weight
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| res1 | int | Residue number of first crosslinked site |
| chain1 | char | Chain ID of first site |
| res2 | int | Residue number of second crosslinked site |
| chain2 | char | Chain ID of second site |
| min_dist | float | Minimum allowed distance (Angstroms) |
| max_dist | float | Maximum allowed distance (Angstroms) |
| weight | float | Weight/confidence of this crosslink (0-1) |

### Example

```
# Format: res1 chain1 res2 chain2 min_dist max_dist weight
94 A 651 B 0 30 0.85
149 A 651 B 0 30 0.92
280 C 196 A 0 30 0.96
789 D 159 E 0 30 0.67
40 E 27 F 0 30 0.86
```

### Distance Constraints

Typical crosslinker distance constraints:

| Crosslinker | Typical max_dist |
|-------------|------------------|
| DSS/BS3 | 30 Angstroms |
| EDC | 15 Angstroms |
| Photo-crosslinkers | Varies |

### Weight Guidelines

| Weight | Meaning |
|--------|---------|
| 0.9-1.0 | High confidence, reliable crosslink |
| 0.7-0.9 | Medium confidence |
| 0.5-0.7 | Low confidence, possibly ambiguous |
| < 0.5 | Very low confidence |

---

## Subunits.json Schema

### JSON Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "patternProperties": {
    "^[A-Za-z0-9_]+$": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Unique identifier (must match key)"
        },
        "chain_names": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Chain IDs in final complex"
        },
        "start_res": {
          "type": "integer",
          "minimum": 1,
          "description": "Starting residue number"
        },
        "sequence": {
          "type": "string",
          "pattern": "^[ACDEFGHIKLMNPQRSTVWYX]+$",
          "description": "Amino acid sequence"
        }
      },
      "required": ["name", "chain_names", "start_res", "sequence"]
    }
  }
}
```

### Field Details

#### name

- Must be unique across all subunits
- Must match the dictionary key
- Alphanumeric characters and underscores only

#### chain_names

- Array of single-character chain IDs
- Length determines stoichiometry
- Each chain ID should be unique within the complex
- Standard: A-Z, then a-z, then 0-9

#### start_res

- Starting residue number in the chain
- Usually 1 for complete chains
- Different from 1 when defining partial chains (domains)

#### sequence

- One-letter amino acid codes
- 'X' for unknown/unstructured residues
- Must match sequences in AFM predictions

### Complete Example

```json
{
  "Subunit_Alpha": {
    "name": "Subunit_Alpha",
    "chain_names": ["A", "B", "C"],
    "start_res": 1,
    "sequence": "MKDILEKLEERRAQARLGGGEKRLEAQHKRGKLTARERIELLLDHGSFEE"
  },
  "Subunit_Beta_N": {
    "name": "Subunit_Beta_N",
    "chain_names": ["D"],
    "start_res": 1,
    "sequence": "MFDKILIANRGEIACRIIKTAQKMGIKTVAVYSDADRDAVH"
  },
  "Subunit_Beta_C": {
    "name": "Subunit_Beta_C",
    "chain_names": ["D"],
    "start_res": 42,
    "sequence": "VAMADEAVHIGPAPAAQSYLLIEKIIDACKQTGAQAVHPGYGFLSERESFPK"
  }
}
```

---

## Environment Variables

CombFold respects the following environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `COMBFOLD_HOME` | Installation directory | Auto-detected |
| `BOOST_ROOT` | Boost installation path | System default |

---

## Tuning Guidelines

### For Better Accuracy

```bash
# Use stricter collision detection
-b 0.05 -t 80

# Require more constraint satisfaction
-r 0.05

# Generate more models, tighter clustering
-j 200 -c 3.0
```

### For Faster Assembly

```bash
# Read fewer transformations
# Change trans_num from 900 to 500

# Keep fewer intermediate results
# Change best_k from 100 to 50

# Looser collision detection
-b 0.15 -t 0
```

### For Challenging Complexes

```bash
# More permissive parameters
-b 0.15 -p -2.0 -r 0.2

# Keep more results
-j 500 -c 7.0
```

### For Symmetric Complexes

When assembling homo-oligomers:

```bash
# Ensure adequate sampling of symmetric transformations
# Use higher trans_num and best_k values
```

### With Crosslinks

```bash
# Use crosslinks but allow some violations
python3 scripts/run_on_pdbs.py subunits.json pdbs/ output/ crosslinks.txt

# Inside assembly, use:
-r 0.15  # Allow 15% violation for noisy XL-MS data
```

### Memory Constraints

For systems with limited memory:

```bash
# Reduce number of transformations
# Change trans_num from 900 to 300

# Reduce results kept
-j 50
```

---

## Configuration Profiles

### Profile: High Accuracy

```bash
CombinatorialAssembler.out chain.list trans/ 900 150 xlinks.txt \
    -b 0.05 -t 80 -r 0.05 -c 3.0 -p -0.5
```

### Profile: Fast Assembly

```bash
CombinatorialAssembler.out chain.list trans/ 300 50 xlinks.txt \
    -b 0.15 -t 0 -r 0.2 -c 7.0 -p -2.0
```

### Profile: Large Complex

```bash
CombinatorialAssembler.out chain.list trans/ 500 100 xlinks.txt \
    -b 0.1 -t 50 -r 0.15 -c 5.0 -p -1.0 -j 300
```

### Profile: With Good Crosslinks

```bash
CombinatorialAssembler.out chain.list trans/ 900 100 xlinks.txt \
    -b 0.1 -t 80 -r 0.05 -c 5.0 -p -1.0
```

---

## See Also

- [Pipeline Guide](pipeline.md) - How parameters affect each stage
- [C++ Architecture](cpp-architecture.md) - Technical parameter details
- [Troubleshooting](troubleshooting.md) - Parameter-related issues
- [Examples](examples.md) - Configuration in practice
