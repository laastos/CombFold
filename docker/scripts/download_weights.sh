#!/bin/bash
# Download ColabFold model weights and optionally MMseqs2 databases
# Run this once after building the container

set -e

# Default paths
CACHE_DIR="${XDG_CACHE_HOME:-/cache}"
WEIGHTS_DIR="$CACHE_DIR/colabfold"
DB_DIR="$CACHE_DIR/colabfold_db"

# Parse arguments
DOWNLOAD_DB=false
DB_TYPE="full"  # full, light, or uniref_only

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --weights-only     Download only model weights (~5GB) [default]"
    echo "  --with-db          Download weights + MMseqs2 databases (~2TB)"
    echo "  --db-only          Download only MMseqs2 databases"
    echo "  --db-light         Download lightweight databases (~500GB)"
    echo "  --db-uniref        Download only UniRef30 (~100GB)"
    echo "  --db-dir PATH      Database directory (default: $DB_DIR)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Database sizes (approximate):"
    echo "  Full:     UniRef30 + ColabFoldDB (~2TB uncompressed)"
    echo "  Light:    UniRef30 + PDB70 (~500GB)"
    echo "  UniRef:   UniRef30 only (~100GB compressed, ~400GB uncompressed)"
    exit 0
}

SKIP_WEIGHTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --weights-only)
            DOWNLOAD_DB=false
            shift
            ;;
        --with-db)
            DOWNLOAD_DB=true
            DB_TYPE="full"
            shift
            ;;
        --db-only)
            DOWNLOAD_DB=true
            SKIP_WEIGHTS=true
            shift
            ;;
        --db-light)
            DOWNLOAD_DB=true
            DB_TYPE="light"
            shift
            ;;
        --db-uniref)
            DOWNLOAD_DB=true
            DB_TYPE="uniref_only"
            shift
            ;;
        --db-dir)
            DB_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo "=========================================="
echo "CombFold Data Download Script"
echo "=========================================="
echo ""

# Download model weights
if [ "$SKIP_WEIGHTS" = false ]; then
    echo "=== Downloading ColabFold/AlphaFold2 weights ==="
    echo ""
    echo "This will download approximately 5GB of model weights."
    echo "Weights will be cached in $WEIGHTS_DIR"
    echo ""

    # ColabFold is installed via pip, just run download
    python -m colabfold.download

    echo ""
    echo "Model weights download complete!"
    echo ""
fi

# Download MMseqs2 databases
if [ "$DOWNLOAD_DB" = true ]; then
    echo "=========================================="
    echo "=== Downloading MMseqs2 Databases ==="
    echo "=========================================="
    echo ""
    echo "Database type: $DB_TYPE"
    echo "Database directory: $DB_DIR"
    echo ""

    mkdir -p "$DB_DIR"
    cd "$DB_DIR"

    case $DB_TYPE in
        full)
            echo "Downloading full databases (UniRef30 + ColabFoldDB)"
            echo "WARNING: This requires ~2TB of disk space!"
            echo ""

            # Check disk space
            AVAILABLE=$(df -BG "$DB_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
            if [ "$AVAILABLE" -lt 2200 ]; then
                echo "WARNING: Only ${AVAILABLE}GB available, recommended 2200GB+"
                echo "Continue anyway? (y/N)"
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    echo "Aborted."
                    exit 1
                fi
            fi

            # Download UniRef30
            echo ""
            echo "--- Downloading UniRef30 (2024_02) ---"
            if [ ! -f "uniref30_2302_db.idx" ]; then
                wget -c https://wwwuser.gwdg.de/~compbiol/colabfold/uniref30_2302.tar.gz
                tar xzf uniref30_2302.tar.gz
                rm -f uniref30_2302.tar.gz
            else
                echo "UniRef30 already exists, skipping."
            fi

            # Download ColabFoldDB (environmental sequences)
            echo ""
            echo "--- Downloading ColabFoldDB ---"
            if [ ! -f "colabfold_envdb_202108_db.idx" ]; then
                wget -c https://wwwuser.gwdg.de/~compbiol/colabfold/colabfold_envdb_202108.tar.gz
                tar xzf colabfold_envdb_202108.tar.gz
                rm -f colabfold_envdb_202108.tar.gz
            else
                echo "ColabFoldDB already exists, skipping."
            fi
            ;;

        light)
            echo "Downloading light databases (UniRef30 + PDB70)"
            echo "This requires ~500GB of disk space."
            echo ""

            # Download UniRef30
            echo "--- Downloading UniRef30 ---"
            if [ ! -f "uniref30_2302_db.idx" ]; then
                wget -c https://wwwuser.gwdg.de/~compbiol/colabfold/uniref30_2302.tar.gz
                tar xzf uniref30_2302.tar.gz
                rm -f uniref30_2302.tar.gz
            else
                echo "UniRef30 already exists, skipping."
            fi

            # Download PDB70
            echo ""
            echo "--- Downloading PDB70 ---"
            if [ ! -f "pdb70_220313_db.idx" ]; then
                wget -c https://wwwuser.gwdg.de/~compbiol/colabfold/pdb70_220313.tar.gz
                tar xzf pdb70_220313.tar.gz
                rm -f pdb70_220313.tar.gz
            else
                echo "PDB70 already exists, skipping."
            fi
            ;;

        uniref_only)
            echo "Downloading UniRef30 only"
            echo "This requires ~100GB compressed, ~400GB uncompressed."
            echo ""

            if [ ! -f "uniref30_2302_db.idx" ]; then
                wget -c https://wwwuser.gwdg.de/~compbiol/colabfold/uniref30_2302.tar.gz
                tar xzf uniref30_2302.tar.gz
                rm -f uniref30_2302.tar.gz
            else
                echo "UniRef30 already exists, skipping."
            fi
            ;;
    esac

    echo ""
    echo "MMseqs2 database download complete!"
    echo "Database location: $DB_DIR"
    echo ""
    echo "To use local databases, run colabfold_search first:"
    echo "  colabfold_search input.fasta $DB_DIR output/"
    echo ""
    echo "Or set environment variable:"
    echo "  export COLABFOLD_DB=$DB_DIR"
fi

echo "=========================================="
echo "Download complete!"
echo "=========================================="
echo ""

if [ "$DOWNLOAD_DB" = true ]; then
    echo "Database contents:"
    ls -lh "$DB_DIR"/*.idx 2>/dev/null || echo "  (no index files found)"
    echo ""
    echo "Total database size:"
    du -sh "$DB_DIR"
fi
