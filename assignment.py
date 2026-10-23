"""
assignment.py
-------------
Creates the simulated nodes and decides which node stores which segment.

Analogy: Handing out copies of five book volumes to 30 libraries by
drawing names from a hat — three libraries per volume.

Each Node is a Python object (not a real computer).  The assignment
engine uses random.sample to pick distinct replica holders per segment.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from segmentation import Segment


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """
    One simulated computer in the network.

    Fields
    ------
    node_id            : Name: N1 to N<num_nodes>.
    segment_ids        : Which segments this node stores.
    is_online          : Whether the node is up.  Used by failure tests.
    stored_block_bytes : Block data bytes stored (filled by StorageMetrics).
    header_bytes       : Header bytes (all blocks).
    state_bytes        : Latest state bytes.
    total_bytes        : Sum of the three above.
    """

    node_id: str
    segment_ids: List[str] = field(default_factory=list)
    is_online: bool = True

    # Filled in later by storage_metrics
    stored_block_bytes: int = 0
    header_bytes: int = 0
    state_bytes: int = 0
    total_bytes: int = 0

    def __repr__(self) -> str:
        segs = ", ".join(self.segment_ids) if self.segment_ids else "none"
        status = "online" if self.is_online else "OFFLINE"
        return f"Node({self.node_id}: segs=[{segs}], {status})"


# ---------------------------------------------------------------------------
# AssignmentEngine
# ---------------------------------------------------------------------------

class AssignmentEngine:
    """
    Creates N nodes and assigns each segment to *m* distinct random nodes.

    Usage
    -----
    >>> from segmentation import SegmentationEngine
    >>> from blockchain import Blockchain
    >>> bc = Blockchain.generate_chain(100, 5, 7)
    >>> se = SegmentationEngine()
    >>> segs = se.partition_segments(bc.blocks, 5)
    >>> ae = AssignmentEngine()
    >>> ae.assign_segment_replicas(segs, num_nodes=30, replicas_per_segment=3, seed=7)
    >>> ae.segment_replicas["S1"]
    ['N11', 'N5', 'N13']
    """

    def __init__(self) -> None:
        self.nodes: List[Node] = []
        self._node_map: Dict[str, Node] = {}
        # Dict: segment_id → list of node_ids that hold it
        self.segment_replicas: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def assign_segment_replicas(
        self,
        segments: List[Segment],
        num_nodes: int,
        replicas_per_segment: int,
        seed: int = 7,
    ) -> Dict[str, List[str]]:
        """
        Steps
        -----
        1. Validate inputs.
        2. Seed random and create N1 … N<num_nodes> with empty segment lists.
        3. For each segment, random.sample picks *replicas_per_segment*
           distinct node indices (0-based), converted to node ids.
        4. Each chosen node gets the segment id appended to segment_ids.
        5. segment_replicas records the node ids.
        6. validate_assignment() confirms every segment has exactly the
           expected number of distinct holders.
        """
        if num_nodes <= 0:
            raise ValueError("num_nodes must be > 0")
        if replicas_per_segment <= 0:
            raise ValueError("replicas_per_segment must be > 0")
        if replicas_per_segment > num_nodes:
            raise ValueError(
                f"replicas_per_segment ({replicas_per_segment}) cannot "
                f"exceed num_nodes ({num_nodes})"
            )

        random.seed(seed)

        # Create nodes
        self.nodes = [Node(node_id=f"N{i+1}") for i in range(num_nodes)]
        self._node_map = {n.node_id: n for n in self.nodes}
        self.segment_replicas = {}

        for seg in segments:
            chosen_indices = random.sample(range(num_nodes), replicas_per_segment)
            chosen_ids = []
            for idx in chosen_indices:
                node = self.nodes[idx]
                node.segment_ids.append(seg.segment_id)
                chosen_ids.append(node.node_id)
            self.segment_replicas[seg.segment_id] = chosen_ids

        self.validate_assignment(segments, replicas_per_segment)
        return self.segment_replicas

    def validate_assignment(
        self,
        segments: List[Segment],
        expected_replicas: int,
    ) -> None:
        """
        Check every segment has exactly *expected_replicas* distinct holders.

        Raises ValueError if not.
        """
        for seg in segments:
            holders = self.segment_replicas.get(seg.segment_id, [])
            if len(holders) != expected_replicas:
                raise ValueError(
                    f"Segment {seg.segment_id} has {len(holders)} replicas "
                    f"(expected {expected_replicas})"
                )
            if len(set(holders)) != len(holders):
                raise ValueError(
                    f"Segment {seg.segment_id} has duplicate node assignments"
                )

    # ------------------------------------------------------------------
    # Node status controls
    # ------------------------------------------------------------------

    def set_node_status(self, node_id: str, is_online: bool) -> None:
        """Toggle a node online or offline."""
        node = self._node_map.get(node_id)
        if node is None:
            raise KeyError(f"Node {node_id!r} not found")
        node.is_online = is_online

    def reset_all_nodes(self) -> None:
        """Bring all nodes back online."""
        for node in self.nodes:
            node.is_online = True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._node_map.get(node_id)

    def get_segment_replica_count(self, segment_id: str) -> int:
        """Return the number of *online* holders of this segment."""
        holder_ids = self.segment_replicas.get(segment_id, [])
        return sum(
            1
            for nid in holder_ids
            if self._node_map.get(nid, Node("_")).is_online
        )

    def get_assignment_matrix(self) -> List[dict]:
        """
        Return one row per node, showing node_id, segment_ids, and status.
        Useful for the Network page table.
        """
        return [
            {
                "node_id": n.node_id,
                "segment_ids": n.segment_ids,
                "is_online": n.is_online,
                "stored_block_bytes": n.stored_block_bytes,
                "header_bytes": n.header_bytes,
                "state_bytes": n.state_bytes,
                "total_bytes": n.total_bytes,
            }
            for n in self.nodes
        ]

    def get_node_ids_for_segment(self, segment_id: str) -> List[str]:
        return self.segment_replicas.get(segment_id, [])

    def __repr__(self) -> str:
        return (
            f"AssignmentEngine(nodes={len(self.nodes)}, "
            f"segments={len(self.segment_replicas)})"
        )
