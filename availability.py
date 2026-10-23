"""
availability.py
---------------
Switches nodes off and checks which segments still have a living copy.

Analogy: A fire drill — close some libraries and see which volumes you
can no longer find anywhere.

Note: This file only checks "is any copy online?", it does not
simulate actually fetching data over a network.
"""

import random
from typing import Dict, List, Optional, Set

from assignment import AssignmentEngine


# ---------------------------------------------------------------------------
# AvailabilitySimulator
# ---------------------------------------------------------------------------

class AvailabilitySimulator:
    """
    Simulates random or targeted node failures and reports which segments
    survive.

    Usage
    -----
    >>> sim = AvailabilitySimulator(assignment_engine)
    >>> result = sim.simulate_node_failures(failure_percentage=30, seed=42)
    >>> result["availability_percentage"]
    60.0
    """

    def __init__(self, assignment: AssignmentEngine) -> None:
        self.assignment = assignment
        self.failed_nodes: Set[str] = set()

    # ------------------------------------------------------------------
    # Failure simulation
    # ------------------------------------------------------------------

    def simulate_node_failures(
        self,
        node_ids: Optional[List[str]] = None,
        failure_percentage: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> dict:
        """
        Mark nodes as failed and report segment availability.

        Steps
        -----
        1. Reset every node to online and clear the failure set.
        2a. If *node_ids* is given, mark those nodes offline.
        2b. If *failure_percentage* is given, seed the generator, compute
            int(total × pct / 100) and pick that many with random.sample.
        3. For each segment count online holders.  Zero → lost.
        4. Return a full results dictionary.

        Parameters
        ----------
        node_ids           : Explicit list of node ids to take offline.
        failure_percentage : Fraction of nodes to fail randomly (0–100).
        seed               : Seed for the random choice of failing nodes.
        """
        # 1. Reset
        self.assignment.reset_all_nodes()
        self.failed_nodes = set()

        total_nodes = len(self.assignment.nodes)

        if node_ids is not None:
            for nid in node_ids:
                self.assignment.set_node_status(nid, False)
                self.failed_nodes.add(nid)

        elif failure_percentage is not None and failure_percentage > 0:
            if seed is not None:
                random.seed(seed)
            num_to_fail = int(total_nodes * failure_percentage / 100)
            all_ids = [n.node_id for n in self.assignment.nodes]
            chosen = random.sample(all_ids, min(num_to_fail, total_nodes))
            for nid in chosen:
                self.assignment.set_node_status(nid, False)
                self.failed_nodes.add(nid)

        return self._build_result()

    def fail_random_nodes(self, count: int, seed: Optional[int] = None) -> dict:
        """Fail exactly *count* randomly chosen nodes."""
        self.assignment.reset_all_nodes()
        self.failed_nodes = set()
        if seed is not None:
            random.seed(seed)
        all_ids = [n.node_id for n in self.assignment.nodes]
        chosen = random.sample(all_ids, min(count, len(all_ids)))
        for nid in chosen:
            self.assignment.set_node_status(nid, False)
            self.failed_nodes.add(nid)
        return self._build_result()

    def restore_node(self, node_id: str) -> None:
        """Bring a single node back online."""
        self.assignment.set_node_status(node_id, True)
        self.failed_nodes.discard(node_id)

    def restore_all_nodes(self) -> None:
        """Bring all nodes back online."""
        self.assignment.reset_all_nodes()
        self.failed_nodes = set()

    # ------------------------------------------------------------------
    # Status query
    # ------------------------------------------------------------------

    def get_critical_segments(self) -> List[str]:
        """Return segment ids that have exactly one online holder."""
        return [
            seg_id
            for seg_id in self.assignment.segment_replicas
            if self.assignment.get_segment_replica_count(seg_id) == 1
        ]

    def _build_result(self) -> dict:
        """Compile the full availability report."""
        total_nodes = len(self.assignment.nodes)
        online_nodes = total_nodes - len(self.failed_nodes)
        surviving_replicas: Dict[str, int] = {}
        lost_segments: List[str] = []
        critical_segments: List[str] = []

        for seg_id in self.assignment.segment_replicas:
            count = self.assignment.get_segment_replica_count(seg_id)
            surviving_replicas[seg_id] = count
            if count == 0:
                lost_segments.append(seg_id)
            elif count == 1:
                critical_segments.append(seg_id)

        total_segments = len(self.assignment.segment_replicas)
        available_segments = total_segments - len(lost_segments)
        availability_pct = (
            available_segments / total_segments * 100 if total_segments else 0.0
        )

        return {
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "offline_nodes": len(self.failed_nodes),
            "failed_node_ids": sorted(self.failed_nodes),
            "surviving_replicas": surviving_replicas,
            "lost_segments": lost_segments,
            "critical_segments": critical_segments,
            "available_segments": available_segments,
            "total_segments": total_segments,
            "availability_percentage": round(availability_pct, 2),
        }

    def __repr__(self) -> str:
        return (
            f"AvailabilitySimulator("
            f"nodes={len(self.assignment.nodes)}, "
            f"failed={len(self.failed_nodes)})"
        )
