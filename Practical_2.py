
import hashlib
import json
import time

class Block:
    def __init__(self, index, data, previous_hash):
        self.index = index
        self.timestamp = time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        content = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True)

        return hashlib.sha256(
            content.encode()
        ).hexdigest()


genesis = Block(0, "Genesis Block", "0")
block1 = Block(1, "Alice pays Bob", genesis.hash)
block2 = Block(2, "Bob pays Carol", block1.hash)

for block in [genesis, block1, block2]:
    print("Block:", block.index)
    print("Data:", block.data)
    print("Previous Hash:", block.previous_hash)
    print("Current Hash:", block.hash)
    print()
