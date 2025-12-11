# ===============================================================
# CombFold + LocalColabFold Docker Image (NGC JAX with Blackwell Support)
# ===============================================================
# Uses NVIDIA NGC JAX 25.01 container with native Blackwell (CC 12.0) support
# Combines CombFold combinatorial assembly with ColabFold for AFM predictions
#
# Build: docker build -t combfold:latest .
# Run:   docker run --gpus all --ipc=host -it combfold:latest
#
FROM nvcr.io/nvidia/jax:25.01-py3

LABEL maintainer="CombFold Team"
LABEL description="CombFold + LocalColabFold for large protein complex structure prediction (Blackwell GPU support)"
LABEL version="1.0"

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ===============================================================
# 1. Install system dependencies
# ===============================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    build-essential \
    g++ \
    libboost-all-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ===============================================================
# 2. Install ColabFold and dependencies
# ===============================================================
# Install Miniforge (formerly Mambaforge) for ColabFold environment management
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh && \
    bash Miniforge3-Linux-x86_64.sh -bfp /opt/conda && \
    rm -f Miniforge3-Linux-x86_64.sh

# Create ColabFold environment
# Note: We use a separate conda env to avoid conflicts with NGC's JAX
# Pin JAX/Haiku versions for compatibility with ColabFold 1.5.5
ENV PATH="/opt/conda/bin:${PATH}"
RUN mamba create -y -n colabfold python=3.10 && \
    mamba install -y -n colabfold -c conda-forge -c bioconda \
    colabfold=1.5.5 \
    openmm \
    pdbfixer \
    kalign2 \
    hhsuite \
    mmseqs2 \
    && mamba clean -afy

# Fix JAX/Haiku version compatibility for ColabFold with CUDA support
# ColabFold 1.5.5 requires specific JAX/Haiku versions
# Use JAX 0.4.23 with explicit CUDA 12 jaxlib wheel
RUN /opt/conda/envs/colabfold/bin/pip uninstall -y jax jaxlib dm-haiku 2>/dev/null || true && \
    /opt/conda/envs/colabfold/bin/pip install --no-cache-dir \
    jax==0.4.23 \
    https://storage.googleapis.com/jax-releases/cuda12/jaxlib-0.4.23+cuda12.cudnn89-cp310-cp310-manylinux2014_x86_64.whl \
    dm-haiku==0.0.12

# Verify JAX installation
RUN /opt/conda/envs/colabfold/bin/python -c "import jax; print('JAX version:', jax.__version__)"

# Set CUDA/JAX environment for ColabFold
# Disable memory preallocation to avoid OOM on large predictions
ENV XLA_PYTHON_CLIENT_MEM_FRACTION=0.8
ENV XLA_PYTHON_CLIENT_PREALLOCATE=false
# Point to NGC container's CUDA installation
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"
ENV CUDA_DIR=/usr/local/cuda
ENV XLA_FLAGS="--xla_gpu_cuda_data_dir=/usr/local/cuda"

# Set up ColabFold environment paths
ENV COLABFOLD_ENV="/opt/conda/envs/colabfold"
ENV MPLBACKEND=Agg
ENV MPLCONFIGDIR=/cache
ENV XDG_CACHE_HOME=/cache

# ===============================================================
# 3. Install Python dependencies for CombFold (in NGC base Python)
# ===============================================================
RUN pip install --no-cache-dir \
    numpy \
    biopython \
    scipy

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

# TensorFlow environment variables (for GPU memory management)
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV TF_CPP_MIN_LOG_LEVEL=2

# ===============================================================
# 6. Copy helper scripts
# ===============================================================
COPY docker/scripts/ /app/docker/scripts/
RUN chmod +x /app/docker/scripts/*.sh 2>/dev/null || true

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
CMD ["bash", "-c", "echo 'CombFold + LocalColabFold Docker Container (Blackwell GPU)'; echo ''; echo 'Usage:'; echo '  source /opt/conda/etc/profile.d/conda.sh && conda activate colabfold'; echo '  colabfold_batch <input.fasta> <output_dir> - Run AFM predictions'; echo '  python3 /app/scripts/run_on_pdbs.py - Run CombFold assembly'; echo ''; echo 'See /app/docs/ for documentation'"]
