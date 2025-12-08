# Python API Reference

This document provides detailed documentation for all Python scripts and modules in CombFold.

## Table of Contents

- [Main Scripts](#main-scripts)
  - [run_on_pdbs.py](#run_on_pdbspy)
  - [prepare_fastas.py](#prepare_fastaspy)
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
