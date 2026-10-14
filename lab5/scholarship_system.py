"""Scholarship screener module for evaluating student scholarship eligibility.

This module computes merit scores from GPA and extracurricular credits,
evaluates family income against limits, and saves eligible candidate
shortlists.
"""

import ast
import json
import operator
from typing import Any, Dict, List, Optional

# Global configuration and state
RESULTS: Dict[str, Dict[str, Any]] = {}
results = RESULTS
MERIT_CONFIG = {"formula": "gpa * 10 + credits * 2"}
INCOME_LIMIT = 800000
CUTOFF = 85

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _safe_eval_formula(expr: str, context: Dict[str, float]) -> float:
    """Safely parse and evaluate an arithmetic formula without eval."""
    tree = ast.parse(expr, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(
            node.value, (int, float)
        ):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in context:
                return float(context[node.id])
            raise ValueError(f"Undefined variable in formula: {node.id}")
        if (
            isinstance(node, ast.UnaryOp)
            and type(node.op) in _ALLOWED_OPERATORS
        ):
            return _ALLOWED_OPERATORS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
            return _ALLOWED_OPERATORS[type(node.op)](
                _eval(node.left), _eval(node.right)
            )
        raise ValueError(
            f"Unsupported syntax in formula: {type(node).__name__}"
        )

    return _eval(tree)


def calculate_merit_score(
    gpa: float,
    applicant_credits: float = 0.0,
    **kwargs: Any,
) -> float:
    """Calculate the merit score based on GPA and extra credits."""
    credits_val = kwargs.get("credits", applicant_credits)
    context = {"gpa": float(gpa), "credits": float(credits_val)}
    return _safe_eval_formula(MERIT_CONFIG["formula"], context)


def evaluate_applicant(
    student_id: str,
    test_scores: Dict[str, Any],
    logs: Optional[List[str]] = None,
) -> bool:
    """Evaluate applicant eligibility based on score and income."""
    if logs is None:
        logs = []
    gpa = test_scores.get("gpa", 0.0)
    credits_count = test_scores.get("credits", 0)
    income = test_scores.get("income", 0)
    score = calculate_merit_score(gpa, credits_count)
    eligible = score >= CUTOFF and income < INCOME_LIMIT
    RESULTS[student_id] = {"score": score, "eligible": eligible}
    logs.append(f"{student_id} scored {score}")
    return eligible


def change_formula(new_formula: str) -> None:
    """Update the merit calculation formula securely."""
    MERIT_CONFIG["formula"] = new_formula


def persist_results(filepath: str = "scholarships.json") -> None:
    """Persist screening results to a JSON file."""
    with open(filepath, "w", encoding="utf-8") as file_handle:
        json.dump(RESULTS, file_handle, indent=2)


def load_results(filepath: str = "scholarships.json") -> None:
    """Load screening results from a JSON file into module state."""
    try:
        with open(filepath, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
            RESULTS.clear()
            RESULTS.update(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass


def print_shortlist() -> None:
    """Print the shortlisted eligible applicants to stdout."""
    print("Shortlisted applicants:")
    for student_id, details in RESULTS.items():
        if details["eligible"]:
            print(f"  {student_id} score = {details['score']}")


def main() -> None:
    """Execute the scholarship evaluation workflow."""
    evaluate_applicant(
        "U001", {"gpa": 9.1, "credits": 4, "income": 450000}
    )
    evaluate_applicant(
        "U002", {"gpa": 7.2, "credits": 1, "income": 300000}
    )
    evaluate_applicant(
        "U003", {"gpa": 12.5, "credits": -3, "income": -1}
    )
    evaluate_applicant("U004", {"gpa": 6.5})
    formula = input("Merit formula (Enter to keep default): ")
    if formula.strip():
        change_formula(formula.strip())
    evaluate_applicant(
        "U005", {"gpa": 8.4, "credits": 3, "income": 600000}
    )
    persist_results()
    load_results()
    print_shortlist()


if __name__ == "__main__":
    main()
