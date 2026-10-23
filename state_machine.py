"""
state_machine.py
----------------
Tracks account balances and takes snapshots (checkpoints).

Analogy: A bank statement that you can freeze at certain pages so you
can start reading from the freeze instead of from page one.

Note: This file is written and tested but app.py does not call it
directly, so the dashboard shows no live balances.  The logic is here
so a future version (or your own experimentation) can use it.
"""

import copy
from typing import Dict, List, Optional

from blockchain import Block, Blockchain


# ---------------------------------------------------------------------------
# StateMachine
# ---------------------------------------------------------------------------

class StateMachine:
    """
    Replays block transfers to maintain the running balance of each account.

    Fields
    ------
    balances     : Dict mapping account name → current balance.
                   Starts at 1 000.00 for Account_1 … Account_10
                   (10 000 total, preserved across transfers).
    checkpoints  : Dict mapping block index → copy of balances right
                   after that block was applied.
    """

    STARTING_BALANCE = 1_000.0
    ACCOUNTS = [f"Account_{i}" for i in range(1, 11)]

    def __init__(self) -> None:
        self.balances: Dict[str, float] = {
            acc: self.STARTING_BALANCE for acc in self.ACCOUNTS
        }
        self.checkpoints: Dict[int, Dict[str, float]] = {}
        self._processed_up_to: int = -1

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    def _process_transaction(self, sender: str, receiver: str, amount: float) -> None:
        """Apply one transfer.  Balances may go negative (no guard)."""
        self.balances[sender] = self.balances.get(sender, 0.0) - amount
        self.balances[receiver] = self.balances.get(receiver, 0.0) + amount

    def derive_state(
        self,
        blocks: List[Block],
        segment_boundaries: Optional[List[int]] = None,
    ) -> None:
        """
        Walk all blocks and optionally save a checkpoint at each boundary.

        Steps
        -----
        1. Reset balances and checkpoints.
        2. Walk blocks in order; apply each transfer.
        3. If the block's index is in *segment_boundaries*, save a copy of
           the current balances as a checkpoint for that index.

        Parameters
        ----------
        blocks             : Ordered list of Block objects.
        segment_boundaries : Block indices at which to save checkpoints.
                             Pass the last index of each segment.
                             Example: [19, 39, 59, 79, 99].
        """
        self.balances = {acc: self.STARTING_BALANCE for acc in self.ACCOUNTS}
        self.checkpoints = {}
        boundaries = set(segment_boundaries or [])

        for block in blocks:
            for tx in block.transactions:
                self._process_transaction(tx.sender, tx.receiver, tx.amount)
            if block.index in boundaries:
                self.checkpoints[block.index] = copy.deepcopy(self.balances)

        self._processed_up_to = blocks[-1].index if blocks else -1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_balances(self) -> Dict[str, float]:
        """Return a copy of the current balances."""
        return dict(self.balances)

    def get_checkpoint(self, block_index: int) -> Optional[Dict[str, float]]:
        """Return the checkpoint saved at *block_index*, or None."""
        return self.checkpoints.get(block_index)

    def validate_balances(self) -> bool:
        """Return True if every account balance is ≥ 0."""
        return all(v >= 0 for v in self.balances.values())

    def get_total_balance(self) -> float:
        """Sum of all balances.  Should equal STARTING_BALANCE × 10 = 10 000."""
        return sum(self.balances.values())

    def get_summary(self) -> dict:
        return {
            "balances": self.get_balances(),
            "total": round(self.get_total_balance(), 2),
            "checkpoints_saved": sorted(self.checkpoints.keys()),
            "all_non_negative": self.validate_balances(),
        }

    def __repr__(self) -> str:
        return (
            f"StateMachine(accounts={len(self.balances)}, "
            f"checkpoints={list(self.checkpoints.keys())})"
        )
