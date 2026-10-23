
class DivyCoin:
    def __init__(self):
        self.balances = {
            "Alice": 500,
            "Bob": 300,
            "Carol": 200
        }
        self.transactions = []

    def transfer(self, sender, receiver, amount):
        if sender not in self.balances:
            print("Invalid sender")
            return

        if receiver not in self.balances:
            print("Invalid receiver")
            return

        if amount <= 0:
            print("Amount must be positive")
            return

        if self.balances[sender] < amount:
            print("Insufficient balance")
            return

        self.balances[sender] -= amount
        self.balances[receiver] += amount

        self.transactions.append(
            (sender, receiver, amount)
        )

        print("Transaction successful")

coin = DivyCoin()

coin.transfer("Alice", "Bob", 50)
coin.transfer("Bob", "Carol", 25)

print("\nFinal balances:")
for name, balance in coin.balances.items():
    print(name, ":", balance, "DVC")

print("\nTransaction history:")
for transaction in coin.transactions:
    print(transaction)
