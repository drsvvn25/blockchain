"""
storage_metrics.py
------------------
Works out how many bytes a full node and a segmented node need.

Analogy: A price calculator — what does each shelf cost if every
library owns every volume, compared to owning only some?

Model assumptions (all tunable via the sidebar):
  header_size      = 160 bytes per block
  state_size       = 4 096 bytes (latest balances)
  block_data_size  = 1 000 bytes per block's transaction list

These are assumed constants, not measured data from real disk usage.
"""

from typing import Dict, List, Optional

from assignment import AssignmentEngine, Node
from segmentation import SegmentationEngine, Segment


# ---------------------------------------------------------------------------
# StorageMetrics
# ---------------------------------------------------------------------------

class StorageMetrics:
    """
    Computes and stores per-node and network-wide byte counts.

    Usage
    -----
    >>> sm = StorageMetrics(block_data_size=1000, header_size=160, state_size=4096)
    >>> sm.calculate_segmented_storage(assignment_engine, segmentation_engine, total_blocks)
    >>> sm.full_node_bytes
    120096
    """

    DEFAULT_BLOCK_DATA_SIZE = 1_000   # bytes per block's data
    DEFAULT_HEADER_SIZE = 160          # bytes per block header
    DEFAULT_STATE_SIZE = 4_096         # bytes for the latest state

    def __init__(
        self,
        block_data_size: int = DEFAULT_BLOCK_DATA_SIZE,
        header_size: int = DEFAULT_HEADER_SIZE,
        state_size: int = DEFAULT_STATE_SIZE,
    ) -> None:
        self.block_data_size = block_data_size
        self.header_size = header_size
        self.state_size = state_size

        # Filled by estimate_storage / calculate_segmented_storage
        self.full_node_bytes: int = 0
        self.average_node_bytes: float = 0.0
        self.min_node_bytes: int = 0
        self.max_node_bytes: int = 0
        self.reduction_percentage: float = 0.0
        self.total_network_bytes: int = 0
        self._total_blocks: int = 0

    # ------------------------------------------------------------------
    # Full-node estimate
    # ------------------------------------------------------------------

    def estimate_storage(self, total_blocks: int) -> dict:
        """
        Calculate bytes for a node that stores all block data.

        full = blocks × data_size + blocks × header_size + state_size
        """
        self._total_blocks = total_blocks
        block_data = total_blocks * self.block_data_size
        headers = total_blocks * self.header_size
        state = self.state_size
        self.full_node_bytes = block_data + headers + state
        return {
            "block_data_bytes": block_data,
            "header_bytes": headers,
            "state_bytes": state,
            "total_bytes": self.full_node_bytes,
        }

    # ------------------------------------------------------------------
    # Per-node segmented storage
    # ------------------------------------------------------------------

    def calculate_segmented_storage(
        self,
        assignment: AssignmentEngine,
        segmentation: SegmentationEngine,
        total_blocks: int,
    ) -> List[dict]:
        """
        Walk each node, compute its byte count and write the values back
        into the Node objects.

        Per-node formula
        ----------------
          stored_block_bytes = sum(seg.block_count × block_data_size
                                   for each seg this node holds)
          header_bytes       = total_blocks × header_size   (always full)
          state_bytes        = state_size                   (always full)
          total_bytes        = above three summed

        Also updates self.average_node_bytes, min, max, reduction_percentage
        and total_network_bytes.
        """
        self.estimate_storage(total_blocks)

        seg_id_to_block_count: Dict[str, int] = {
            seg.segment_id: seg.block_count
            for seg in segmentation.segments
        }
        all_headers = total_blocks * self.header_size
        results = []

        for node in assignment.nodes:
            blk_bytes = sum(
                seg_id_to_block_count.get(sid, 0) * self.block_data_size
                for sid in node.segment_ids
            )
            node.stored_block_bytes = blk_bytes
            node.header_bytes = all_headers
            node.state_bytes = self.state_size
            node.total_bytes = blk_bytes + all_headers + self.state_size
            results.append({
                "node_id": node.node_id,
                "stored_block_bytes": node.stored_block_bytes,
                "header_bytes": node.header_bytes,
                "state_bytes": node.state_bytes,
                "total_bytes": node.total_bytes,
            })

        totals = [n.total_bytes for n in assignment.nodes]
        self.average_node_bytes = sum(totals) / len(totals)
        self.min_node_bytes = min(totals)
        self.max_node_bytes = max(totals)
        self.total_network_bytes = sum(totals)
        self.reduction_percentage = self.calculate_reduction()
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def compare_storage(self) -> dict:
        return {
            "full_node_bytes": self.full_node_bytes,
            "average_segmented_bytes": round(self.average_node_bytes, 2),
            "min_segmented_bytes": self.min_node_bytes,
            "max_segmented_bytes": self.max_node_bytes,
            "reduction_percentage": round(self.reduction_percentage, 2),
        }

    def calculate_reduction(self) -> float:
        """(full − segmented_average) / full × 100."""
        if self.full_node_bytes == 0:
            return 0.0
        return (self.full_node_bytes - self.average_node_bytes) / self.full_node_bytes * 100

    def calculate_network_storage(self) -> int:
        """Total bytes across all nodes in the network."""
        return self.total_network_bytes

    @staticmethod
    def format_bytes(n: float) -> str:
        """Human-readable size string."""
        if n >= 1_048_576:
            return f"{n / 1_048_576:.2f} MB"
        if n >= 1_024:
            return f"{n / 1_024:.2f} KB"
        return f"{int(n)} B"

    def get_per_node_rows(self, assignment: AssignmentEngine) -> List[dict]:
        """Return a list of dicts suitable for a Streamlit dataframe."""
        return [
            {
                "Node": n.node_id,
                "Segments held": ", ".join(n.segment_ids) if n.segment_ids else "—",
                "Block data (B)": n.stored_block_bytes,
                "Headers (B)": n.header_bytes,
                "State (B)": n.state_bytes,
                "Total (B)": n.total_bytes,
                "Online": n.is_online,
            }
            for n in assignment.nodes
        ]

    def __repr__(self) -> str:
        return (
            f"StorageMetrics("
            f"full={self.full_node_bytes}B, "
            f"avg={self.average_node_bytes:.0f}B, "
            f"reduction={self.reduction_percentage:.1f}%)"
        )
