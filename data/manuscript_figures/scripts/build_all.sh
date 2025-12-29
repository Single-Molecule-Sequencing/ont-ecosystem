#!/bin/bash
# Build all manuscript versions
# Usage: ./build_all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Building all manuscript versions"
echo "=========================================="

# Function to compile LaTeX
compile_latex() {
    local dir=$1
    local file=$2
    local name="${file%.tex}"

    echo ""
    echo "Building: $dir/$file"
    echo "------------------------------------------"

    cd "$BASE_DIR/$dir"

    # First pass
    pdflatex -interaction=nonstopmode "$file" > /dev/null 2>&1

    # BibTeX if .bib exists
    if ls *.bib 1> /dev/null 2>&1; then
        bibtex "$name" > /dev/null 2>&1 || true
        pdflatex -interaction=nonstopmode "$file" > /dev/null 2>&1
    fi

    # Final pass
    pdflatex -interaction=nonstopmode "$file" > /dev/null 2>&1

    # Cleanup
    rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot 2>/dev/null || true

    # Report
    if [ -f "${name}.pdf" ]; then
        pages=$(pdfinfo "${name}.pdf" 2>/dev/null | grep Pages | awk '{print $2}')
        size=$(ls -lh "${name}.pdf" | awk '{print $5}')
        echo "  ✓ ${name}.pdf ($pages pages, $size)"
    else
        echo "  ✗ Failed to create ${name}.pdf"
        return 1
    fi
}

# Build main manuscript
compile_latex "." "main_manuscript.tex"

# Build supplementary materials
compile_latex "." "supplementary_materials.tex"

# Build cover letter
compile_latex "." "cover_letter.tex"

# Build Scientific Data version
compile_latex "scientific_data" "main_sdata.tex"
compile_latex "scientific_data" "cover_letter_sdata.tex"

# Build bioRxiv version
compile_latex "biorxiv" "main_biorxiv.tex"

echo ""
echo "=========================================="
echo "Build Summary"
echo "=========================================="

cd "$BASE_DIR"

echo ""
echo "Main manuscripts:"
ls -lh main_manuscript.pdf supplementary_materials.pdf 2>/dev/null | awk '{print "  "$NF": "$5}'

echo ""
echo "Scientific Data:"
ls -lh scientific_data/*.pdf 2>/dev/null | awk '{print "  "$NF": "$5}'

echo ""
echo "bioRxiv:"
ls -lh biorxiv/*.pdf 2>/dev/null | awk '{print "  "$NF": "$5}'

echo ""
echo "Cover letters:"
ls -lh cover_letter.pdf scientific_data/cover_letter_sdata.pdf 2>/dev/null | awk '{print "  "$NF": "$5}'

echo ""
echo "Build complete!"
