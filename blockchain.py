"""
blockchain.py
-------------
Builds a fake (simulated) blockchain and checks it has not been changed.

Analogy: A notebook where every page begins by copying a fingerprint of
the previous page. Rip one page out and the next page no longer matches.

Every field, every function, and every hash in this file is described in
the SegmentChain Deep Dive guide.
"""

import hashlib
import json
import random
import copy
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    """One transfer of money from a sender to a receiver."""

    sender: str           # Account_1 to Account_10
    receiver: str         # Always different from sender
    amount: float         # 1.00 to 100.00, two decimal places
    transaction_id: str   # Label built from block number and position: tx_<block>_<pos>

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "transaction_id": self.transaction_id,
        }

    def __repr__(self) -> str:
        return (
            f"Transaction({self.sender} → {self.receiver}  "
            f"{self.amount:.2f}  {self.transaction_id})"
        )


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """
    One record (page) of the ledger.

    Fields
    ------
    index          : Position in the chain.  Genesis block is 0.
    timestamp      : Fake time in seconds.  Genesis is 0.0, others are
                     random between 1e9 and 2e9.
    transactions   : List of transfers in this block.
    previous_hash  : block_hash of the block before.  Genesis uses 64 zeros.
    data_hash      : SHA-256 fingerprint of the transactions list only.
    block_hash     : SHA-256 fingerprint of index + timestamp + data_hash
                     + previous_hash glued together.  This is the block's
                     identity and what the next block copies.
    """

    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    data_hash: str = ""
    block_hash: str = ""

    # ------------------------------------------------------------------
    # Hashing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def compute_data_hash(self) -> str:
        """Fingerprint the transaction list as a JSON string (sorted keys)."""
        tx_list = [tx.to_dict() for tx in self.transactions]
        serialised = json.dumps(tx_list, sort_keys=True)
        return self._sha256(serialised)

    def compute_block_hash(self) -> str:
        """
        Fingerprint of index + timestamp + data_hash + previous_hash glued
        together as a plain string (no separator), matching blockchain.py's
        original formula.
        """
        raw = f"{self.index}{self.timestamp}{self.data_hash}{self.previous_hash}"
        return self._sha256(raw)

    def finalise(self) -> None:
        """Compute and store both hashes.  Call after setting all fields."""
        self.data_hash = self.compute_data_hash()
        self.block_hash = self.compute_block_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "data_hash": self.data_hash,
            "block_hash": self.block_hash,
        }

    def __repr__(self) -> str:
        return (
            f"Block(index={self.index}, "
            f"tx={len(self.transactions)}, "
            f"hash={self.block_hash[:12]}…)"
        )


# ---------------------------------------------------------------------------
# Blockchain
# ---------------------------------------------------------------------------

GENESIS_PREV_HASH = "0" * 64
ACCOUNTS = [f"Account_{i}" for i in range(1, 11)]   # Account_1 … Account_10


class Blockchain:
    """
    A linked list of Block objects.

    Usage
    -----
    >>> bc = Blockchain.generate_chain(num_blocks=100, tx_per_block=5, seed=7)
    >>> result = bc.verify_chain()
    >>> result["valid"]
    True
    """

    def __init__(self, blocks: Optional[List[Block]] = None) -> None:
        self.blocks: List[Block] = blocks if blocks is not None else []

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    @classmethod
    def generate_chain(
        cls,
        num_blocks: int = 100,
        tx_per_block: int = 5,
        seed: int = 7,
    ) -> "Blockchain":
        """
        Build a deterministic fake chain.

        Parameters
        ----------
        num_blocks   : Total number of blocks (including genesis).
        tx_per_block : Transfers inside every non-genesis block.
        seed         : Passed to random.seed() first so the same inputs
                       always produce the same chain.

        Steps
        -----
        1. Seed the random generator.
        2. Create the genesis block (index 0, timestamp 0.0, no transactions,
           previous_hash = 64 zeros).
        3. For every subsequent block: pick random transfers, compute hashes
           and link to the previous block.
        """
        random.seed(seed)
        blocks: List[Block] = []

        # Genesis block
        genesis = Block(
            index=0,
            timestamp=0.0,
            transactions=[],
            previous_hash=GENESIS_PREV_HASH,
        )
        genesis.finalise()
        blocks.append(genesis)

        prev_hash = genesis.block_hash

        for idx in range(1, num_blocks):
            timestamp = round(random.uniform(1e9, 2e9), 7)
            txs = cls._make_transactions(idx, tx_per_block)
            block = Block(
                index=idx,
                timestamp=timestamp,
                transactions=txs,
                previous_hash=prev_hash,
            )
            block.finalise()
            blocks.append(block)
            prev_hash = block.block_hash

        return cls(blocks)

    @staticmethod
    def _make_transactions(block_index: int, count: int) -> List[Transaction]:
        """Create *count* random transfers for a given block."""
        txs = []
        for pos in range(count):
            sender = random.choice(ACCOUNTS)
            others = [a for a in ACCOUNTS if a != sender]
            receiver = random.choice(others)
            amount = round(random.uniform(1.0, 100.0), 2)
            txs.append(
                Transaction(
                    sender=sender,
                    receiver=receiver,
                    amount=amount,
                    transaction_id=f"tx_{block_index}_{pos}",
                )
            )
        return txs

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_chain(self) -> dict:
        """
        Walk left to right and report the first mismatch.

        Returns
        -------
        {"valid": True, "error": None, "failed_block": None}
        or
        {"valid": False, "error": "<description>", "failed_block": <index>}
        """
        for i, block in enumerate(self.blocks):
            # Check data_hash
            expected_data_hash = block.compute_data_hash()
            if block.data_hash != expected_data_hash:
                return {
                    "valid": False,
                    "error": f"Transaction data hash mismatch at block {i}",
                    "failed_block": i,
                }

            # Check block_hash (recompute using stored data_hash)
            expected_block_hash = block.compute_block_hash()
            if block.block_hash != expected_block_hash:
                return {
                    "valid": False,
                    "error": f"Block hash mismatch at block {i}",
                    "failed_block": i,
                }

            # Check previous_hash link
            if i == 0:
                if block.previous_hash != GENESIS_PREV_HASH:
                    return {
                        "valid": False,
                        "error": "Genesis block has invalid previous hash",
                        "failed_block": 0,
                    }
            else:
                expected_prev = self.blocks[i - 1].block_hash
                if block.previous_hash != expected_prev:
                    return {
                        "valid": False,
                        "error": f"Previous hash link broken at block {i}",
                        "failed_block": i,
                    }

        return {"valid": True, "error": None, "failed_block": None}

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.blocks)

    def __getitem__(self, idx: int) -> Block:
        return self.blocks[idx]

    def __iter__(self):
        return iter(self.blocks)

    def __repr__(self) -> str:
        return f"Blockchain(blocks={len(self.blocks)})"

    def get_block(self, index: int) -> Optional[Block]:
        if 0 <= index < len(self.blocks):
            return self.blocks[index]
        return None

    def get_chain_info(self) -> dict:
        """Summary dictionary suitable for dashboard display."""
        return {
            "total_blocks": len(self.blocks),
            "genesis_hash": self.blocks[0].block_hash if self.blocks else None,
            "latest_hash": self.blocks[-1].block_hash if self.blocks else None,
            "total_transactions": sum(len(b.transactions) for b in self.blocks),
        }

    def deep_copy(self) -> "Blockchain":
        """Return a completely independent copy of this chain."""
        return Blockchain(copy.deepcopy(self.blocks))
