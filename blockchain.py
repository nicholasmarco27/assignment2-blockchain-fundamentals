import hashlib
import json
import datetime


PRIVATE_KEYS = {
    "Nico":  "key_nico",
    "Azza":  "key_azza",
    "Riyan": "key_riyan",
}


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


# Class Transaction
class Transaction:

    def __init__(self, sender, receiver, amount, signature=None):
        self.sender    = sender
        self.receiver  = receiver
        self.amount    = amount
        self.signature = signature  # None sebelum sign()

    def _message(self):
        return f"{self.sender} -> {self.receiver} : {self.amount}"

    # Digital Signature: hash dari pesan + private_key
    def sign(self, private_key):
        self.signature = sha256(self._message() + private_key)

    # Validasi digital signature transaksi
    def is_valid(self):
        if self.sender == "SYSTEM": 
            return True
        if self.sender not in PRIVATE_KEYS:
            return False
        expected = sha256(self._message() + PRIVATE_KEYS[self.sender])
        return self.signature == expected

    def to_dict(self):
        return {
            "sender":    self.sender,
            "receiver":  self.receiver,
            "amount":    self.amount,
            "signature": self.signature,
        }

    def __repr__(self):
        return f"[{self.sender} -> {self.receiver} | {self.amount} koin]"


# Class block
class Block:

    def __init__(self, index, transactions, previous_hash, nonce=0, timestamp=None, hash=None):
        self.index         = index
        self.timestamp     = timestamp or str(datetime.datetime.now())
        self.transactions  = transactions
        self.previous_hash = previous_hash
        self.nonce         = nonce
        self.hash          = hash or self.calculate_hash()

    def calculate_hash(self):
        data = {
            "index":         self.index,
            "timestamp":     self.timestamp,
            "transactions":  [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce":         self.nonce,
        }
        return sha256(json.dumps(data, sort_keys=True))

    # Proof of Work: cari nonce yang menghasilkan hash dengan prefix tertentu"
    def mine(self, difficulty):
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index":         self.index,
            "timestamp":     self.timestamp,
            "transactions":  [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce":         self.nonce,
            "hash":          self.hash,
        }

# Class Blockchain
class Blockchain:

    MINING_REWARD = 5

    def __init__(self, difficulty=3):
        self.difficulty           = difficulty
        self.pending_transactions = []
        self.chain                = [self._genesis_block()]

    def _genesis_block(self):
        return Block(0, [], "0000000000000000")

    def last_block(self):
        return self.chain[-1]

    # Validasi digital signature->masukkan transaksi ke antrian pending
    def add_transaction(self, transaction):
        if not transaction.is_valid():
            return False, f"Signature {transaction.sender} tidak valid"
        self.pending_transactions.append(transaction)
        return True, "Transaksi ditambahkan ke antrian"

    # Kemas transaksi pending jadi blok, tambah reward, terus mine
    def mine_pending(self, miner_name):

        # Reward untuk miner dari system
        reward_tx = Transaction("SYSTEM", miner_name, self.MINING_REWARD)
        self.pending_transactions.append(reward_tx)

        new_block = Block(
            index         = len(self.chain),
            transactions  = self.pending_transactions,
            previous_hash = self.last_block().hash,
        )
        new_block.mine(self.difficulty)

        self.chain.append(new_block)
        self.pending_transactions = []

        return True, new_block

    # Sinkronisasi: ganti chain jika chain dari node lain lebih panjang dan valid
    def replace_chain(self, new_chain_data):
        new_chain = []
        for block_data in new_chain_data:
            txs = [
                Transaction(
                    sender    = t["sender"],
                    receiver  = t["receiver"],
                    amount    = t["amount"],
                    signature = t["signature"],
                )
                for t in block_data["transactions"]
            ]
            block = Block(
                index         = block_data["index"],
                transactions  = txs,
                previous_hash = block_data["previous_hash"],
                nonce         = block_data["nonce"],
                timestamp     = block_data["timestamp"],
                hash          = block_data["hash"],
            )
            new_chain.append(block)

        # Cek 1: hanya ganti jika lebih panjang
        if len(new_chain) <= len(self.chain):
            return False, "Chain yang diterima tidak lebih panjang"

        # Cek 2 & 3: validasi integritas chain
        for i in range(1, len(new_chain)):
            curr = new_chain[i]
            prev = new_chain[i - 1]
            if curr.hash != curr.calculate_hash():
                return False, "Chain tidak valid (hash blok berubah)"
            if curr.previous_hash != prev.hash:
                return False, "Chain tidak valid (rantai putus)"

        # Cek 4: validasi semua signature transaksi
        for block in new_chain[1:]:
            for tx in block.transactions:
                if not tx.is_valid():
                    return False, f"Chain tidak valid (signature {tx.sender} gagal)"

        self.chain = new_chain
        return True, "Chain berhasil disinkronisasi"

    def chain_to_dict(self):
        return [block.to_dict() for block in self.chain]