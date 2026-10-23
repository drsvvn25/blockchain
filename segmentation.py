"""
segmentation.py
---------------
Cuts the list of blocks into consecutive segments.

Analogy: Cutting a long film reel into equal parts without losing or
repeating a single frame.

Every segment is a named slice of the chain (S1, S2, …).  Nodes store
the block data of their segments plus all headers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from blockchain import Block


# ---------------------------------------------------------------------------
# Segment dataclass
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    """
    A consecutive run of blocks.

    Fields
    ------
    segment_id   : Name: S1, S2, …
    start_height : Index of the first block in the segment.
    end_height   : Index of the last block (inclusive).
    block_count  : Number of blocks it holds.
    blocks       : The block objects themselves.
    checkpoint   : Reserved for a balance snapshot at end_height.
                   Always None in the current version.
    """

    segment_id: str
    start_height: int
    end_height: int
    block_count: int
    blocks: List[Block] = field(default_factory=list)
    checkpoint: Optional[dict] = None

    def __repr__(self) -> str:
        return (
            f"Segment({self.segment_id}: "
            f"blocks {self.start_height}–{self.end_height}, "
            f"count={self.block_count})"
        )

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "start_height": self.start_height,
            "end_height": self.end_height,
            "block_count": self.block_count,
        }


# ---------------------------------------------------------------------------
# SegmentationEngine
# ---------------------------------------------------------------------------

class SegmentationEngine:
    """
    Partitions a chain into consecutive segments and provides lookups.

    Usage
    -----
    >>> from blockchain import Blockchain
    >>> bc = Blockchain.generate_chain(100, 5, 7)
    >>> engine = SegmentationEngine()
    >>> segments = engine.partition_segments(bc.blocks, num_segments=5)
    >>> engine.get_segment_by_id("S3")
    Segment(S3: blocks 40–59, count=20)
    """

    def __init__(self) -> None:
        self.segments: List[Segment] = []
        self._id_map: Dict[str, Segment] = {}

    # ------------------------------------------------------------------
    # Partitioning
    # ------------------------------------------------------------------

    def partition_segments(
        self,
        blocks: List[Block],
        num_segments: int,
    ) -> List[Segment]:
        """
        Divide *blocks* into *num_segments* consecutive segments.

        Steps
        -----
        1. Validate inputs.
        2. Compute base size and remainder using integer division.
        3. First *remainder* segments get one extra block (round-robin).
        4. Build Segment objects and call validate_partitioning().
        5. Store results and return them.

        Example
        -------
        103 blocks into 5 segments → sizes [21, 21, 21, 20, 20].
        100 blocks into 5 segments → sizes [20, 20, 20, 20, 20].
        """
        if num_segments <= 0:
            raise ValueError("num_segments must be > 0")
        if not blocks:
            raise ValueError("blocks list is empty")
        if num_segments > len(blocks):
            raise ValueError(
                f"Cannot create {num_segments} segments from "
                f"only {len(blocks)} blocks"
            )

        n = len(blocks)
        base = n // num_segments
        remainder = n % num_segments

        self.segments = []
        self._id_map = {}
        cursor = 0

        for seg_num in range(1, num_segments + 1):
            size = base + (1 if seg_num <= remainder else 0)
            seg_blocks = blocks[cursor: cursor + size]
            seg = Segment(
                segment_id=f"S{seg_num}",
                start_height=cursor,
                end_height=cursor + size - 1,
                block_count=size,
                blocks=seg_blocks,
                checkpoint=None,
            )
            self.segments.append(seg)
            self._id_map[seg.segment_id] = seg
            cursor += size

        self.validate_partitioning(blocks)
        return self.segments

    def validate_partitioning(self, blocks: List[Block]) -> None:
        """
        Confirm no gaps, no overlaps, every block covered exactly once.

        Raises ValueError on any inconsistency.
        """
        covered = []
        for seg in self.segments:
            for blk in seg.blocks:
                covered.append(blk.index)

        if len(covered) != len(blocks):
            raise ValueError(
                f"Partitioning covers {len(covered)} blocks but chain has "
                f"{len(blocks)}"
            )
        if sorted(covered) != list(range(len(blocks))):
            raise ValueError("Partitioning has gaps or overlaps")

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_segment_by_id(self, segment_id: str) -> Optional[Segment]:
        """Return the Segment with the given id (e.g. 'S3'), or None."""
        return self._id_map.get(segment_id)

    def get_segment_by_height(self, block_height: int) -> Optional[Segment]:
        """Return the Segment that contains the block at *block_height*."""
        for seg in self.segments:
            if seg.start_height <= block_height <= seg.end_height:
                return seg
        return None

    def get_segment_boundaries(self) -> List[int]:
        """Return the end_height of each segment (useful for checkpoints)."""
        return [seg.end_height for seg in self.segments]

    def summary(self) -> List[dict]:
        return [seg.to_dict() for seg in self.segments]

    def __len__(self) -> int:
        return len(self.segments)

    def __repr__(self) -> str:
        return f"SegmentationEngine(segments={len(self.segments)})"
