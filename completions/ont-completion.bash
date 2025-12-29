# Bash completion for ONT Ecosystem CLI tools
# Source this file: source ont-completion.bash
# Or add to ~/.bashrc: source /path/to/ont-ecosystem/completions/ont-completion.bash

# ont_experiments.py completion
_ont_experiments() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="init discover register list info run history export replay tag status public fetch remove tasks progress init-tasks next math stages stage validate"

    case "${prev}" in
        ont_experiments.py|ont-experiments)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            return 0
            ;;
        run)
            local analyses="end_reasons basecalling alignment monitoring signal_qc"
            COMPREPLY=( $(compgen -W "${analyses}" -- ${cur}) )
            return 0
            ;;
        --format)
            COMPREPLY=( $(compgen -W "json yaml csv" -- ${cur}) )
            return 0
            ;;
        --model)
            local models="fast hac sup fast@v5.0.0 hac@v5.0.0 sup@v5.0.0"
            COMPREPLY=( $(compgen -W "${models}" -- ${cur}) )
            return 0
            ;;
    esac

    if [[ ${cur} == -* ]]; then
        local opts="--help --json --verbose --force --dry-run"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _ont_experiments ont_experiments.py
complete -F _ont_experiments ont-experiments

# ont_manuscript.py completion
_ont_manuscript() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="select pipeline figure table export compare list-pipelines list-figures list-tables artifacts"

    case "${prev}" in
        ont_manuscript.py|ont-manuscript)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            return 0
            ;;
        pipeline)
            local pipelines="qc-report full-analysis comparison summary-only"
            COMPREPLY=( $(compgen -W "${pipelines}" -- ${cur}) )
            return 0
            ;;
        figure)
            local figures="fig_end_reason_kde fig_end_reason_pie fig_quality_dist fig_read_length fig_yield_timeline fig_n50_barplot fig_metrics_heatmap fig_comparison fig_coverage fig_alignment_stats"
            COMPREPLY=( $(compgen -W "${figures}" -- ${cur}) )
            return 0
            ;;
        table)
            local tables="tbl_qc_summary tbl_basecalling tbl_alignment tbl_comparison tbl_experiment_summary"
            COMPREPLY=( $(compgen -W "${tables}" -- ${cur}) )
            return 0
            ;;
        --format)
            COMPREPLY=( $(compgen -W "pdf png tex csv json html" -- ${cur}) )
            return 0
            ;;
        --target)
            COMPREPLY=( $(compgen -W "latex html" -- ${cur}) )
            return 0
            ;;
    esac

    if [[ ${cur} == -* ]]; then
        local opts="--help --format --target --output"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _ont_manuscript ont_manuscript.py
complete -F _ont_manuscript ont-manuscript

# ont_context.py completion
_ont_context() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="show list equations compute"

    case "${prev}" in
        ont_context.py|ont-context)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            return 0
            ;;
        equations)
            COMPREPLY=( $(compgen -W "--computable --stage --chapter" -- ${cur}) )
            return 0
            ;;
    esac

    if [[ ${cur} == -* ]]; then
        local opts="--help --json --computable"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _ont_context ont_context.py
complete -F _ont_context ont-context

# ont_stats.py completion
_ont_stats() {
    local cur
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"

    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "--help --json --brief" -- ${cur}) )
        return 0
    fi
}
complete -F _ont_stats ont_stats.py
complete -F _ont_stats ont-stats

# make completion for ont-ecosystem targets
_ont_make() {
    local cur targets
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"

    targets="help install install-dev test test-quick test-coverage lint validate validate-skills validate-registry validate-equations pre-commit pre-commit-install package clean dashboard list-figures list-tables list-pipes version"

    COMPREPLY=( $(compgen -W "${targets}" -- ${cur}) )
}
complete -F _ont_make make

echo "ONT Ecosystem shell completion loaded"
