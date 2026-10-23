"""
integrity.py
------------
Tampers with a copy of the chain to show that changes are detected.

Analogy: A tamper-evident seal test — break a seal on a spare box and
see whether the inspector notices, while the real box stays sealed.

The real chain is NEVER altered.  All changes happen on a deep copy.
"""

import copy
import random
import hashlib
import json

from blockchain import Blockchain, Block, Transaction


# ---------------------------------------------------------------------------
# IntegrityChecker
# ---------------------------------------------------------------------------

class IntegrityChecker:
    """
    Saves an untouched copy of the chain and provides tampering experiments.

    Fields
    ------
    blockchain      : The Blockchain object being tested.
    original_chain  : Deep copy saved at construction.  Used for restoring.
    """

    def __init__(self, blockchain: Blockchain) -> None:
        self.blockchain = blockchain
        self.original_chain: list[Block] = copy.deepcopy(blockchain.blocks)

    # ------------------------------------------------------------------
    # Save / Restore
    # ------------------------------------------------------------------

    def save_original(self) -> None:
        """Re-save the current chain state (overwrite the saved copy)."""
        self.original_chain = copy.deepcopy(self.blockchain.blocks)

    def reset_experiment(self) -> None:
        """Restore the blockchain to the saved original."""
        self.blockchain.blocks = copy.deepcopy(self.original_chain)

    # ------------------------------------------------------------------
    # Tampering experiments
    # ------------------------------------------------------------------

    def tamper_copy(
        self,
        block_index: int,
        tx_index: int,
        new_amount: float,
    ) -> dict:
        """
        Make a deep copy, change one transaction amount, then verify.

        The attacker recomputes data_hash and block_hash on the altered
        block to cover their tracks — but the NEXT block still holds the
        old block_hash of the altered block, so verify_chain() catches it.

        Returns
        -------
        {
          "original_amount"  : float,
          "tampered_amount"  : float,
          "block_index"      : int,
          "tamper_type"      : "transaction_amount",
          "verification"     : dict from verify_chain()
        }
        """
        test_chain = self.blockchain.deep_copy()
        block = test_chain.blocks[block_index]

        original_amount = block.transactions[tx_index].amount
        block.transactions[tx_index].amount = new_amount

        # Attacker recomputes hashes on the altered block
        block.finalise()

        result = test_chain.verify_chain()
        return {
            "original_amount": original_amount,
            "tampered_amount": new_amount,
            "block_index": block_index,
            "tx_index": tx_index,
            "tamper_type": "transaction_amount",
            "verification": result,
        }

    def tamper_previous_hash(self, block_index: int) -> dict:
        """
        Replace the previous_hash of a block with a random value, then
        recompute that block's own block_hash and verify.

        Returns
        -------
        {
          "block_index"    : int,
          "tamper_type"    : "previous_hash",
          "verification"   : dict from verify_chain()
        }
        """
        test_chain = self.blockchain.deep_copy()
        block = test_chain.blocks[block_index]

        # Random 64-hex string (fake previous_hash)
        fake_hash = "".join(random.choices("0123456789abcdef", k=64))
        block.previous_hash = fake_hash
        # Recompute block_hash with the new previous_hash
        block.block_hash = block.compute_block_hash()

        result = test_chain.verify_chain()
        return {
            "block_index": block_index,
            "tamper_type": "previous_hash",
            "fake_previous_hash": fake_hash,
            "verification": result,
        }

    def tamper_last_block(self, tx_index: int = 0, new_amount: float = 9_999.0) -> dict:
        """
        Tamper with the very last block.  Since nothing references its
        block_hash yet, verify_chain() still passes.  This shows that
        hash-chaining alone cannot detect changes to the tail.

        Returns
        -------
        Same structure as tamper_copy().
        """
        last_idx = len(self.blockchain.blocks) - 1
        return self.tamper_copy(last_idx, tx_index, new_amount)

    # ------------------------------------------------------------------
    # Quick checks
    # ------------------------------------------------------------------

    def verify_original(self) -> dict:
        """
        Run verify_chain() on the saved (untouched) copy.

        Should always return valid: True if the chain was not modified.
        """
        original_bc = Blockchain(copy.deepcopy(self.original_chain))
        return original_bc.verify_chain()

    def verify_current(self) -> dict:
        """Run verify_chain() on the live chain."""
        return self.blockchain.verify_chain()

    def run_all_experiments(self, block_index: int = 10) -> dict:
        """
        Run three standard experiments and return their results.

        1. Change an amount in *block_index*.
        2. Change the previous_hash of *block_index*.
        3. Change the last block (should pass).
        """
        exp1 = self.tamper_copy(block_index, tx_index=0, new_amount=9_999.0)
        exp2 = self.tamper_previous_hash(block_index)
        exp3 = self.tamper_last_block(tx_index=0, new_amount=9_999.0)
        return {
            "tamper_amount": exp1,
            "tamper_prev_hash": exp2,
            "tamper_last_block": exp3,
        }

    def __repr__(self) -> str:
        n = len(self.blockchain.blocks)
        return f"IntegrityChecker(chain_length={n})"
