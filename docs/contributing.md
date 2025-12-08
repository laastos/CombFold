# Contributing to CombFold

Thank you for your interest in contributing to CombFold! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributions from everyone and are committed to providing a harassment-free experience.

## Getting Started

### Prerequisites

- Git
- C++ compiler (g++ with C++17 support)
- Python 3.7+
- Boost libraries
- Basic understanding of protein structure prediction

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CombFold.git
   cd CombFold
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/dina-lab3D/CombFold.git
   ```

## How to Contribute

### Types of Contributions

We welcome the following types of contributions:

| Type | Description |
|------|-------------|
| Bug fixes | Fix issues in existing code |
| Features | Add new functionality |
| Documentation | Improve or add documentation |
| Tests | Add or improve test coverage |
| Performance | Optimize existing code |
| Examples | Add usage examples |

### Finding Issues to Work On

- Check [GitHub Issues](https://github.com/dina-lab3D/CombFold/issues)
- Look for issues labeled `good first issue` or `help wanted`
- Feel free to create an issue for discussion before starting major work

## Development Setup

### Setting Up the Development Environment

```bash
# Clone and build
git clone https://github.com/YOUR_USERNAME/CombFold.git
cd CombFold/CombinatorialAssembler
make

# Install Python dependencies
pip install numpy biopython scipy

# Install development dependencies (optional)
pip install pytest black flake8 mypy
```

### Project Structure

```
CombFold/
├── CombinatorialAssembler/   # C++ core engine
│   ├── *.cc, *.h             # Main source files
│   ├── libs_gamb/            # Geometry library
│   ├── libs_DockingLib/      # Docking library
│   └── AF2trans/             # Transform extraction
├── scripts/                   # Python scripts
│   ├── *.py                  # Main scripts
│   └── libs/                 # Python libraries
├── example/                   # Example data
├── docs/                      # Documentation
└── tests/                     # Test files (if present)
```

## Code Style

### Python Code Style

We follow PEP 8 with some modifications:

```python
# Good
def calculate_score(pdb_path: str, chain_id: str) -> float:
    """
    Calculate the interface score for a chain.

    Args:
        pdb_path: Path to the PDB file
        chain_id: Chain identifier

    Returns:
        Interface pLDDT score
    """
    model = get_pdb_model_readonly(pdb_path)
    # ... implementation
    return score


# Type hints are encouraged
def process_subunits(
    subunits_info: SubunitsInfo,
    output_path: str,
    verbose: bool = False
) -> List[str]:
    pass
```

**Key Guidelines:**

- Use type hints
- Write docstrings for public functions
- Keep functions focused and reasonably sized
- Use meaningful variable names

**Formatting:**

```bash
# Format with black
black scripts/

# Check with flake8
flake8 scripts/ --max-line-length=120
```

### C++ Code Style

```cpp
// Class names: PascalCase
class HierarchicalFold {
public:
    // Public methods: camelCase
    void hierarchicalFold(int stepSize);

    // Constants: UPPER_SNAKE_CASE
    static const int MAX_ITERATIONS = 1000;

private:
    // Member variables: camelCase with trailing underscore
    int bestK_;
    std::vector<SuperBB> superBBs_;
};

// Functions: camelCase
float calculateScore(const SuperBB& assembly);

// Namespaces: lowercase
namespace gamb {
    // ...
}
```

**Key Guidelines:**

- Use modern C++ features (C++17)
- Prefer references over pointers when possible
- Use `const` appropriately
- Comment complex algorithms

## Testing

### Running Existing Tests

```bash
# Run on example data
python3 scripts/run_on_pdbs.py example/subunits.json example/pdbs test_output/

# Compare with expected
diff -r test_output/assembled_results example/expected_assembled
```

### Writing Tests

For Python code:

```python
# tests/test_utils_classes.py
import pytest
from scripts.libs.utils_classes import SubunitInfo, read_subunits_info

def test_subunit_info_creation():
    info = SubunitInfo(
        name="TestSubunit",
        chain_names=["A", "B"],
        start_res=1,
        sequence="MKDILEKLEERRAQARLGGG"
    )
    assert info.name == "TestSubunit"
    assert len(info.chain_names) == 2
    assert info.get_end_res() == 20

def test_read_subunits_info():
    info = read_subunits_info("example/subunits.json")
    assert "A0" in info
    assert "G0" in info
```

### Test Coverage Goals

- Unit tests for utility functions
- Integration tests for main pipeline
- Validation against expected outputs

## Submitting Changes

### Branch Naming

```
feature/add-new-scoring-function
bugfix/fix-memory-leak
docs/improve-installation-guide
```

### Commit Messages

Follow conventional commit format:

```
type(scope): short description

Longer description if needed.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `perf`: Performance improvement

Examples:

```
feat(assembly): add support for flexible linkers

fix(python): handle empty PDB files gracefully

docs: add troubleshooting section for memory issues
```

### Pull Request Process

1. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat: description of changes"
   ```

3. **Keep branch updated:**
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

4. **Push and create PR:**
   ```bash
   git push origin feature/your-feature
   ```

5. **In GitHub:**
   - Create Pull Request
   - Fill in the PR template
   - Link related issues
   - Request review

### PR Checklist

- [ ] Code compiles without warnings
- [ ] Tests pass
- [ ] Documentation updated (if needed)
- [ ] Code follows style guidelines
- [ ] Commit messages are clear
- [ ] PR description explains changes

## Reporting Issues

### Bug Reports

Include:

1. **Description**: What happened vs. what you expected
2. **Steps to reproduce**: Minimal example
3. **Environment**:
   ```
   OS: Ubuntu 22.04
   Python: 3.10.4
   g++: 11.3.0
   ```
4. **Error message**: Complete traceback
5. **Input files**: If relevant (or minimal example)

### Feature Requests

Include:

1. **Use case**: Why is this needed?
2. **Proposed solution**: How would it work?
3. **Alternatives**: What else was considered?
4. **Additional context**: Examples, references

### Issue Template

```markdown
## Description
[Clear description of the issue]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [...]

## Expected Behavior
[What you expected to happen]

## Actual Behavior
[What actually happened]

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.4]
- CombFold version/commit: [e.g., abc1234]

## Additional Context
[Any other information]
```

## Development Tips

### Debugging C++

```bash
# Build with debug symbols
make CXXFLAGS="-std=c++17 -g -O0 -Wall"

# Run with debugger
gdb ./CombinatorialAssembler.out
```

### Debugging Python

```python
import pdb; pdb.set_trace()  # Add breakpoint

# Or use debugger
python3 -m pdb scripts/run_on_pdbs.py ...
```

### Performance Profiling

```bash
# C++ profiling
perf record ./CombinatorialAssembler.out ...
perf report

# Python profiling
python3 -m cProfile -o output.prof scripts/run_on_pdbs.py ...
```

## Community

### Communication Channels

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and discussions

### Getting Help

- Check existing documentation
- Search closed issues
- Ask in GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

## Quick Reference

### Commands

```bash
# Setup
git clone https://github.com/YOUR_USERNAME/CombFold.git
cd CombFold/CombinatorialAssembler && make

# Development
git checkout -b feature/my-feature
# ... make changes ...
black scripts/  # Format Python
make clean && make  # Rebuild C++

# Testing
python3 scripts/run_on_pdbs.py example/subunits.json example/pdbs test_output/

# Submit
git add . && git commit -m "feat: description"
git push origin feature/my-feature
```

### Checklist

- [ ] Fork and clone repository
- [ ] Set up development environment
- [ ] Create feature branch
- [ ] Make changes following style guide
- [ ] Test changes
- [ ] Update documentation
- [ ] Submit PR

Thank you for contributing to CombFold!
