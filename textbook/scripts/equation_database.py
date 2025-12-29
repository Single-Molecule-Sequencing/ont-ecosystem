#!/usr/bin/env python3
"""
Equation and Variable Database Management System
Version 1.0

Manages storage, retrieval, and organization of all equations and variables
in the SMS Textbook.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import re

@dataclass
class Equation:
    """Represents a single equation in the textbook"""
    id: str  # e.g., "5.1"
    chapter: int
    index: int
    title: str
    latex: str
    latex_full: str
    type: str  # equation, inequality, identity, definition
    category: str  # fundamental, derived, computational, empirical
    description: str
    physical_meaning: str
    assumptions: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    related_equations: List[str] = field(default_factory=list)
    appears_in: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    interactive: Dict[str, Any] = field(default_factory=dict)
    proof_sketch: str = ""
    importance: str = "normal"  # critical, high, normal, low
    difficulty: str = "intermediate"  # beginner, intermediate, advanced
    tags: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Generate LaTeX label for this equation"""
        # Extract from latex_full if present
        match = re.search(r'\\label\{([^}]+)\}', self.latex_full)
        if match:
            return match.group(1)
        # Generate default label
        clean_title = re.sub(r'[^a-z0-9]+', '-', self.title.lower()).strip('-')
        return f"eq:{clean_title}"

    def to_latex_eqbox(self, include_interactive: bool = False) -> str:
        """Generate enhanced LaTeX eqbox code"""
        lines = []

        lines.append(f"\\begin{{eqbox}}{{{self.title}}}")
        lines.append(f"\\begin{{equation}}")
        lines.append(self.latex)
        lines.append(f"\\label{{{self.label}}}")
        lines.append(f"\\end{{equation}}")

        # Add description if present
        if self.description:
            lines.append(f"\\vspace{{6pt}}")
            lines.append(f"\\textit{{{self.description}}}")

        lines.append(f"\\end{{eqbox}}")

        return "\n".join(lines)

    def to_html_card(self) -> str:
        """Generate HTML card for interactive display"""
        return f"""
<div class="equation-card" data-eq-id="{self.id}">
    <div class="eq-header">
        <span class="eq-number">Equation {self.id}</span>
        <span class="eq-title">{self.title}</span>
    </div>
    <div class="eq-content">
        <div class="eq-latex">$${self.latex}$$</div>
        <div class="eq-description">{self.description}</div>
    </div>
    {self._generate_examples_html()}
    {self._generate_interactive_html()}
</div>
"""

    def _generate_examples_html(self) -> str:
        if not self.examples:
            return ""

        html = ['<div class="eq-examples">']
        html.append('<h4>Examples</h4>')
        for ex in self.examples:
            html.append(f'<div class="example">')
            html.append(f'<strong>{ex.get("title", "Example")}</strong>')
            html.append(f'<p>{ex.get("description", "")}</p>')
            if "input" in ex:
                html.append(f'<div class="example-input">Input: {ex["input"]}</div>')
            if "output" in ex:
                html.append(f'<div class="example-output">Output: {ex["output"]}</div>')
            if "interpretation" in ex:
                html.append(f'<div class="example-interpretation">{ex["interpretation"]}</div>')
            html.append('</div>')
        html.append('</div>')
        return "\n".join(html)

    def _generate_interactive_html(self) -> str:
        if not self.interactive:
            return ""

        sim_type = self.interactive.get("simulator_type", "basic")
        params = self.interactive.get("parameters", [])

        html = [f'<div class="eq-interactive" data-sim-type="{sim_type}">']
        html.append('<h4>Interactive Simulator</h4>')

        # Generate controls for each parameter
        for param in params:
            html.append(self._generate_param_control(param))

        html.append('<button onclick="runSimulation(this)">Calculate</button>')
        html.append('<div class="sim-output"></div>')
        html.append('</div>')

        return "\n".join(html)

    def _generate_param_control(self, param: Dict) -> str:
        name = param.get('name', 'param')
        range_vals = param.get('range', [0, 1])
        default = param.get('default', (range_vals[0] + range_vals[1]) / 2)
        step = param.get('step', 0.01)

        return f"""
<div class="param-control">
    <label for="param-{name}">{name}:</label>
    <input type="range" id="param-{name}" name="{name}"
           min="{range_vals[0]}" max="{range_vals[1]}"
           step="{step}" value="{default}">
    <span class="param-value">{default}</span>
</div>
"""


@dataclass
class Variable:
    """Represents a variable used in the textbook"""
    symbol: str  # LaTeX: "\pi"
    symbol_display: str  # Unicode: "π"
    name: str
    alt_names: List[str] = field(default_factory=list)
    description: str = ""
    physical_meaning: str = ""
    units: str = ""
    domain: str = ""
    typical_range: str = ""
    measurement_methods: List[Dict[str, str]] = field(default_factory=list)
    determination: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    related_variables: List[Dict[str, str]] = field(default_factory=list)
    appears_in_equations: List[Dict[str, str]] = field(default_factory=list)
    typical_values: Dict[str, str] = field(default_factory=dict)
    common_errors: List[Dict[str, str]] = field(default_factory=list)
    importance: str = "normal"
    difficulty: str = "intermediate"
    first_chapter: int = 0
    tags: List[str] = field(default_factory=list)

    def to_latex_varbox(self) -> str:
        """Generate LaTeX varbox code"""
        lines = []

        lines.append(f"\\begin{{varbox}}{{{self.symbol}}}")

        lines.append(f"\\textbf{{Physical description.}}")
        lines.append(self.description)
        lines.append("")

        lines.append(f"\\textbf{{Units.}}")
        lines.append(self.units + (f" (domain: {self.domain})" if self.domain else ""))
        lines.append("")

        lines.append(f"\\textbf{{Measurement / determination.}}")
        lines.append(self.determination if self.determination else
                    self._format_measurement_methods())
        lines.append("")

        if self.examples:
            lines.append(f"\\textbf{{Example.}}")
            ex = self.examples[0]  # Use first example
            lines.append(f"{ex.get('context', '')}:")
            lines.append(f"\\[")
            lines.append(f"{self.symbol} = {ex.get('value', '')} \\quad \\text{{{ex.get('units', '')}}}")
            lines.append(f"\\]")
            if 'interpretation' in ex:
                lines.append(ex['interpretation'])

        lines.append(f"\\end{{varbox}}")

        return "\n".join(lines)

    def _format_measurement_methods(self) -> str:
        if not self.measurement_methods:
            return "No specific measurement method defined."

        methods = []
        for m in self.measurement_methods:
            methods.append(f"{m.get('method', 'Unknown')} ({m.get('accuracy', 'unknown')} accuracy)")

        return " or ".join(methods)

    def to_html_card(self) -> str:
        """Generate HTML card for interactive display"""
        return f"""
<div class="variable-card" data-var-symbol="{self.symbol_display}">
    <div class="var-header">
        <span class="var-symbol">${self.symbol}$</span>
        <span class="var-name">{self.name}</span>
    </div>
    <div class="var-content">
        <div class="var-description">{self.description}</div>
        <div class="var-units"><strong>Units:</strong> {self.units}</div>
        <div class="var-domain"><strong>Domain:</strong> {self.domain}</div>
        {self._generate_examples_html()}
        {self._generate_typical_values_html()}
    </div>
</div>
"""

    def _generate_examples_html(self) -> str:
        if not self.examples:
            return ""

        html = ['<div class="var-examples">']
        html.append('<h5>Examples</h5>')
        for ex in self.examples:
            html.append(f'<div class="example">')
            html.append(f'<strong>{ex.get("context", "Example")}</strong>: ')
            html.append(f'{self.symbol_display} = {ex.get("value", "")} {ex.get("units", "")}')
            if 'interpretation' in ex:
                html.append(f'<br><em>{ex["interpretation"]}</em>')
            html.append('</div>')
        html.append('</div>')
        return "\n".join(html)

    def _generate_typical_values_html(self) -> str:
        if not self.typical_values:
            return ""

        html = ['<div class="var-typical-values">']
        html.append('<h5>Typical Values</h5>')
        html.append('<ul>')
        for context, value_range in self.typical_values.items():
            html.append(f'<li><strong>{context}:</strong> {value_range}</li>')
        html.append('</ul>')
        html.append('</div>')
        return "\n".join(html)


class EquationDatabase:
    """Manages the equation database"""

    def __init__(self, db_file: str = "equations.yaml"):
        self.db_file = Path(db_file)
        self.equations: Dict[str, Equation] = {}
        self.load()

    def load(self):
        """Load equations from YAML file"""
        if not self.db_file.exists():
            print(f"Database file {self.db_file} not found. Starting with empty database.")
            return

        with open(self.db_file, 'r') as f:
            data = yaml.safe_load(f)

        if not data or 'equations' not in data:
            return

        for eq_id, eq_data in data['equations'].items():
            self.equations[eq_id] = Equation(**eq_data)

    def save(self):
        """Save equations to YAML file"""
        data = {
            'equations': {
                eq_id: asdict(eq)
                for eq_id, eq in self.equations.items()
            }
        }

        with open(self.db_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def add_equation(self, equation: Equation):
        """Add or update an equation"""
        self.equations[equation.id] = equation

    def get_equation(self, eq_id: str) -> Optional[Equation]:
        """Retrieve an equation by ID"""
        return self.equations.get(eq_id)

    def get_equations_by_chapter(self, chapter: int) -> List[Equation]:
        """Get all equations for a specific chapter"""
        return [eq for eq in self.equations.values() if eq.chapter == chapter]

    def search_equations(self, query: str, field: str = "description") -> List[Equation]:
        """Search equations by field content"""
        results = []
        query_lower = query.lower()

        for eq in self.equations.values():
            if field == "description" and query_lower in eq.description.lower():
                results.append(eq)
            elif field == "title" and query_lower in eq.title.lower():
                results.append(eq)
            elif field == "tags" and query_lower in [t.lower() for t in eq.tags]:
                results.append(eq)

        return results


class VariableDatabase:
    """Manages the variable database"""

    def __init__(self, db_file: str = "variables.yaml"):
        self.db_file = Path(db_file)
        self.variables: Dict[str, Variable] = {}
        self.load()

    def load(self):
        """Load variables from YAML file"""
        if not self.db_file.exists():
            print(f"Database file {self.db_file} not found. Starting with empty database.")
            return

        with open(self.db_file, 'r') as f:
            data = yaml.safe_load(f)

        if not data or 'variables' not in data:
            return

        for var_id, var_data in data['variables'].items():
            self.variables[var_id] = Variable(**var_data)

    def save(self):
        """Save variables to YAML file"""
        data = {
            'variables': {
                var_id: asdict(var)
                for var_id, var in self.variables.items()
            }
        }

        with open(self.db_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def add_variable(self, variable: Variable):
        """Add or update a variable"""
        self.variables[variable.symbol_display] = variable

    def get_variable(self, symbol: str) -> Optional[Variable]:
        """Retrieve a variable by symbol"""
        return self.variables.get(symbol)

    def get_variables_by_chapter(self, chapter: int) -> List[Variable]:
        """Get all variables first introduced in a chapter"""
        return [var for var in self.variables.values() if var.first_chapter == chapter]

    def get_variables_used_in_equation(self, eq_id: str) -> List[Variable]:
        """Get all variables used in a specific equation"""
        results = []
        for var in self.variables.values():
            for usage in var.appears_in_equations:
                if usage.get('eq_id') == eq_id:
                    results.append(var)
                    break
        return results


if __name__ == "__main__":
    # Example usage
    print("Equation and Variable Database Management System")
    print("=" * 70)

    # Initialize databases
    eq_db = EquationDatabase("equations.yaml")
    var_db = VariableDatabase("variables.yaml")

    # Example: Create an equation
    eq = Equation(
        id="5.1",
        chapter=5,
        index=1,
        title="Purity ceiling on TPR",
        latex=r"\text{TPR} \leq \pi",
        latex_full=r"\begin{equation}\text{TPR} \leq \pi\label{eq:purity-ceiling}\end{equation}",
        type="inequality",
        category="fundamental",
        description="TPR cannot exceed molecular purity",
        physical_meaning="Physical constraint on classification accuracy",
        variables=["TPR", "pi"],
        tags=["purity", "fundamental"]
    )

    print(f"\nExample Equation: {eq.id} - {eq.title}")
    print(f"LaTeX: {eq.latex}")
    print(f"\nGenerated eqbox:\n{eq.to_latex_eqbox()}")

    # Example: Create a variable
    var = Variable(
        symbol=r"\pi",
        symbol_display="π",
        name="Purity",
        description="Fraction of molecules with correct sequence",
        units="dimensionless",
        domain="[0, 1]",
        first_chapter=5,
        tags=["quality", "fundamental"]
    )

    print(f"\nExample Variable: {var.symbol_display} - {var.name}")
    print(f"\nGenerated varbox:\n{var.to_latex_varbox()}")
