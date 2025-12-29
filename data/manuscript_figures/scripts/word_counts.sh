#!/bin/bash
# Generate word counts for all manuscript versions
# Usage: ./word_counts.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Manuscript Word Counts"
echo "=========================================="

cd "$BASE_DIR"

# Function to count words in PDF
count_pdf_words() {
    local pdf=$1
    if [ -f "$pdf" ]; then
        words=$(pdftotext "$pdf" - 2>/dev/null | wc -w)
        pages=$(pdfinfo "$pdf" 2>/dev/null | grep Pages | awk '{print $2}')
        printf "  %-40s %6d words (%2d pages)\n" "$pdf" "$words" "$pages"
    fi
}

# Function to count words in text file
count_text_words() {
    local txt=$1
    if [ -f "$txt" ]; then
        words=$(wc -w < "$txt")
        printf "  %-40s %6d words\n" "$txt" "$words"
    fi
}

echo ""
echo "Main Manuscript Sections (text files):"
echo "------------------------------------------"
for f in abstract_registry.txt introduction_registry.txt methods_registry.txt results_registry.txt discussion_registry.txt; do
    count_text_words "$f"
done

echo ""
total_text=$(cat abstract_registry.txt introduction_registry.txt methods_registry.txt results_registry.txt discussion_registry.txt 2>/dev/null | wc -w)
echo "  TOTAL (main text):                        $total_text words"

echo ""
echo "Compiled PDFs:"
echo "------------------------------------------"
count_pdf_words "main_manuscript.pdf"
count_pdf_words "supplementary_materials.pdf"
count_pdf_words "scientific_data/main_sdata.pdf"
count_pdf_words "biorxiv/main_biorxiv.pdf"

echo ""
echo "Figures and Tables:"
echo "------------------------------------------"
fig_count=$(ls -1 fig_*.pdf 2>/dev/null | wc -l)
tbl_count=$(ls -1 tbl_*.tex 2>/dev/null | wc -l)
echo "  Main figures:     $fig_count"
echo "  Main tables:      $tbl_count"

echo ""
echo "References:"
echo "------------------------------------------"
for bib in references_registry.bib scientific_data/references_sdata.bib biorxiv/references_biorxiv.bib; do
    if [ -f "$bib" ]; then
        refs=$(grep -c "@" "$bib" 2>/dev/null || echo 0)
        printf "  %-40s %6d references\n" "$bib" "$refs"
    fi
done

echo ""
echo "=========================================="
