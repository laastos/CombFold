# C++ Architecture Documentation

This document provides technical details about the C++ Combinatorial Assembler engine, including its architecture, algorithms, and data structures.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
- [Hierarchical Assembly Algorithm](#hierarchical-assembly-algorithm)
- [Data Structures](#data-structures)
- [Libraries](#libraries)
- [Build System](#build-system)
- [Command Line Interface](#command-line-interface)

## Overview

The Combinatorial Assembler is written in C++ for performance-critical assembly operations. It implements a hierarchical folding algorithm that builds protein complexes incrementally from pairwise transformations.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CombinatorialAssembler                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ MainCombDock│───▶│ HierarchicalFold │───▶│   Output Files  │     │
│  │    (.cc)    │    │     (.cc/.h)     │    │   (.res, .txt)  │     │
│  └──────┬──────┘    └────────┬─────────┘    └─────────────────┘     │
│         │                    │                                       │
│         ▼                    ▼                                       │
│  ┌─────────────┐    ┌─────────────────┐                             │
│  │ BBContainer │    │     SuperBB     │                             │
│  │   (.h)      │    │   (.cc/.h)      │                             │
│  └──────┬──────┘    └────────┬────────┘                             │
│         │                    │                                       │
│         ▼                    ▼                                       │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │     BB      │    │ Transformation  │    │    Scoring      │     │
│  │  (.cc/.h)   │    │   AndScore      │    │   Functions     │     │
│  └──────┬──────┘    └─────────────────┘    └─────────────────┘     │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                        Libraries                             │   │
│  │  ┌──────────────┐              ┌──────────────────┐         │   │
│  │  │  libs_gamb   │              │  libs_DockingLib │         │   │
│  │  │  (geometry)  │              │    (chemistry)   │         │   │
│  │  └──────────────┘              └──────────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
CombinatorialAssembler/
├── MainCombDock.cc              # Entry point
├── HierarchicalFold.cc/h        # Core assembly algorithm
├── SuperBB.cc/h                 # Super building block (assembly)
├── BB.cc/h                      # Building block (single subunit)
├── BBContainer.h                # Container for all BBs
├── BBGrid.cc/h                  # Spatial grid for collision
├── BitId.h                      # Bitset-based subunit tracking
├── BestK.h/cc                   # Priority queue for top K results
├── FoldStep.h                   # Assembly step tracking
├── TransformationAndScore.cc/h  # Transformation data
├── ComplexDistanceConstraint.cc/h # Distance constraints
├── DOCK.conf                    # Configuration file
├── chem_params.txt              # Chemical parameters
├── Makefile                     # Build system
│
├── AF2trans/                    # Transform extraction
│   └── AF2trans.cc              # Main source
│
├── libs_gamb/                   # Geometry library
│   ├── Vector3.h                # 3D vector
│   ├── Matrix3.h                # 3x3 matrix
│   ├── RigidTrans3.h            # Rigid transformation
│   ├── Atom.h                   # Atom representation
│   ├── Molecule.h               # Molecule structure
│   └── ...                      # Additional utilities
│
└── libs_DockingLib/             # Docking library
    ├── ChemMolecule.cc/h        # Chemical molecule
    ├── ChemAtom.h               # Chemical atom
    ├── ChemLib.h                # Chemistry library
    ├── CrossLink.h              # Crosslink constraints
    ├── DistanceRestraint.h      # Distance restraints
    ├── connolly_surface.cc      # Surface calculation
    └── ...                      # Additional utilities
```

## Core Components

### MainCombDock.cc

Entry point that handles:

1. **Argument parsing** (using Boost.program_options)
2. **Initialization** of BBContainer with subunit structures
3. **Loading transformations** from files
4. **Running** the HierarchicalFold algorithm
5. **Output** of results and timing information

```cpp
int main(int argc, char *argv[]) {
    // Parse arguments
    po::options_description desc("Usage...");
    // ... argument definitions ...

    // Initialize container
    BBContainer bbContainer(suFileName, chemLibFileName, minTemp);
    bbContainer.readTransformationFiles(transFilesPrefix, transNumToRead);

    // Run assembly
    HierarchicalFold hierarchalFold(bbContainer, bestK, ...);
    hierarchalFold.readConstraints(constraintsFileName);
    hierarchalFold.fold(outFileNamePrefix);

    return 0;
}
```

### HierarchicalFold

The core assembly algorithm that builds complexes hierarchically.

#### Key Methods

```cpp
class HierarchicalFold {
public:
    // Constructor
    HierarchicalFold(BBContainer& bbContainer, int bestK,
                     unsigned int maxResultPerResSet,
                     float minTempForCollision,
                     float maxBackboneCollisionPerChain,
                     double penetrationThr,
                     double restraintsRatio);

    // Main assembly method
    void fold(std::string outFileNamePrefix);

    // Read distance constraints (crosslinks)
    void readConstraints(std::string constraintsFileName);

    // Check connectivity of input graph
    void checkConnectivity();

    // Output connectivity graph for debugging
    void outputConnectivityGraph(std::string fileName);

private:
    // Hierarchical fold step
    void hierarchicalFold(int stepSize, BestK<SuperBB>& bestKSuperBBs);

    // Try combining two SuperBBs
    void tryConnect(SuperBB& sbb1, SuperBB& sbb2, int stepSize,
                    BestK<SuperBB>& bestKSuperBBs);

    // Score a combination
    float scoreAssembly(SuperBB& assembly);
};
```

#### Algorithm Flow

```
1. Initialize: Create SuperBB for each individual subunit
     │
     ▼
2. For stepSize = 2 to N (total subunits):
     │
     ├─▶ For each pair of combinable SuperBBs:
     │       │
     │       ├─▶ Try all compatible transformations
     │       │
     │       ├─▶ Check collision constraints
     │       │
     │       ├─▶ Check distance constraints (crosslinks)
     │       │
     │       └─▶ Keep top K results for this combination
     │
     └─▶ Cluster and filter results
     │
     ▼
3. Output final models with scores
```

### SuperBB (Super Building Block)

Represents an assembled group of subunits with their transformations.

```cpp
class SuperBB {
public:
    // Get which subunits are included
    BitId getResidSet() const;

    // Add a new building block with transformation
    void addBB(int bbIndex, const RigidTrans3& trans);

    // Calculate collision score with another SuperBB
    float calculateCollisionScore(const SuperBB& other) const;

    // Apply transformation to all subunits
    void applyTransformation(const RigidTrans3& trans);

    // Get transformation string for output
    std::string getTransformationString() const;

private:
    BitId residSet_;                    // Bitset of included subunits
    std::vector<int> bbIndices_;        // Indices of building blocks
    std::vector<RigidTrans3> transforms_; // Transformations for each
    float score_;                       // Overall score
};
```

### BB (Building Block)

Represents a single subunit structure.

```cpp
class BB {
public:
    // Load from PDB file
    void loadFromPDB(const std::string& pdbPath);

    // Get atoms
    const std::vector<Atom>& getAtoms() const;

    // Get backbone atoms for collision detection
    const std::vector<Atom>& getBackboneAtoms() const;

    // Get surface points
    const Surface& getSurface() const;

    // Get collision detection grid
    BBGrid& getGrid();

private:
    std::vector<Atom> atoms_;
    std::vector<Atom> backboneAtoms_;
    Surface surface_;
    BBGrid grid_;
    std::vector<TransformationAndScore> transformations_;
};
```

### BBGrid

Spatial hashing grid for efficient collision detection.

```cpp
class BBGrid {
public:
    // Create grid from atoms
    BBGrid(const std::vector<Atom>& atoms, float resolution);

    // Check collision with another grid
    float checkCollision(const BBGrid& other,
                         const RigidTrans3& transform) const;

    // Get penetration depth
    float getPenetrationDepth(const Vector3& point) const;

private:
    float resolution_;
    std::unordered_map<GridKey, std::vector<Atom*>> grid_;
};
```

### BitId

Efficient bitset-based tracking of subunit combinations.

```cpp
class BitId {
public:
    BitId();
    BitId(int singleIndex);

    // Set operations
    BitId operator|(const BitId& other) const;  // Union
    BitId operator&(const BitId& other) const;  // Intersection

    // Check if two BitIds are compatible (no overlap)
    bool isCompatible(const BitId& other) const;

    // Count set bits
    int count() const;

    // Iterate over set bits
    std::vector<int> getSetBits() const;

private:
    std::bitset<MAX_SUBUNITS> bits_;
};
```

### TransformationAndScore

Stores transformation data from AFM predictions.

```cpp
class TransformationAndScore {
public:
    RigidTrans3 transformation;  // Rigid body transformation
    float score;                  // Interface pLDDT score
    std::string description;      // Source file info

    // Comparison for sorting
    bool operator<(const TransformationAndScore& other) const {
        return score > other.score;  // Higher score = better
    }
};
```

### ComplexDistanceConstraint

Handles crosslink and connectivity constraints.

```cpp
class ComplexDistanceConstraint {
public:
    // Add a crosslink constraint
    void addCrosslink(int res1, char chain1,
                      int res2, char chain2,
                      float minDist, float maxDist,
                      float weight);

    // Add chain connectivity constraint
    void addChainConnectivity(int subunit1, int subunit2);

    // Check constraints for an assembly
    float evaluateConstraints(const SuperBB& assembly) const;

    // Get constraint violation ratio
    float getViolationRatio(const SuperBB& assembly) const;

private:
    std::vector<Crosslink> crosslinks_;
    std::vector<ChainConstraint> chainConstraints_;
};
```

## Hierarchical Assembly Algorithm

### Overview

The algorithm builds the complete complex through progressive assembly:

1. **Initialization**: Each subunit starts as a separate SuperBB
2. **Pair Assembly**: Try all pairs with compatible transformations
3. **Progressive Growth**: Combine successful pairs into larger assemblies
4. **Filtering**: Remove assemblies with too many collisions or constraint violations
5. **Clustering**: Group similar results and keep representatives
6. **Output**: Generate final models

### Pseudo-code

```
HIERARCHICAL_FOLD(subunits, transformations, constraints):
    // Initialize
    superBBs = {new SuperBB(s) for s in subunits}

    // Iterate through assembly sizes
    for stepSize = 2 to len(subunits):
        newSuperBBs = {}

        // Try all compatible pairs
        for sbb1, sbb2 in combinablePairs(superBBs):
            if sbb1.size + sbb2.size != stepSize:
                continue

            // Get compatible transformations
            for trans in getTransformations(sbb1, sbb2):
                // Create candidate assembly
                candidate = combine(sbb1, sbb2, trans)

                // Check collision
                if collisionRatio(candidate) > maxCollision:
                    continue

                // Check penetration
                if penetration(candidate) < penetrationThr:
                    continue

                // Check constraints
                if constraintViolation(candidate) > maxViolation:
                    continue

                // Score and add to candidates
                score = calculateScore(candidate)
                newSuperBBs.add(candidate, score)

        // Keep top K per combination
        superBBs = filterBestK(newSuperBBs, K)

    // Cluster and output
    results = cluster(superBBs, clusterRMSD)
    output(results)
```

### Scoring Function

The assembly score combines multiple factors:

```
score = weightedTransScore + constraintScore

weightedTransScore = sum(interface_pLDDT * transformation_count) / total_transformations

constraintScore = (satisfied_crosslinks / total_crosslinks) * crosslink_weight
```

### Filtering Criteria

| Filter | Default | Description |
|--------|---------|-------------|
| Penetration | -1.0 | Maximum surface penetration depth |
| Backbone Collision | 0.1 (10%) | Max % of backbone atoms in collision |
| Min Temperature | 80 | B-factor threshold for collision |
| Restraints Ratio | 0.1 | Max constraint violation ratio |

## Data Structures

### Transformation File Format

```
rank | score | description | transformation_numbers
1 | 85.2 | 3.2_2.1_A_B_model.pdb | rx ry rz tx ty tz
2 | 82.1 | 2.8_1.9_A_B_model.pdb | rx ry rz tx ty tz
...
```

### Output File Format (output.res)

```
[transformations] key1 value1 key2 value2 ...
[0(rx ry rz tx ty tz),1(rx ry rz tx ty tz),...] weightedTransScore 85.2 numTrans 15
```

### Chain List Format (chain.list)

```
SubunitA_A.pdb
SubunitA_B.pdb 1
SubunitB_C.pdb
```

The optional `1` flag marks subunits in group 1 (for two-group assembly).

## Libraries

### libs_gamb (Geometry and Molecular Building Blocks)

Core mathematical and molecular data structures:

| File | Purpose |
|------|---------|
| `Vector3.h` | 3D vector operations |
| `Matrix3.h` | 3x3 matrix operations |
| `RigidTrans3.h` | Rigid body transformations (rotation + translation) |
| `Atom.h` | Atom representation |
| `Molecule.h` | Collection of atoms |
| `Surface.h` | Molecular surface |
| `MoleculeGrid.h` | Spatial indexing for molecules |
| `GeomHash.h` | Geometric hashing |
| `Match.h` | Structure matching |
| `Parameters.h` | Parameter handling |
| `AminoAcid.h` | Amino acid properties |

### libs_DockingLib (Docking Library)

Chemistry and docking-specific components:

| File | Purpose |
|------|---------|
| `ChemMolecule.cc/h` | Chemical molecule with properties |
| `ChemAtom.h` | Atom with chemical properties |
| `ChemLib.h` | Chemical property database |
| `CrossLink.h` | Crosslink constraint representation |
| `DistanceRestraint.h` | Generic distance restraints |
| `connolly_surface.cc` | Connolly surface calculation |
| `GeomScore.h` | Geometric scoring functions |

### AF2trans

Transform extraction from AlphaFold predictions:

```cpp
// AF2trans.cc
// Input: 4 PDB files
//   - rep1: Representative subunit 1
//   - rep2: Representative subunit 2
//   - sample1: Sample subunit 1 (from AFM)
//   - sample2: Sample subunit 2 (from AFM)
// Output: Rigid transformation between subunits
```

## Build System

### Makefile Structure

```makefile
# Compiler settings
CXX = g++
CXXFLAGS = -std=c++17 -O2 -Wall

# Boost paths (customize if needed)
BOOST_INCLUDE = /usr/include
BOOST_LIB = /usr/lib

# Targets
all: CombinatorialAssembler.out AF2trans.out

CombinatorialAssembler.out: $(OBJS) $(LIBS)
    $(CXX) $(CXXFLAGS) -o $@ $^ -lboost_program_options -lpthread

AF2trans.out: AF2trans/AF2trans.cc $(LIBS)
    $(CXX) $(CXXFLAGS) -o $@ $^ -lboost_program_options

clean:
    rm -f *.o libs_*/*.o

clean_all: clean
    rm -f *.out libs_*/*.a
```

### Build Commands

```bash
# Standard build
make

# Parallel build
make -j4

# Debug build
make CXXFLAGS="-std=c++17 -g -O0 -Wall"

# Clean and rebuild
make clean && make
```

## Command Line Interface

### CombinatorialAssembler.out

```
Usage: <subunitsFileList> <transFilesPrefix> <transNumToRead> <bestK> <constraintsFile>

Options:
  -h [ --help ]                    Help message
  --version                        Version information

  -p [ --penetrationThr ] (=-1.0)  Maximum surface penetration
  -r [ --restraintsRatio ] (=0.1)  Max constraint violation ratio
  -c [ --clusterRMSD ] (=5.0)      Clustering RMSD threshold
  -b [ --maxBackboneCollisionPerChain ] (=0.1)
                                   Max backbone collision %
  -t [ --minTemperatureToConsiderCollision ] (=0)
                                   Min B-factor for collision
  -j [ --maxResultPerResSet ] (=K) Results per combination
  -o [ --outputFileNamePrefix ] (=output)
                                   Output file prefix
```

### AF2trans.out

```
Usage: AF2trans <rep1.pdb> <rep2.pdb> <sample1.pdb> <sample2.pdb>

Output format:
  index | rmsd1_rmsd2_chain1_chain2_filename | rx ry rz tx ty tz
```

## Performance Considerations

### Memory Usage

- Each BB stores coordinates, surfaces, and grids
- SuperBB memory grows with assembly size
- BestK maintains priority queue of top results

### Time Complexity

- Pair enumeration: O(N^2)
- Transformation evaluation: O(T * C) per pair
  - T = number of transformations
  - C = collision checking cost
- Overall: O(N^2 * T * C * K)

### Optimization Strategies

1. **Spatial Hashing**: BBGrid for O(1) collision queries
2. **BitId**: Efficient subunit tracking with bitwise operations
3. **Early Filtering**: Reject bad assemblies quickly
4. **Parallel Processing**: Boost threading for large complexes

---

## See Also

- [Configuration Reference](configuration.md) - All tunable parameters
- [Python API](python-api.md) - Python interface to C++ tools
- [Pipeline Guide](pipeline.md) - How C++ fits in the workflow
