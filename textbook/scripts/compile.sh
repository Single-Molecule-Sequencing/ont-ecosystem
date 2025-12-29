#!/bin/bash
# SMS Haplotype Framework - Three-Pass Compilation Script
# =========================================================

echo ""
echo "========================================================"
echo " SMS Haplotype Classification Framework"
echo " Three-Pass PDF Compilation"
echo "========================================================"
echo ""

COMPILER=pdflatex
MAINFILE=haplotype_v6_complete_FIXED.tex
OUTPUTNAME=SMS_Haplotype_Framework_Textbook

# Check if compiler exists
if ! command -v $COMPILER &> /dev/null; then
    echo "ERROR: pdflatex not found!"
    echo "Please install TeX Live or MacTeX."
    exit 1
fi

# Check if main file exists
if [ ! -f "$MAINFILE" ]; then
    echo "ERROR: Main LaTeX file not found: $MAINFILE"
    exit 1
fi

echo "Starting compilation..."
echo ""

# Remove old PDF to ensure we detect compilation failure
if [ -f "${OUTPUTNAME}.pdf" ]; then
    echo "Removing old PDF file..."
    rm -f "${OUTPUTNAME}.pdf"
fi
echo ""

echo "--------------------------------------------------------"
echo "PASS 1 of 3: Initial compilation"
echo "--------------------------------------------------------"
$COMPILER -interaction=nonstopmode -jobname=$OUTPUTNAME $MAINFILE
PASS1_EXIT=$?
if [ $PASS1_EXIT -ne 0 ]; then
    echo "WARNING: Pass 1 completed with errors. Check log file."
else
    echo "Pass 1 complete."
fi
echo ""

echo "--------------------------------------------------------"
echo "Running BibTeX for bibliography processing"
echo "--------------------------------------------------------"
bibtex $OUTPUTNAME
BIBTEX_EXIT=$?
if [ $BIBTEX_EXIT -ne 0 ]; then
    echo "WARNING: BibTeX returned non-zero status. Check .blg file."
else
    echo "BibTeX complete."
fi
echo ""

echo "--------------------------------------------------------"
echo "PASS 2 of 3: Resolving cross-references"
echo "--------------------------------------------------------"
$COMPILER -interaction=nonstopmode -jobname=$OUTPUTNAME $MAINFILE
PASS2_EXIT=$?
if [ $PASS2_EXIT -ne 0 ]; then
    echo "WARNING: Pass 2 completed with errors. Check log file."
else
    echo "Pass 2 complete."
fi
echo ""

echo "--------------------------------------------------------"
echo "PASS 3 of 3: Finalizing hyperlinks"
echo "--------------------------------------------------------"
$COMPILER -interaction=nonstopmode -jobname=$OUTPUTNAME $MAINFILE
PASS3_EXIT=$?
if [ $PASS3_EXIT -ne 0 ]; then
    echo "WARNING: Pass 3 completed with warnings/errors. Check log file."
else
    echo "Pass 3 complete."
fi
echo ""

# Check if PDF was created
if [ -f "${OUTPUTNAME}.pdf" ]; then
    # Check for fatal LaTeX errors in the log
    if grep -E -q "(! LaTeX Error:|Emergency stop\.)" "${OUTPUTNAME}.log"; then
        echo "========================================================"
        echo " COMPILATION FAILED!"
        echo "========================================================"
        echo ""
        echo "Fatal LaTeX error detected in compilation."
        echo "Check ${OUTPUTNAME}.log for details."
        echo ""
        echo "Last 50 lines of log file:"
        tail -50 "${OUTPUTNAME}.log"
        exit 1
    fi
    
    echo "========================================================"
    echo " COMPILATION SUCCESSFUL!"
    echo "========================================================"
    echo ""
    echo "Output PDF: ${OUTPUTNAME}.pdf"

    # Get file size
    if [ -f "${OUTPUTNAME}.pdf" ]; then
        FILE_SIZE=$(du -h "${OUTPUTNAME}.pdf" | cut -f1)
        echo "File Size: ${FILE_SIZE}"
    fi

    # Report on warnings
    echo ""
    if grep -q "LaTeX Warning:" "${OUTPUTNAME}.log"; then
        echo "Note: Warnings present during compilation. Review ${OUTPUTNAME}.log if needed."
    fi

    echo ""
    echo "Opening PDF viewer..."

    # Open PDF based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "${OUTPUTNAME}.pdf"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open "${OUTPUTNAME}.pdf" &
    fi
else
    echo "========================================================"
    echo " COMPILATION FAILED!"
    echo "========================================================"
    echo ""
    echo "PDF file was not created. Check ${OUTPUTNAME}.log for errors."
    exit 1
fi

echo ""
