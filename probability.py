"""
probability.py
--------------
Calculates the theoretical chance of losing a segment to an attacker,
using the formula from the paper:

    P = (A / n) ^ m

where
  n = total nodes in the network
  A = number of nodes the attacker controls
  m = replicas per segment (copies)

Analogy: Betting odds — if each of three copies independently has a
1-in-10 chance of sitting on a bad node, all three being bad is 1-in-1000.

Note: This module is independent of the simulated network.  It is pure
math shown alongside the simulation.
"""

from typing import Dict, List, Optional, Tuple
import math


# ---------------------------------------------------------------------------
# Core formula
# ---------------------------------------------------------------------------

def segment_loss_probability(
    total_nodes: int,
    adversarial_nodes: int,
    replicas_per_segment: int,
) -> dict:
    """
    Compute P = (A/n)^m and return a detailed result dictionary.

    Parameters
    ----------
    total_nodes          (n) : Total nodes in the network.  Must be > 0.
    adversarial_nodes    (A) : Nodes controlled by the attacker.
                               Must be 0 ≤ A ≤ n.
    replicas_per_segment (m) : Copies of each segment.  Must be 0 < m ≤ n.

    Returns
    -------
    {
      "probability"         : float  (0 to 1)
      "percentage"          : float  (0 to 100)
      "formula_text"        : str    e.g. "P = (3/30)^3"
      "adversarial_fraction": float
      "one_in"              : float  (1 / probability, or inf)
    }
    """
    n = total_nodes
    A = adversarial_nodes
    m = replicas_per_segment

    # --- Input validation ---
    if n <= 0:
        raise ValueError("total_nodes must be > 0")
    if A < 0 or A > n:
        raise ValueError(f"adversarial_nodes must be 0 ≤ A ≤ n, got {A}")
    if m <= 0 or m > n:
        raise ValueError(f"replicas_per_segment must be 0 < m ≤ n, got {m}")

    frac = A / n
    probability = frac ** m
    percentage = probability * 100
    one_in = (1 / probability) if probability > 0 else float("inf")

    return {
        "probability": probability,
        "percentage": percentage,
        "formula_text": f"P = ({A}/{n})^{m}",
        "adversarial_fraction": frac,
        "one_in": one_in,
    }


# ---------------------------------------------------------------------------
# Exact probability (sampling without replacement)
# ---------------------------------------------------------------------------

def exact_segment_loss_probability(
    total_nodes: int,
    adversarial_nodes: int,
    replicas_per_segment: int,
) -> float:
    """
    Exact probability that all m replicas land on adversarial nodes when
    nodes are drawn *without* replacement.

    Formula: (A/n) × ((A-1)/(n-1)) × … for m terms.

    This is an addition for learning — the paper uses the simpler formula.
    For n=30, A=3, m=3 this gives 1 in 4 060 vs the formula's 1 in 1 000.
    """
    n, A, m = total_nodes, adversarial_nodes, replicas_per_segment
    if A < m:
        return 0.0
    p = 1.0
    for i in range(m):
        if A - i <= 0:
            return 0.0
        p *= (A - i) / (n - i)
    return p


# ---------------------------------------------------------------------------
# Curve helpers
# ---------------------------------------------------------------------------

def calculate_probability_curve(
    total_nodes: int,
    adversarial_nodes: int,
    max_replicas: int = 10,
) -> List[dict]:
    """
    Repeat the formula for m = 1, 2, … max_replicas.

    Returns a list of dicts with keys: m, probability, percentage, one_in.
    """
    results = []
    for m in range(1, max_replicas + 1):
        try:
            r = segment_loss_probability(total_nodes, adversarial_nodes, m)
            r["m"] = m
            results.append(r)
        except ValueError:
            break
    return results


def calculate_multiple_curves(
    total_nodes: int,
    attacker_percentages: List[float],
    max_replicas: int = 10,
) -> Dict[float, List[dict]]:
    """
    Compute a probability curve for each attacker percentage in the list.

    Returns a dict: pct → list of per-m results.
    """
    curves = {}
    for pct in attacker_percentages:
        A = max(0, min(total_nodes, round(total_nodes * pct / 100)))
        curves[pct] = calculate_probability_curve(total_nodes, A, max_replicas)
    return curves


# ---------------------------------------------------------------------------
# Assumption text
# ---------------------------------------------------------------------------

def get_assumptions_explanation() -> str:
    return (
        "Assumptions used in the paper's formula:\n"
        "1. Each of the m replicas is placed on a node chosen independently.\n"
        "2. The attacker controls exactly A out of n nodes.\n"
        "3. A segment is 'lost' only when ALL m replicas fall on adversarial nodes.\n"
        "4. This models a coordinated adversary — a different question from\n"
        "   random node failures, which the availability simulator covers.\n"
        "5. The formula is a slightly cautious upper bound; the exact probability\n"
        "   (without replacement) is always lower or equal."
    )
