# ===============================================================
# CombFold + ColabFold Docker Image (Python 3.10 + CUDA)
# ===============================================================
# Uses NVIDIA CUDA base image with Python 3.10 for ColabFold compatibility
# ColabFold requires Python <3.12, NGC JAX container has Python 3.12+
#
# Build: docker build -t combfold:latest .
# Run:   docker run --gpus all --ipc=host -it combfold:latest
#
FROM nvidia/cuda:12.4.0-cudnn-devel-ubuntu22.04

LABEL maintainer="CombFold Team"
LABEL description="CombFold + ColabFold for large protein complex structure prediction (Blackwell GPU support)"
LABEL version="2.0"

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ===============================================================
# 1. Install system dependencies and Python 3.10
# ===============================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    build-essential \
    g++ \
    libboost-all-dev \
    ca-certificates \
    software-properties-common \
    # Python 3.10
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    # Tools needed by ColabFold
    kalign \
    hmmer \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install MMseqs2 from GitHub releases (latest version)
RUN wget -q https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz && \
    tar xzf mmseqs-linux-avx2.tar.gz && \
    mv mmseqs/bin/mmseqs /usr/local/bin/ && \
    rm -rf mmseqs mmseqs-linux-avx2.tar.gz

# ===============================================================
# 2. Install JAX with CUDA support
# ===============================================================
# Install JAX 0.4.23 with CUDA 12 support (compatible with ColabFold)
RUN pip install --no-cache-dir \
    "jax[cuda12_pip]==0.4.23" \
    -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

# Verify JAX installation
RUN python3 -c "import jax; print('JAX version:', jax.__version__)"

# ===============================================================
# 3. Install ColabFold and dependencies
# ===============================================================
RUN pip install --no-cache-dir \
    "colabfold[alphafold]==1.5.5" \
    dm-haiku==0.0.12 \
    biopython \
    scipy \
    pandas \
    matplotlib \
    py3Dmol \
    tqdm \
    appdirs \
    absl-py

# Install OpenMM for structure relaxation (optional but recommended)
RUN pip install --no-cache-dir openmm pdbfixer

# ===============================================================
# 3. Set environment variables for JAX/CUDA
# ===============================================================
ENV XLA_PYTHON_CLIENT_MEM_FRACTION=0.8
ENV XLA_PYTHON_CLIENT_PREALLOCATE=false
ENV XLA_FLAGS="--xla_gpu_cuda_data_dir=/usr/local/cuda"
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV TF_CPP_MIN_LOG_LEVEL=2

# ColabFold cache directories
ENV MPLBACKEND=Agg
ENV MPLCONFIGDIR=/cache
ENV XDG_CACHE_HOME=/cache

# ===============================================================
# 4. Copy and build CombFold
# ===============================================================
WORKDIR /app

# Copy CombFold source code
COPY CombinatorialAssembler/ /app/CombinatorialAssembler/
COPY scripts/ /app/scripts/
COPY example/ /app/example/

# Build CombFold C++ components
# Fix Makefile for Linux paths
RUN cd /app/CombinatorialAssembler && \
    sed -i 's|BOOST_INCLUDE = /opt/homebrew/include|BOOST_INCLUDE = /usr/include|g' Makefile && \
    sed -i 's|BOOST_LIB = /opt/homebrew/lib/|BOOST_LIB = /usr/lib/x86_64-linux-gnu|g' Makefile && \
    make clean_all || true && \
    make

# Verify binaries exist
RUN ls -la /app/CombinatorialAssembler/CombinatorialAssembler.out && \
    ls -la /app/CombinatorialAssembler/AF2trans.out

# ===============================================================
# 5. Setup directories and environment
# ===============================================================
RUN mkdir -p /data/input /data/output /data/pdbs /cache

# Set environment variables
ENV COMBFOLD_HOME=/app
ENV PATH="${COMBFOLD_HOME}/CombinatorialAssembler:${PATH}"

# ===============================================================
# 6. Copy helper scripts
# ===============================================================
COPY docker/scripts/ /app/docker/scripts/
RUN chmod +x /app/docker/scripts/*.sh 2>/dev/null || true

# Verify ColabFold and JAX GPU support
RUN python3 -c "import jax; print('Final JAX devices:', jax.devices())" && \
    python3 -c "from colabfold.batch import run; print('ColabFold imported successfully')" || \
    echo "ColabFold import check (may need GPU at runtime)"

# Create volumes for persistent data
VOLUME ["/cache", "/data"]

# Default working directory for user data
WORKDIR /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import numpy; import Bio; import scipy; print('OK')" || exit 1

# ===============================================================
# 7. Default entrypoint
# ===============================================================
CMD ["bash", "-c", "echo 'CombFold + ColabFold Docker Container (Blackwell GPU)'; echo ''; echo 'GPU Status:'; python3 -c \"import jax; print('JAX devices:', jax.devices())\"; echo ''; echo 'Usage:'; echo '  colabfold_batch <input.fasta> <output_dir> - Run AFM predictions'; echo '  python3 /app/scripts/run_on_pdbs.py - Run CombFold assembly'; echo ''; echo 'See /app/docs/ for documentation'"]
