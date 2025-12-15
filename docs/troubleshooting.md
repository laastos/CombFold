# Troubleshooting Guide

This guide covers common issues, error messages, and their solutions when using CombFold.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Build Errors](#build-errors)
- [Runtime Errors](#runtime-errors)
- [Assembly Problems](#assembly-problems)
- [Output Issues](#output-issues)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

## Installation Issues

### Boost Not Found

**Error:**
```
fatal error: boost/program_options.hpp: No such file or directory
```

**Solutions:**

1. **Install Boost:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libboost-all-dev

   # macOS
   brew install boost
   ```

2. **Update Makefile paths:**
   ```makefile
   # Edit CombinatorialAssembler/Makefile
   BOOST_INCLUDE = /path/to/boost/include
   BOOST_LIB = /path/to/boost/lib
   ```

3. **Find existing installation:**
   ```bash
   # Linux
   find /usr -name "program_options.hpp" 2>/dev/null

   # macOS
   find /usr/local /opt -name "program_options.hpp" 2>/dev/null
   ```

### Python Dependencies Missing

**Error:**
```
ModuleNotFoundError: No module named 'Bio'
```

**Solution:**
```bash
pip install biopython numpy scipy

# Or with specific versions
pip install biopython>=1.79 numpy>=1.19 scipy>=1.6
```

### Wrong Python Version

**Error:**
```
SyntaxError: invalid syntax
```

**Solution:**
```bash
# Check Python version
python3 --version  # Should be 3.7+

# Use python3 explicitly
python3 scripts/run_on_pdbs.py ...
```

---

## Build Errors

### C++17 Not Supported

**Error:**
```
error: unrecognized command line option '-std=c++17'
```

**Solutions:**

1. **Upgrade compiler:**
   ```bash
   # Ubuntu
   sudo apt-get install g++-9
   export CXX=g++-9
   ```

2. **Use C++14 fallback:**
   ```makefile
   # Edit Makefile
   CXXFLAGS = -std=c++14 -O2 -Wall
   ```

### Linker Errors

**Error:**
```
undefined reference to `boost::program_options::options_description::...'
```

**Solutions:**

1. **Check library path:**
   ```bash
   # Find library
   find /usr -name "libboost_program_options*" 2>/dev/null
   ```

2. **Add library path:**
   ```makefile
   LDFLAGS = -L/path/to/boost/lib -lboost_program_options
   ```

3. **Set LD_LIBRARY_PATH:**
   ```bash
   export LD_LIBRARY_PATH=/path/to/boost/lib:$LD_LIBRARY_PATH
   ```

### Make Fails with "No rule to make target"

**Error:**
```
make: *** No rule to make target 'libs_gamb/Vector3.o', needed by...
```

**Solution:**
```bash
# Ensure you're in the correct directory
cd CombinatorialAssembler
make clean
make
```

---

## Runtime Errors

### Binary Not Found

**Error:**
```
combinatorial assembly binary not found at .../CombinatorialAssembler.out
```

**Solution:**
```bash
# Build the binary
cd CombinatorialAssembler
make

# Verify it exists
ls -la CombinatorialAssembler.out
```

### Output Folder Not Empty

**Error:**
```
output path /path/to/output is not empty, exiting
```

**Note:** As of the latest version, CombFold automatically detects and cleans up directories containing only empty folders. You will see:
```
output path /path/to/output contains only empty folders, cleaning up and continuing...
```

If the directory contains actual files (not just empty folders), you'll need to manually resolve:

**Solution:**
```bash
# Remove existing output
rm -rf /path/to/output

# Or use a new folder name
python3 scripts/run_on_pdbs.py ... new_output_folder/
```

### Missing Rep Subunits

**Error:**
```
AssertionError: missing rep subunits for {'SubunitX'}
```

**Causes:**
- Sequence in subunits.json doesn't match PDB files
- PDB files don't contain all required subunits
- Sequence typos or formatting issues

**Solutions:**

1. **Verify sequences match:**
   ```python
   # Check PDB sequence
   from Bio.PDB import PDBParser
   from Bio import SeqUtils

   parser = PDBParser(QUIET=True)
   struct = parser.get_structure('pdb', 'your_file.pdb')
   for chain in struct[0]:
       seq = ''.join([SeqUtils.seq1(r.resname) for r in chain])
       print(f"Chain {chain.id}: {seq[:50]}...")
   ```

2. **Compare with subunits.json:**
   ```bash
   cat subunits.json | python3 -c "
   import json, sys
   data = json.load(sys.stdin)
   for name, info in data.items():
       print(f'{name}: {info[\"sequence\"][:50]}...')
   "
   ```

### Transformation Extraction Fails

**Error:**
```
Unexpected output from AF2mer2trans
```

**Causes:**
- PDB files have wrong format
- Missing chains in PDB files
- Residue numbering mismatches

**Solutions:**

1. **Check PDB format:**
   ```bash
   head -20 your_file.pdb
   # Should have ATOM records with chain IDs
   ```

2. **Verify chain presence:**
   ```bash
   grep "^ATOM" your_file.pdb | cut -c22 | sort -u
   # Should list all chain IDs
   ```

---

## Assembly Problems

### No Assembly Output

**Symptom:** Assembly completes but no models generated.

**Causes:**
1. All combinations filtered due to collisions
2. No compatible transformations found
3. Constraints too strict

**Solutions:**

1. **Check the log:**
   ```bash
   cat output/_unified_representation/assembly_output/output.log
   ```

2. **Relax parameters:**
   ```bash
   # Edit run_on_pdbs.py to use:
   -b 0.15 -t 0 -r 0.3 -p -2.0
   ```

3. **Verify transformations exist:**
   ```bash
   ls output/_unified_representation/transformations/
   # Should have files like SubunitA_plus_SubunitB
   ```

### Low Confidence Scores

**Symptom:** Models generated but all have low scores (< 50).

**Causes:**
1. Poor quality AFM predictions
2. Missing important interactions
3. Wrong subunit definitions

**Solutions:**

1. **Check AFM prediction quality:**
   - Look at pLDDT values in original PDB files
   - Re-run AFM with more models: `--num-models 5`

2. **Add group predictions (Stage 3):**
   ```bash
   python3 scripts/prepare_fastas.py ... --stage groups ...
   ```

3. **Verify subunit definitions are biologically meaningful**

### Incorrect Assembly Topology

**Symptom:** Models assemble wrong (e.g., chains in wrong positions).

**Solutions:**

1. **Check subunit definitions:**
   - Ensure chain_names are correct
   - Verify start_res values

2. **Add crosslink constraints:**
   ```bash
   # Create crosslinks.txt with known contacts
   python3 scripts/run_on_pdbs.py ... crosslinks.txt
   ```

3. **Use stricter parameters:**
   ```
   -b 0.05 -t 80
   ```

### Memory Error During Assembly

**Error:**
```
std::bad_alloc
```
or
```
Killed
```

**Solutions:**

1. **Reduce parameters:**
   ```
   # Reduce transformations read
   trans_num: 300 (instead of 900)

   # Reduce results kept
   best_k: 50 (instead of 100)
   ```

2. **Use swap space:**
   ```bash
   sudo fallocate -l 8G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

## Output Issues

### PDB Files Invalid

**Symptom:** Generated PDBs can't be opened in viewers.

**Solutions:**

1. **Check for truncation:**
   ```bash
   tail output_clustered_0.pdb
   # Should end with END or proper termination
   ```

2. **Try CIF output:**
   ```python
   # In run_on_pdbs.py, change:
   output_cif=True
   ```

3. **Validate PDB:**
   ```python
   from Bio.PDB import PDBParser
   parser = PDBParser(QUIET=True)
   try:
       struct = parser.get_structure('test', 'output_clustered_0.pdb')
       print(f"Successfully loaded {len(list(struct.get_atoms()))} atoms")
   except Exception as e:
       print(f"Error: {e}")
   ```

### Wrong Chain IDs in Output

**Symptom:** Output has different chain IDs than expected.

**Cause:** Internal naming uses `SubunitName_ChainID` format.

**Solution:** Chain IDs in output match the original chain_names from subunits.json.

### Missing Residues in Output

**Symptom:** Some residues missing from assembled models.

**Causes:**
1. Partial subunits used for assembly
2. Missing atoms in input PDBs

**Solutions:**

1. **Use complete AFM predictions**
2. **Check input PDBs have full sequences**

---

## Performance Issues

### Assembly Takes Too Long

**Typical times:**
- Small complex (< 10 subunits): < 5 minutes
- Medium complex (10-20 subunits): 5-30 minutes
- Large complex (> 20 subunits): 30+ minutes

**Solutions:**

1. **Reduce transformations:**
   ```
   trans_num: 500 (instead of 900)
   ```

2. **Reduce best_k:**
   ```
   best_k: 50 (instead of 100)
   ```

3. **Use relaxed collision detection:**
   ```
   -b 0.2 -t 0
   ```

### High Memory Usage

**Solutions:**

1. **Monitor memory:**
   ```bash
   # Run with memory monitoring
   /usr/bin/time -v python3 scripts/run_on_pdbs.py ...
   ```

2. **Reduce parameters (see above)**

3. **Process in batches for very large complexes**

---

## Common Error Messages Reference

| Error | Cause | Solution |
|-------|-------|----------|
| "missing rep subunits" | Sequence mismatch | Verify sequences |
| "output path is not empty" | Existing output with files | Remove or rename |
| "contains only empty folders, cleaning up" | Empty folders from interrupted run | Auto-cleaned, continues normally |
| "binary not found" | Not built | Run `make` |
| "Unexpected output from AF2mer2trans" | Bad PDB format | Check PDB files |
| "No module named 'Bio'" | Missing package | `pip install biopython` |
| "std::bad_alloc" | Out of memory | Reduce parameters |
| "Could not assemble" | All filtered | Relax parameters |

---

## Diagnostic Commands

### Check Installation

```bash
# C++ binaries
ls -la CombinatorialAssembler/*.out

# Python dependencies
python3 -c "import Bio, numpy, scipy; print('OK')"

# Version info
./CombinatorialAssembler/CombinatorialAssembler.out --version
```

### Validate Input

```bash
# Check subunits.json
python3 -c "
from scripts.libs.utils_classes import read_subunits_info
info = read_subunits_info('subunits.json')
for name, sub in info.items():
    print(f'{name}: {len(sub.chain_names)} chains, {len(sub.sequence)} residues')
"

# Check PDB folder
ls -la pdbs/*.pdb | wc -l
```

### Debug Assembly

```bash
# Run with verbose output
python3 scripts/run_on_pdbs.py subunits.json pdbs/ output/ 2>&1 | tee debug.log

# Check assembly log
cat output/_unified_representation/assembly_output/output.log
```

---

## Getting Help

### Resources

1. **GitHub Issues**: [github.com/dina-lab3D/CombFold/issues](https://github.com/dina-lab3D/CombFold/issues)
2. **Demo Notebook**: [Google Colab](https://colab.research.google.com/github/dina-lab3D/CombFold/blob/master/CombFold.ipynb)
3. **Paper**: [Nature Methods](https://www.nature.com/articles/s41592-024-02174-0)

### Reporting Issues

When reporting issues, include:

1. **System information:**
   ```bash
   uname -a
   python3 --version
   g++ --version
   ```

2. **Error message (complete)**

3. **Command used**

4. **Input file snippets (if relevant)**

5. **Output of diagnostic commands**

---

## See Also

- [Installation Guide](installation.md) - Setup instructions
- [Configuration Reference](configuration.md) - Parameter tuning
- [Examples](examples.md) - Working examples
