#!/bin/bash
# SMA-seq Custom Barcode Demultiplexing
# Runs three separate Dorado demux passes for different barcode lengths

set -e
cd /data2/repos/ont-ecosystem/sma_db/exp_12282025_IF

INPUT_DIR="/data1/12282025_IF_DoubleBC_SMA_seq_no_trim/no_sample_id"
OUTPUT_DIR="demux_output"

echo "=============================================="
echo "SMA-seq Custom Barcode Demultiplexing"
echo "=============================================="

# Find all BAM files
BAM_FILES=$(find "$INPUT_DIR" -name "*.bam" -path "*/bam_pass/*" | head -20)
echo "Found BAM files to process"

# Create output directories
mkdir -p "$OUTPUT_DIR/24bp" "$OUTPUT_DIR/23bp" "$OUTPUT_DIR/22bp"

echo ""
echo "Pass 1: 24bp barcodes (BC02, BC09)..."
for bam in $BAM_FILES; do
    dorado demux \
      --kit-name SMA_24bp \
      --barcode-arrangement config/SMA_24bp.toml \
      --barcode-sequences config/SMA_24bp_sequences.fasta \
      --output-dir "$OUTPUT_DIR/24bp" \
      --no-trim \
      "$bam" 2>/dev/null
done
echo "  Done"

echo ""
echo "Pass 2: 23bp barcodes (BC04)..."
for bam in $BAM_FILES; do
    dorado demux \
      --kit-name SMA_23bp \
      --barcode-arrangement config/SMA_23bp.toml \
      --barcode-sequences config/SMA_23bp_sequences.fasta \
      --output-dir "$OUTPUT_DIR/23bp" \
      --no-trim \
      "$bam" 2>/dev/null
done
echo "  Done"

echo ""
echo "Pass 3: 22bp barcodes (BC07)..."
for bam in $BAM_FILES; do
    dorado demux \
      --kit-name SMA_22bp \
      --barcode-arrangement config/SMA_22bp.toml \
      --barcode-sequences config/SMA_22bp_sequences.fasta \
      --output-dir "$OUTPUT_DIR/22bp" \
      --no-trim \
      "$bam" 2>/dev/null
done
echo "  Done"

echo ""
echo "=============================================="
echo "Output summary:"
echo "=============================================="
echo "24bp barcodes (BC02, BC09):"
ls -la "$OUTPUT_DIR/24bp/"*.bam 2>/dev/null | grep -v unclassified || echo "  (none)"
echo ""
echo "23bp barcodes (BC04):"
ls -la "$OUTPUT_DIR/23bp/"*.bam 2>/dev/null | grep -v unclassified || echo "  (none)"
echo ""
echo "22bp barcodes (BC07):"
ls -la "$OUTPUT_DIR/22bp/"*.bam 2>/dev/null | grep -v unclassified || echo "  (none)"
