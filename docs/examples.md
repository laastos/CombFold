# Examples and Tutorials

This document provides step-by-step examples for common CombFold use cases.

## Table of Contents

- [Example 1: Basic Assembly (Included Example)](#example-1-basic-assembly-included-example)
- [Example 2: Assembly with Crosslinks](#example-2-assembly-with-crosslinks)
- [Example 3: Full Pipeline from Sequences](#example-3-full-pipeline-from-sequences)
- [Example 4: Multi-Domain Protein](#example-4-multi-domain-protein)
- [Example 5: Large Symmetric Complex](#example-5-large-symmetric-complex)
- [Advanced: Custom Scoring](#advanced-custom-scoring)

## Example 1: Basic Assembly (Included Example)

The repository includes a complete example in the `example/` folder.

### Dataset Description

- **Complex**: A₆B₆ heterododecamer
- **Subunit Alpha (A0)**: 6 copies (chains A-F), 502 residues
- **Subunit Beta (G0)**: 6 copies (chains G-L), 592 residues
- **Total**: 12 chains, ~6,500 residues

### Step 1: Examine the Input

```bash
# View the subunits definition
cat example/subunits.json
```

```json
{
  "A0": {
    "name": "A0",
    "chain_names": ["A", "B", "C", "D", "E", "F"],
    "start_res": 1,
    "sequence": "MKDILEKLEERRAQARLGGG..."
  },
  "G0": {
    "name": "G0",
    "chain_names": ["G", "H", "I", "J", "K", "L"],
    "start_res": 1,
    "sequence": "MFDKILIANRGEIACRIIK..."
  }
}
```

```bash
# List the PDB files
ls example/pdbs/
```

### Step 2: Run Assembly

```bash
python3 scripts/run_on_pdbs.py \
    example/subunits.json \
    example/pdbs \
    example_output/
```

### Step 3: Examine Output

```bash
# List assembled models
ls example_output/assembled_results/

# View confidence scores
cat example_output/assembled_results/confidence.txt
```

Expected output:
```
output_clustered_0.pdb 89.2
output_clustered_1.pdb 85.7
output_clustered_2.pdb 82.3
output_clustered_3.pdb 78.9
output_clustered_4.pdb 74.1
```

### Step 4: Visualize

```bash
# Open in PyMOL
pymol example_output/assembled_results/output_clustered_0.pdb
```

### Step 5: Compare with Expected

```bash
# The expected output is provided
ls example/expected_assembled/
```

---

## Example 2: Assembly with Crosslinks

The repository includes a crosslinks example in `example/example_xlinks/`.

### Dataset Description

- **Complex**: 5-subunit assembly
- **Crosslinks**: 14 distance constraints from XL-MS

### Step 1: Examine Crosslinks

```bash
cat example/example_xlinks/crosslinks.txt
```

```
94 2 651 C 0 30 0.85
149 2 651 C 0 30 0.92
280 2 196 A 0 30 0.96
789 C 159 T 0 30 0.67
40 T 27 b 0 30 0.86
...
```

Format: `residue1 chain1 residue2 chain2 min_dist max_dist weight`

### Step 2: Run Assembly with Crosslinks

```bash
python3 scripts/run_on_pdbs.py \
    example/example_xlinks/subunits.json \
    example/example_xlinks/pdbs \
    xlinks_output/ \
    example/example_xlinks/crosslinks.txt
```

### Step 3: Analyze Crosslink Satisfaction

The assembly will prioritize models that satisfy more crosslinks:

```bash
# Models are ranked by combined score (pLDDT + crosslink satisfaction)
cat xlinks_output/assembled_results/confidence.txt
```

### Creating Your Own Crosslinks File

```bash
# Template
echo "# Format: res1 chain1 res2 chain2 min_dist max_dist weight" > my_crosslinks.txt
echo "45 A 120 B 0 30 0.90" >> my_crosslinks.txt
echo "78 A 89 C 0 30 0.85" >> my_crosslinks.txt
```

**Tips:**
- Use max_dist = 30 for DSS/BS3 crosslinkers
- Higher weights (0.9+) for confident crosslinks
- Include only high-confidence crosslinks for best results

---

## Example 3: Full Pipeline from Sequences

Complete walkthrough starting from amino acid sequences.

### Step 1: Create subunits.json

```bash
cat > my_complex/subunits.json << 'EOF'
{
  "ProtA": {
    "name": "ProtA",
    "chain_names": ["A", "B"],
    "start_res": 1,
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQQIAAALSSVRPCVAELPEFLKAGDFLCVTYAQSGSCQQIQALAEALESAVRTLQADLQQLFEQMERVLEQH"
  },
  "ProtB": {
    "name": "ProtB",
    "chain_names": ["C", "D"],
    "start_res": 1,
    "sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
  },
  "ProtC": {
    "name": "ProtC",
    "chain_names": ["E"],
    "start_res": 1,
    "sequence": "MGSSHHHHHHSSGLVPRGSHMGDKIESKKAAAAAEVSTVPGFLGVIESPEHAVTIADEIGYPVMIKASAGAGGGKGMRIAESADEVAEGFARAKSEASSSFGDDRVFVEKFITDPR"
  }
}
EOF
```

### Step 2: Generate Pair FASTA Files

```bash
mkdir -p my_complex/fastas_pairs

python3 scripts/prepare_fastas.py \
    my_complex/subunits.json \
    --stage pairs \
    --output-fasta-folder my_complex/fastas_pairs \
    --max-af-size 1800
```

Generated files:
```
my_complex/fastas_pairs/
├── ProtA_ProtA.fasta    # Homodimer
├── ProtA_ProtB.fasta    # Heterodimer
├── ProtA_ProtC.fasta
├── ProtB_ProtB.fasta    # Homodimer
├── ProtB_ProtC.fasta
└── ProtC_ProtC.fasta    # Homodimer
```

### Step 3: Run AlphaFold-Multimer

Using localcolabfold:

```bash
mkdir -p my_complex/afm_results

for fasta in my_complex/fastas_pairs/*.fasta; do
    echo "Running AFM on: $fasta"
    colabfold_batch "$fasta" my_complex/afm_results/ --num-models 5
done
```

Or using ColabFold on Google Colab (upload files manually).

### Step 4: (Optional) Generate Group FASTA Files

```bash
mkdir -p my_complex/fastas_groups

python3 scripts/prepare_fastas.py \
    my_complex/subunits.json \
    --stage groups \
    --output-fasta-folder my_complex/fastas_groups \
    --max-af-size 1800 \
    --input-pairs-results my_complex/afm_results
```

Run AFM on group files:

```bash
for fasta in my_complex/fastas_groups/*.fasta; do
    colabfold_batch "$fasta" my_complex/afm_results/ --num-models 5
done
```

### Step 5: Run Assembly

```bash
python3 scripts/run_on_pdbs.py \
    my_complex/subunits.json \
    my_complex/afm_results \
    my_complex/output/
```

### Step 6: Analyze Results

```bash
# View results
ls my_complex/output/assembled_results/

# Check confidence
cat my_complex/output/assembled_results/confidence.txt

# Visualize best model
pymol my_complex/output/assembled_results/output_clustered_0.pdb
```

---

## Example 4: Multi-Domain Protein

When a protein chain has multiple independent domains.

### Scenario

Chain E is 500 residues with two domains:
- Domain 1: residues 1-250
- Domain 2: residues 251-500

### Step 1: Define Split Subunits

```json
{
  "ProtE_N": {
    "name": "ProtE_N",
    "chain_names": ["E"],
    "start_res": 1,
    "sequence": "FIRST_250_RESIDUES..."
  },
  "ProtE_C": {
    "name": "ProtE_C",
    "chain_names": ["E"],
    "start_res": 251,
    "sequence": "LAST_250_RESIDUES..."
  },
  "ProtF": {
    "name": "ProtF",
    "chain_names": ["F"],
    "start_res": 1,
    "sequence": "FULL_SEQUENCE..."
  }
}
```

**Key Points:**
- Both `ProtE_N` and `ProtE_C` share chain "E"
- `start_res` indicates position in full chain
- Assembly will connect both domains to form chain E

### Step 2: Run Pipeline

```bash
# Generate FASTA files (all pairs)
python3 scripts/prepare_fastas.py subunits.json \
    --stage pairs \
    --output-fasta-folder fastas/ \
    --max-af-size 1800

# This generates pairs including:
# - ProtE_N_ProtE_C (domain interaction)
# - ProtE_N_ProtF
# - ProtE_C_ProtF
```

### Step 3: Assembly

The assembler will:
1. Place both domains
2. Enforce chain connectivity (N-C terminal constraint)
3. Output complete chain E with correct residue numbering

---

## Example 5: Large Symmetric Complex

Assembling a homo-oligomer with many copies.

### Scenario

A decameric ring: 10 copies of the same protein.

### Step 1: Define Subunits

```json
{
  "MonomerA": {
    "name": "MonomerA",
    "chain_names": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
    "start_res": 1,
    "sequence": "MONOMER_SEQUENCE..."
  }
}
```

### Step 2: Generate Pairs

For a homo-oligomer, only one FASTA file is needed:

```bash
python3 scripts/prepare_fastas.py subunits.json \
    --stage pairs \
    --output-fasta-folder fastas/ \
    --max-af-size 1800
```

Generates:
```
fastas/
└── MonomerA_MonomerA.fasta
```

### Step 3: Run AFM with Multiple Seeds

For symmetric complexes, use multiple random seeds:

```bash
colabfold_batch MonomerA_MonomerA.fasta afm_results/ \
    --num-models 5 \
    --num-seeds 5
```

This generates 25 predictions, increasing chances of capturing different interfaces.

### Step 4: Assembly

```bash
python3 scripts/run_on_pdbs.py subunits.json afm_results/ output/
```

The assembler will:
1. Identify all unique interfaces (may find multiple)
2. Build the ring using consistent transformations
3. Check for symmetric closure

---

## Advanced: Custom Scoring

### Modify Scoring in Python

Edit `scripts/run_on_pdbs.py`:

```python
def score_transformation(pdb_path1: str, pdb_path2: str) -> Optional[float]:
    # ... existing code ...

    # Custom: Weight by sequence identity
    seq_identity = calculate_sequence_identity(chain1_seq, chain2_seq)
    custom_weight = 1.0 if seq_identity < 0.5 else 0.8

    # Custom: Penalize small interfaces
    interface_size = len(chain1_interface) + len(chain2_interface)
    size_bonus = min(interface_size / 50.0, 1.0)

    return (sum(bfactors) / len(bfactors)) * custom_weight * size_bonus
```

### Command Line Parameter Tuning

```bash
# High-quality assembly
python3 scripts/run_on_pdbs.py subunits.json pdbs/ output/

# Internally, the C++ assembler uses:
# -b 0.05 -t 80  # Stricter collision
```

For relaxed parameters, modify `run_on_pdbs.py`:

```python
subprocess.run(f"{COMB_ASSEMBLY_BIN_PATH} chain.list {transformations_path}/ 900 100 xlink_consts.txt "
               f"-b 0.15 -t 50 -r 0.2 > output.log 2>&1", shell=True)
```

---

## Example Output Analysis

### Understanding output_clustered.res

```bash
cat output/_unified_representation/assembly_output/output_clustered.res
```

Format:
```
[transformations] key1 value1 key2 value2 ...
```

Example:
```
[0(0.1 0.2 0.3 10 20 30),1(0 0 0 0 0 0),...] weightedTransScore 85.2 numTrans 15
```

- Numbers in parentheses: `(rx ry rz tx ty tz)` rotation + translation
- `weightedTransScore`: Average interface pLDDT
- `numTrans`: Number of transformations used

### Interpreting Confidence Scores

| Score Range | Interpretation |
|-------------|----------------|
| > 85 | High confidence, likely correct |
| 70-85 | Good confidence, may need validation |
| 50-70 | Low confidence, significant uncertainty |
| < 50 | Very uncertain, likely incorrect |

---

## Common Workflows

### Workflow 1: Quick Test

```bash
# Use only pairs, no groups
python3 scripts/prepare_fastas.py subunits.json --stage pairs ...
# Run AFM
python3 scripts/run_on_pdbs.py ...
```

### Workflow 2: High Quality

```bash
# Use pairs + groups
python3 scripts/prepare_fastas.py subunits.json --stage pairs ...
# Run AFM on pairs
python3 scripts/prepare_fastas.py subunits.json --stage groups ...
# Run AFM on groups
python3 scripts/run_on_pdbs.py ...
```

### Workflow 3: With Experimental Constraints

```bash
# Prepare crosslinks from XL-MS data
# Run assembly with constraints
python3 scripts/run_on_pdbs.py subunits.json pdbs/ output/ crosslinks.txt
```

---

## Troubleshooting Examples

### "Missing rep subunits"

```
AssertionError: missing rep subunits for {'ProteinC'}
```

**Cause**: No PDB file contains the sequence for ProteinC.

**Solution**: Check sequence matches in subunits.json vs. PDB files.

### Low Confidence Scores

**Possible causes**:
1. Poor AFM predictions (check individual pLDDT)
2. Missing key interactions (add group predictions)
3. Wrong subunit definitions

**Solutions**:
- Re-run AFM with more models/seeds
- Add Stage 3 group predictions
- Verify sequences are correct

---

## See Also

- [Pipeline Guide](pipeline.md) - Detailed stage descriptions
- [Configuration Reference](configuration.md) - Parameter tuning
- [Troubleshooting](troubleshooting.md) - Common issues
