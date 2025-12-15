# Python API Reference

This document provides detailed documentation for all Python scripts and modules in CombFold.

## Table of Contents

- [Main Scripts](#main-scripts)
  - [run_on_pdbs.py](#run_on_pdbspy)
  - [prepare_fastas.py](#prepare_fastaspy)
- [Batch Processing Scripts](#batch-processing-scripts)
  - [batch_runner.py](#batch_runnerpy)
  - [run_combfold_job.py](#run_combfold_jobpy)
  - [run_msa_search.py](#run_msa_searchpy)
  - [run_afm_predictions.py](#run_afm_predictionspy)
  - [excel_to_subunits.py](#excel_to_subunitspy)
  - [split_large_subunits.py](#split_large_subunitspy)
- [Library Modules](#library-modules)
  - [utils_classes.py](#utils_classespy)
  - [utils_pdb.py](#utils_pdbpy)
  - [prepare_complex.py](#prepare_complexpy)
- [Automatic Pipeline](#automatic-pipeline)
- [Type Aliases](#type-aliases)

## Main Scripts

### run_on_pdbs.py

**Location:** `scripts/run_on_pdbs.py`

The main orchestrator script for Stage 4 (Combinatorial Assembly).

#### Command Line Usage

```bash
python3 scripts/run_on_pdbs.py <subunits.json> <pdbs_folder> <output_folder> [crosslinks.txt]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `subunits.json` | Yes | Path to subunits definition file |
| `pdbs_folder` | Yes | Directory containing AFM PDB predictions |
| `output_folder` | Yes | Output directory (must be empty or non-existent) |
| `crosslinks.txt` | No | Optional crosslinks constraint file |

#### Key Functions

##### `run_on_pdbs_folder()`

```python
def run_on_pdbs_folder(
    subunits_json_path: str,
    pdbs_folder: str,
    output_path: str,
    crosslinks_path: Optional[str] = None,
    output_cif: bool = False,
    max_results_number: int = 5
) -> None
```

Main entry point that orchestrates the complete assembly pipeline.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `subunits_json_path` | str | Path to subunits.json |
| `pdbs_folder` | str | Directory with PDB files |
| `output_path` | str | Output directory |
| `crosslinks_path` | Optional[str] | Path to crosslinks file |
| `output_cif` | bool | Output CIF instead of PDB |
| `max_results_number` | int | Number of models to generate |

##### `get_pdb_to_partial_subunits()`

```python
def get_pdb_to_partial_subunits(
    pdbs_folder: str,
    subunits_info: SubunitsInfo
) -> Dict[str, List[PartialSubunit]]
```

Scans PDB files to identify which subunits they contain.

**Returns:** Dictionary mapping PDB paths to lists of PartialSubunit objects found in each file.

##### `extract_representative_subunits()`

```python
def extract_representative_subunits(
    pdb_path_to_partial_subunits: Dict[str, List[PartialSubunit]],
    subunits_info: SubunitsInfo,
    representative_subunits_path: str
) -> None
```

For each subunit type, selects the highest-quality (pLDDT) structure as the representative.

##### `extract_transformations()`

```python
def extract_transformations(
    pdb_path_to_partial_subunits: Dict[str, List[PartialSubunit]],
    subunits_info: SubunitsInfo,
    representative_subunits_path: str,
    transformations_path: str
) -> None
```

Extracts rigid-body transformations from each PDB file using the AF2trans binary.

##### `run_combfold()`

```python
def run_combfold(
    representative_subunits_path: str,
    subunits_info: SubunitsInfo,
    transformations_path: str,
    crosslinks_path: Optional[str],
    output_path: str,
    output_cif: bool = False,
    max_results_number: int = 5,
    subunits_group1: Optional[List[str]] = None
) -> None
```

Executes the C++ CombinatorialAssembler binary and processes results.

##### `score_transformation()`

```python
def score_transformation(
    pdb_path1: str,
    pdb_path2: str
) -> Optional[float]
```

Calculates interface-pLDDT score between two subunits.

**Returns:** Average B-factor (pLDDT) of interface residues, or None if no interface exists.

#### Data Classes

##### `PartialSubunit`

```python
@dataclasses.dataclass
class PartialSubunit:
    subunit_name: str           # Name of the subunit
    pdb_path: str               # Source PDB file path
    chain_id: str               # Chain ID in the PDB
    start_residue_id: int       # First residue (inclusive)
    end_residue_id: int         # Last residue (inclusive)
    subunit_start_sequence_id: int  # Offset in full sequence
    is_complete: bool = False   # Whether it's the full subunit
```

##### `TransformationInfo`

```python
@dataclasses.dataclass
class TransformationInfo:
    subunit_names: Tuple[str, str]     # Pair of subunit names
    pdb_path: str                       # Source PDB path
    pdb_chain_ids: Tuple[str, str]      # Chain IDs in source
    rep_imposed_rmsds: Tuple[float, float]  # RMSD to representatives
    transformation_numbers: str          # 6 numbers (rotation + translation)
    score: float                         # Interface pLDDT score
```

---

### prepare_fastas.py

**Location:** `scripts/prepare_fastas.py`

Generates FASTA files for AlphaFold-Multimer predictions.

#### Command Line Usage

```bash
# Stage 2: Generate pairs
python3 scripts/prepare_fastas.py subunits.json \
    --stage pairs \
    --output-fasta-folder output/ \
    --max-af-size 1800

# Stage 3: Generate groups
python3 scripts/prepare_fastas.py subunits.json \
    --stage groups \
    --output-fasta-folder output/ \
    --max-af-size 1800 \
    --input-pairs-results pairs_pdbs/
```

#### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `subunits_json` | Yes | - | Path to subunits.json |
| `--stage` | Yes | `pairs` | Either `pairs` or `groups` |
| `--output-fasta-folder` | Yes | - | Output directory |
| `--max-af-size` | No | 1800 | Max residues per prediction |
| `--input-pairs-results` | Stage 3 | - | PDB folder from Stage 2 |

#### Key Functions

##### `save_fasta()`

```python
def save_fasta(
    subunit_names: List[str],
    subunits_info: SubunitsInfo,
    output_folder: str
) -> None
```

Writes a FASTA file for a combination of subunits.

**FASTA Format:**
```
>SubunitA_SubunitB
SEQUENCEA:SEQUENCEB
```

##### `get_fastas_for_pairs()`

```python
def get_fastas_for_pairs(
    subunits_info: SubunitsInfo,
    output_folder: str,
    max_af_size: int
) -> None
```

Generates FASTA files for all pairwise combinations.

**Output:** Up to `((N+1)*N)/2` FASTA files for N subunits.

##### `get_fastas_for_groups()`

```python
def get_fastas_for_groups(
    subunits_info: SubunitsInfo,
    output_folder: str,
    max_af_size: int,
    pairs_folder: str
) -> None
```

Generates FASTA files for larger groups (3-6 subunits) based on pair quality scores.

##### `score_pdb_pair()`

```python
def score_pdb_pair(
    pair_path: str,
    names_by_sequences: Dict[str, str]
) -> Optional[Tuple[Tuple[str, str], float]]
```

Scores a pair prediction based on interface pLDDT.

**Returns:** Tuple of ((subunit1, subunit2), score) or None if invalid.

---

## Batch Processing Scripts

### batch_runner.py

**Location:** `scripts/batch_runner.py`

Multi-GPU batch job orchestrator for processing multiple complexes from an Excel file.

#### Command Line Usage

```bash
python3 scripts/batch_runner.py --excel batch_jobs.xlsx --output-dir results/
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--excel` | `batch_jobs.xlsx` | Path to Excel file with job specs |
| `--output-dir` | `results` | Base output directory |
| `--max-af-size` | `1800` | Max sequence length for AFM |
| `--num-models` | `5` | Number of AFM models |
| `--force` | `False` | Re-run completed jobs |
| `--skip-afm` | `False` | Skip AFM predictions |

#### Key Functions

##### `get_job_status()`

```python
def get_job_status(job_id: str, output_dir: str = "results") -> str
```

Check the completion status of a job.

**Returns:** Status string (`not_started`, `subunits_created`, `fastas_created`, `predictions_done`, `completed`)

##### `find_free_gpu()`

```python
def find_free_gpu() -> Optional[int]
```

Find an available GPU that is not currently running a job.

**Returns:** GPU ID if available, None if all busy.

##### `detect_gpu_count()`

```python
def detect_gpu_count() -> int
```

Auto-detect the number of available GPUs using nvidia-smi.

---

### run_combfold_job.py

**Location:** `scripts/run_combfold_job.py`

Runs the complete CombFold pipeline for a single job on a specific GPU.

#### Command Line Usage

```bash
python3 scripts/run_combfold_job.py \
    --gpu 0 \
    --job_id Complex_001 \
    --sequences SEQ1 SEQ2 SEQ3
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--gpu` | Yes | GPU device ID to use |
| `--job_id` | Yes | Complex_ID (job identifier) |
| `--sequences` | Yes | Amino acid sequences (space-separated) |
| `--output_dir` | No | Base output directory (default: results) |
| `--skip_afm` | No | Skip AFM predictions |
| `--max_af_size` | No | Max sequence length (default: 1800) |
| `--num_models` | No | Number of AFM models (default: 5) |

#### Key Functions

##### `run_pipeline()`

```python
def run_pipeline(
    job_id: str,
    sequences: List[str],
    output_dir: str,
    gpu_id: int,
    skip_afm: bool = False,
    max_af_size: int = 1800,
    num_models: int = 5
) -> bool
```

Run the complete CombFold pipeline for a single job.

**Returns:** True if successful, False otherwise.

---

### run_msa_search.py

**Location:** `scripts/run_msa_search.py`

Generates Multiple Sequence Alignments (MSAs) from local MMseqs2 databases using colabfold_search.

This is part of the clean pipeline architecture for offline operation:
1. `run_msa_search.py` → Generate MSAs (this script)
2. `run_afm_predictions.py` → Structure prediction
3. `run_on_pdbs.py` → Combinatorial assembly

#### Command Line Usage

```bash
# Basic usage
python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db

# UniRef30 only (faster)
python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db --no-env

# With template search
python3 run_msa_search.py fastas/ msas/ --db /cache/colabfold_db --templates
```

| Argument | Required | Description |
|----------|----------|-------------|
| `fastas_folder` | Yes | Folder containing FASTA files |
| `output_folder` | Yes | Output folder for A3M files |
| `--db` | No | Path to MMseqs2 database (default: /cache/colabfold_db) |
| `--no-env` | No | Don't use environmental sequences |
| `--templates` | No | Search for templates (requires PDB70) |
| `--threads` | No | Number of CPU threads (default: 4) |

#### Key Functions

##### `run_colabfold_search()`

```python
def run_colabfold_search(
    fasta_path: str,
    output_folder: str,
    db_path: str,
    use_env: bool = True,
    use_templates: bool = False,
    threads: int = 4
) -> Tuple[bool, str]
```

Run colabfold_search on a single FASTA file.

**Returns:** Tuple of (success, message).

##### `check_database()`

```python
def check_database(db_path: str) -> Tuple[bool, str]
```

Verify that the MMseqs2 database exists and is valid.

**Returns:** Tuple of (is_valid, message).

##### `get_msa_status()`

```python
def get_msa_status(fasta_name: str, output_folder: str) -> str
```

Check MSA generation status for a FASTA file.

**Returns:** `completed` or `not_started`.

---

### run_afm_predictions.py

**Location:** `scripts/run_afm_predictions.py`

Runs ColabFold predictions on FASTA or A3M files in a directory.

#### Command Line Usage

```bash
# Online mode (uses ColabFold server)
python3 run_afm_predictions.py fastas/ pdbs/ --num-models 5

# Local mode (uses pre-computed A3M files)
python3 run_afm_predictions.py msas/ pdbs/ --msa-mode local

# Offline mode (no MSA)
python3 run_afm_predictions.py fastas/ pdbs/ --msa-mode single_sequence
```

| Argument | Required | Description |
|----------|----------|-------------|
| `input_folder` | Yes | Folder containing FASTA or A3M files |
| `pdbs_folder` | Yes | Output folder for PDB predictions |
| `--num-models` | No | Number of models (default: 5) |
| `--cpu` | No | Use CPU only |
| `--amber` | No | Apply AMBER relaxation |
| `--msa-mode` | No | MSA mode: mmseqs2_uniref_env, single_sequence, local |

#### Key Functions

##### `run_colabfold()`

```python
def run_colabfold(
    fasta_path: str,
    output_folder: str,
    num_models: int = 5,
    use_gpu: bool = True,
    amber_relax: bool = False
) -> Tuple[bool, str]
```

Run ColabFold batch on a single FASTA file.

**Returns:** Tuple of (success, message).

##### `get_prediction_status()`

```python
def get_prediction_status(
    fasta_name: str,
    output_folder: str,
    num_models: int
) -> str
```

Check prediction status for a FASTA file.

**Returns:** `completed`, `partial`, or `not_started`.

---

### excel_to_subunits.py

**Location:** `scripts/excel_to_subunits.py`

Converts Excel files with protein sequences to CombFold subunits.json format.

#### Command Line Usage

```bash
# Single complex
python3 scripts/excel_to_subunits.py sequences.xlsx -o subunits.json

# Multiple complexes
python3 scripts/excel_to_subunits.py sequences.xlsx --split -o output_dir/

# With sequence splitting
python3 scripts/excel_to_subunits.py sequences.xlsx --split -o output_dir/ --max-af-size 1800
```

| Argument | Required | Description |
|----------|----------|-------------|
| `excel_file` | Yes | Path to Excel file |
| `-o`, `--output` | No | Output path (default: subunits.json) |
| `--split` | No | Create separate files per complex |
| `--max-af-size` | No | Split large sequences into domains |

#### Key Functions

##### `row_to_subunits()`

```python
def row_to_subunits(
    complex_id: str,
    sequences: Dict[str, str]
) -> dict
```

Convert a single row's data to subunits.json format.

**Returns:** Dictionary in subunits.json format.

##### `sequences_list_to_dict()`

```python
def sequences_list_to_dict(sequences: List[str]) -> Dict[str, str]
```

Convert a list of sequences to a dict with chain letters.

**Returns:** Dict mapping chain letters to sequences.

---

### split_large_subunits.py

**Location:** `scripts/split_large_subunits.py`

Splits large protein sequences into domains for CombFold processing.

#### Command Line Usage

```bash
# Split and save
python3 scripts/split_large_subunits.py subunits.json -o subunits_split.json

# Check what would be split
python3 scripts/split_large_subunits.py subunits.json --check

# Custom max size
python3 scripts/split_large_subunits.py subunits.json -o out.json --max-af-size 1500

# Add overlap between domains
python3 scripts/split_large_subunits.py subunits.json -o out.json --overlap 50
```

| Argument | Required | Description |
|----------|----------|-------------|
| `input_file` | Yes | Input subunits.json file |
| `-o`, `--output` | No | Output file path |
| `--max-af-size` | No | Max combined size for AFM (default: 1800) |
| `--overlap` | No | Residue overlap between domains (default: 0) |
| `--check` | No | Only show what would be split |
| `--in-place` | No | Modify input file in place |

#### Key Functions

##### `split_subunits_for_af_size()`

```python
def split_subunits_for_af_size(
    subunits: dict,
    max_af_size: int = 1800,
    overlap: int = 0,
    verbose: bool = True
) -> dict
```

Split all subunits that exceed the maximum AFM prediction size.

**Returns:** New dictionary with split subunits.

##### `needs_splitting()`

```python
def needs_splitting(subunits: dict, max_af_size: int = 1800) -> bool
```

Check if any subunit needs splitting.

**Returns:** True if any subunit exceeds max_af_size / 2.

##### `calculate_domain_size()`

```python
def calculate_domain_size(
    sequence_length: int,
    max_af_size: int
) -> Tuple[int, int]
```

Calculate optimal domain size and number of domains.

**Returns:** Tuple of (domain_size, num_domains).

---

## Library Modules

### utils_classes.py

**Location:** `scripts/libs/utils_classes.py`

Core data structures and utilities.

#### Constants

```python
INTERFACE_MIN_ATOM_DIST = 8.0  # Angstroms, defines interface residues
```

#### Type Aliases

```python
SubunitName = str
ChainedSubunitName = str
ChainName = str
PdbPath = str
SubunitsInfo = Dict[SubunitName, SubunitInfo]
```

#### Classes

##### `SubunitInfo`

```python
@dataclasses.dataclass
class SubunitInfo:
    name: SubunitName       # Unique identifier
    chain_names: List[str]  # Chain IDs (defines stoichiometry)
    start_res: int          # Starting residue number
    sequence: str           # Amino acid sequence
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_unstructured_res_ids()` | List[int] | Residue IDs with 'X' in sequence |
| `get_end_res()` | int | Last residue number |
| `get_active_res_ids()` | List[int] | All structured residue IDs |
| `get_relative_active_res_ids()` | List[int] | Active IDs relative to start |
| `get_chained_names()` | List[str] | Names like "SubunitA_A", "SubunitA_B" |
| `to_dict()` | dict | Convert to dictionary |
| `from_dict(d)` | SubunitInfo | Create from dictionary (classmethod) |

##### `SubunitPdbInfo`

```python
@dataclasses.dataclass
class SubunitPdbInfo:
    chain_id: ChainName
    chain_residue_id: int
    pdb_residue_id: int
    length: int
```

#### Functions

##### `read_subunits_info()`

```python
def read_subunits_info(output_path: str) -> SubunitsInfo
```

Loads and validates a subunits.json file.

**Validation:**
- Key names must match `name` field
- No overlapping residues between subunits on same chain

##### `save_subunits_info()`

```python
def save_subunits_info(
    subunits_info: SubunitsInfo,
    output_path: str
) -> None
```

Saves SubunitsInfo to a JSON file.

---

### utils_pdb.py

**Location:** `scripts/libs/utils_pdb.py`

PDB file manipulation utilities.

#### Functions

##### `get_pdb_model_readonly()`

```python
def get_pdb_model_readonly(pdb_path: str) -> Bio.PDB.Model.Model
```

Reads a PDB file and returns the first model.

##### `copy_pdb_set_start_offset()`

```python
def copy_pdb_set_start_offset(
    input_path: str,
    start_offset: int,
    output_path: str
) -> None
```

Copies a PDB file, renumbering residues to start at `start_offset`.

##### `copy_pdb_rename_chain()`

```python
def copy_pdb_rename_chain(
    input_path: str,
    new_chain_name: str,
    output_path: str
) -> None
```

Copies a PDB file with a new chain ID.

---

### prepare_complex.py

**Location:** `scripts/libs/prepare_complex.py`

Functions for creating final complex structures from assembly results.

#### Functions

##### `apply_transform()`

```python
def apply_transform(
    pdb_path: str,
    output_path: str,
    transform_numbers: List[float]
) -> None
```

Applies a rigid-body transformation to a PDB file.

**Parameters:**
- `transform_numbers`: 6 floats [rx, ry, rz, tx, ty, tz] (Euler angles + translation)

##### `create_transformation_pdb()`

```python
def create_transformation_pdb(
    assembly_path: str,
    transforms_str: str,
    output_path: str,
    output_cif: bool = False
) -> None
```

Creates a complex PDB from a transformation string.

**Transform String Format:**
```
0(rx ry rz tx ty tz),1(rx ry rz tx ty tz),...
```

##### `create_complexes()`

```python
def create_complexes(
    result_path: str,
    first_result: Optional[int] = None,
    last_result: Optional[int] = None,
    output_folder: Optional[str] = None,
    output_cif: bool = False
) -> List[str]
```

Creates multiple complex structures from assembly results.

**Returns:** List of output file paths.

##### Internal Functions

```python
def _merge_models(
    model_path1: str,
    model_path2: str,
    output_path: str,
    output_cif: bool = False
) -> None

def _rotate_atom(
    coord: np.ndarray,
    euler_rotation_tuple: Tuple[float, float, float]
) -> np.ndarray
```

---

## Automatic Pipeline

**Location:** `scripts/automatic_pipeline/`

Advanced scripts for end-to-end automation (including AFM job management).

### run_on_job.py

Main orchestrator for fully automated pipeline.

### libs/get_alphafold_jobs.py

Generates AlphaFold job definitions.

### libs/run_alphafold_jobs.py

Submits and monitors AlphaFold jobs.

### libs/parse_alphafold_jobs.py

Parses AlphaFold results and scores interfaces.

### libs/run_assembly.py

Executes the assembly pipeline.

### configurable.py

Configuration management for the automatic pipeline.

---

## Type Aliases

Summary of type aliases used throughout the codebase:

```python
# From utils_classes.py
SubunitName = str              # e.g., "ProteinA"
ChainedSubunitName = str       # e.g., "ProteinA_A"
ChainName = str                # e.g., "A"
PdbPath = str                  # e.g., "/path/to/file.pdb"
SubunitsInfo = Dict[SubunitName, SubunitInfo]

# Common types
TransformNumbers = List[float]  # [rx, ry, rz, tx, ty, tz]
```

---

## Usage Examples

### Programmatic Usage

```python
from scripts.libs.utils_classes import read_subunits_info
from scripts.run_on_pdbs import run_on_pdbs_folder

# Load subunits configuration
subunits_info = read_subunits_info("subunits.json")

# Print subunit information
for name, info in subunits_info.items():
    print(f"{name}: {len(info.chain_names)} copies, {len(info.sequence)} residues")

# Run assembly
run_on_pdbs_folder(
    subunits_json_path="subunits.json",
    pdbs_folder="afm_predictions/",
    output_path="output/",
    crosslinks_path="crosslinks.txt",
    output_cif=False,
    max_results_number=10
)
```

### Custom Scoring

```python
from scripts.run_on_pdbs import score_transformation

# Score an interface
score = score_transformation(
    "subunit_A.pdb",
    "subunit_B.pdb"
)
if score:
    print(f"Interface pLDDT: {score:.1f}")
```

### Creating Custom Transformations

```python
from scripts.libs.prepare_complex import apply_transform, create_complexes

# Apply a transformation
apply_transform(
    pdb_path="input.pdb",
    output_path="transformed.pdb",
    transform_numbers=[0.1, 0.2, 0.3, 10.0, 20.0, 30.0]
)

# Create complexes from results
output_files = create_complexes(
    result_path="output_clustered.res",
    first_result=0,
    last_result=5,
    output_folder="final_models/",
    output_cif=True  # Output mmCIF format
)
```

---

## See Also

- [Pipeline Guide](pipeline.md) - How scripts fit into the workflow
- [Configuration Reference](configuration.md) - All configurable parameters
- [C++ Architecture](cpp-architecture.md) - Understanding the assembly algorithm
