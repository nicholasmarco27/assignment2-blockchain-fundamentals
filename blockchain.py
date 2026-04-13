"""
blockchain_v2.py — Upgraded dengan:
  1. Wallet Address system (ECDSA keypair → address)
  2. Real digital signature (ECDSA secp256k1)
  3. Balance checking (tolak tx jika saldo kurang)
  4. Transaction fee
  5. Chain persistence (simpan/load dari JSON)

Instalasi dependency:
  pip install ecdsa
"""

import hashlib
import json
import datetime
import os
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError

# ─────────────────────────────────────────────────────────────
# WALLET: private key → public key → address
# ─────────────────────────────────────────────────────────────


class Wallet:
    """
    Representasi wallet dengan keypair ECDSA (secp256k1, sama seperti Bitcoin).

    Atribut:
        private_key  : SigningKey  (rahasia, jangan disebar)
        public_key   : VerifyingKey
        address      : str  — "hash160" dari public key (hex 40 karakter)
        name         : str  — label opsional
    """

    def __init__(self, name: str = "", private_key_hex: str = None):
        self.name = name
        if private_key_hex:
            # Load dari hex yang sudah ada
            self.private_key = SigningKey.from_string(
                bytes.fromhex(private_key_hex), curve=SECP256k1
            )
        else:
            # Generate keypair baru
            self.private_key = SigningKey.generate(curve=SECP256k1)

        self.public_key = self.private_key.get_verifying_key()
        self.address = self._derive_address(self.public_key)

    @staticmethod
    def _derive_address(vk: VerifyingKey) -> str:
        """Address = RIPEMD160(SHA256(compressed_pubkey)) — mirip Bitcoin P2PKH."""
        pub_bytes = vk.to_string()
        sha = hashlib.sha256(pub_bytes).digest()
        ripe = hashlib.new("ripemd160", sha).hexdigest()
        return ripe  # 40-char hex

    @property
    def private_key_hex(self) -> str:
        return self.private_key.to_string().hex()

    @property
    def public_key_hex(self) -> str:
        return self.public_key.to_string().hex()

    def sign(self, message: str) -> str:
        """Tandatangani pesan, kembalikan signature sebagai hex string."""
        sig_bytes = self.private_key.sign(message.encode())
        return sig_bytes.hex()

    @staticmethod
    def verify(public_key_hex: str, message: str, signature_hex: str) -> bool:
        """Verifikasi signature dengan public key."""
        try:
            vk = VerifyingKey.from_string(
                bytes.fromhex(public_key_hex), curve=SECP256k1
            )
            sig = bytes.fromhex(signature_hex)
            vk.verify(sig, message.encode())
            return True
        except (BadSignatureError, Exception):
            return False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address": self.address,
            "public_key_hex": self.public_key_hex,
            # JANGAN simpan private_key di sini untuk keamanan
            # private_key_hex ada di file terpisah (wallet.json)
        }

    def __repr__(self):
        return f"Wallet({self.name} | addr: {self.address[:12]}...)"


# ─────────────────────────────────────────────────────────────
# TRANSACTION
# ─────────────────────────────────────────────────────────────


class Transaction:
    """
    Transaksi dengan address sebagai identitas dan ECDSA signature.

    Perubahan dari v1:
    - sender/receiver adalah ADDRESS (bukan nama)
    - signature menggunakan ECDSA (bukan sha256 sederhana)
    - public_key_sender disimpan agar verifikasi bisa dilakukan tanpa lookup
    - fee ditambahkan (opsional, default 0)
    """

    SYSTEM_ADDRESS = "0000000000000000000000000000000000000000"

    def __init__(
        self,
        sender: str,  # address pengirim
        receiver: str,  # address penerima
        amount: int | float,
        public_key_hex: str = None,  # public key pengirim (None untuk SYSTEM)
        signature: str = None,
        fee: int | float = 0,
        timestamp: str = None,
    ):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.fee = fee
        self.public_key_hex = public_key_hex
        self.signature = signature
        self.timestamp = timestamp or str(datetime.datetime.now())

    def _message(self) -> str:
        """Pesan yang ditandatangani — harus deterministik."""
        return (
            f"{self.sender}|{self.receiver}|{self.amount}|{self.fee}|{self.timestamp}"
        )

    def sign_with_wallet(self, wallet: Wallet):
        """Tandatangani transaksi ini menggunakan Wallet."""
        assert wallet.address == self.sender, "Wallet tidak cocok dengan sender address"
        self.public_key_hex = wallet.public_key_hex
        self.signature = wallet.sign(self._message())

    def is_valid(self) -> bool:
        """Verifikasi signature ECDSA."""
        if self.sender == self.SYSTEM_ADDRESS:
            return True
        if not self.signature or not self.public_key_hex:
            return False
        # Pastikan public key memang menghasilkan address yang sesuai
        derived = Wallet._derive_address(
            VerifyingKey.from_string(
                bytes.fromhex(self.public_key_hex), curve=SECP256k1
            )
        )
        if derived != self.sender:
            return False  # public key palsu
        return Wallet.verify(self.public_key_hex, self._message(), self.signature)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "fee": self.fee,
            "public_key_hex": self.public_key_hex,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            sender=d["sender"],
            receiver=d["receiver"],
            amount=d["amount"],
            fee=d.get("fee", 0),
            public_key_hex=d.get("public_key_hex"),
            signature=d.get("signature"),
            timestamp=d.get("timestamp"),
        )

    def __repr__(self):
        short = lambda a: a[:8] + "..."
        return f"[{short(self.sender)} → {short(self.receiver)} | {self.amount} koin + fee:{self.fee}]"


# ─────────────────────────────────────────────────────────────
# BLOCK (tidak banyak berubah dari v1)
# ─────────────────────────────────────────────────────────────


class Block:
    def __init__(
        self,
        index: int,
        transactions: list,
        previous_hash: str,
        nonce: int = 0,
        timestamp: str = None,
        hash: str = None,
    ):
        self.index = index
        self.timestamp = timestamp or str(datetime.datetime.now())
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash or self.calculate_hash()

    def calculate_hash(self) -> str:
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def mine(self, difficulty: int):
        """Proof of Work: cari nonce dengan hash berawalan '0' * difficulty."""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        txs = [Transaction.from_dict(t) for t in d["transactions"]]
        return cls(
            index=d["index"],
            transactions=txs,
            previous_hash=d["previous_hash"],
            nonce=d["nonce"],
            timestamp=d["timestamp"],
            hash=d["hash"],
        )


# ─────────────────────────────────────────────────────────────
# BLOCKCHAIN
# ─────────────────────────────────────────────────────────────


class Blockchain:
    MINING_REWARD = 10
    MIN_FEE = 0
    GENESIS_SUPPLY = 0  # bisa diisi untuk pre-mine

    def __init__(self, difficulty: int = 3, chain_file: str = None):
        self.difficulty = difficulty
        self.pending_transactions: list[Transaction] = []
        self.chain_file = chain_file  # path file JSON untuk persistensi
        self.chain: list[Block] = []

        if chain_file and os.path.exists(chain_file):
            self._load_chain()
        else:
            self.chain = [self._genesis_block()]

    # ── Genesis ──────────────────────────────────────────────

    def _genesis_block(self):
        reward_nico = Transaction(
            Transaction.SYSTEM_ADDRESS, "76cecdcffef45518eafeee55edf17f336d505078", 100
        )
        reward_azza = Transaction(
            Transaction.SYSTEM_ADDRESS, "53af15e34d9e4f06cefadd2a581c0e18de6ffdce", 100
        )
        reward_riyan = Transaction(
            Transaction.SYSTEM_ADDRESS, "737a88b4cc2094cff86b75bc7919ddc617cb7362", 100
        )
        return Block(0, [reward_nico, reward_azza, reward_riyan], "0000...0000")

    # ── Saldo ────────────────────────────────────────────────

    def get_balance(self, address: str) -> int | float:
        """
        Hitung saldo address dengan menelusuri seluruh chain.
        Saldo = (semua penerimaan) - (semua pengeluaran + fee)
        """
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.receiver == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount + tx.fee
        return balance

    def get_all_balances(self) -> dict:
        """Kembalikan dict {address: saldo} untuk semua address yang pernah muncul."""
        addresses = set()
        for block in self.chain:
            for tx in block.transactions:
                addresses.add(tx.sender)
                addresses.add(tx.receiver)
        addresses.discard(Transaction.SYSTEM_ADDRESS)
        return {addr: self.get_balance(addr) for addr in addresses}

    # ── Add transaction ───────────────────────────────────────

    def add_transaction(self, tx: Transaction) -> tuple[bool, str]:
        # 1. Validasi signature
        if not tx.is_valid():
            return False, f"Signature dari {tx.sender[:12]}... tidak valid"

        # 2. Cek saldo (kecuali SYSTEM)
        if tx.sender != Transaction.SYSTEM_ADDRESS:
            total_cost = tx.amount + tx.fee
            balance = self.get_balance(tx.sender)
            # Hitung juga semua pending outgoing dari sender yang sama
            pending_out = sum(
                (t.amount + t.fee)
                for t in self.pending_transactions
                if t.sender == tx.sender
            )
            if balance - pending_out < total_cost:
                return False, (
                    f"Saldo tidak cukup: tersedia {balance - pending_out}, "
                    f"dibutuhkan {total_cost}"
                )

        # 3. Cek fee minimum
        if tx.sender != Transaction.SYSTEM_ADDRESS and tx.fee < self.MIN_FEE:
            return False, f"Fee minimal {self.MIN_FEE} koin"

        self.pending_transactions.append(tx)
        return True, "Transaksi ditambahkan ke antrian"

    # ── Mining ───────────────────────────────────────────────

    def mine_pending(self, miner_address: str) -> tuple[bool, Block]:
        if not self.pending_transactions:
            return False, "Tidak ada transaksi pending"

        # Total fee dari semua transaksi pending → tambahan reward miner
        total_fee = sum(tx.fee for tx in self.pending_transactions)

        reward_tx = Transaction(
            sender=Transaction.SYSTEM_ADDRESS,
            receiver=miner_address,
            amount=self.MINING_REWARD + total_fee,
        )
        all_txs = self.pending_transactions + [reward_tx]

        new_block = Block(
            index=len(self.chain),
            transactions=all_txs,
            previous_hash=self.last_block().hash,
        )
        new_block.mine(self.difficulty)
        self.chain.append(new_block)
        self.pending_transactions = []

        # Simpan chain setelah mining
        self._save_chain()
        return True, new_block

    # ── Chain validation ─────────────────────────────────────

    def is_chain_valid(self) -> tuple[bool, str]:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.hash != curr.calculate_hash():
                return False, f"Hash blok #{i} tidak valid"
            if curr.previous_hash != prev.hash:
                return False, f"Rantai putus di blok #{i}"
            for tx in curr.transactions:
                if not tx.is_valid():
                    return False, f"Signature tidak valid di blok #{i}"
        return True, "Chain valid"

    def replace_chain(self, new_chain_data: list) -> tuple[bool, str]:
        new_chain = [Block.from_dict(d) for d in new_chain_data]

        if len(new_chain) <= len(self.chain):
            return False, "Chain yang diterima tidak lebih panjang"

        tmp = Blockchain.__new__(Blockchain)
        tmp.chain = new_chain
        ok, msg = tmp.is_chain_valid()
        if not ok:
            return False, msg

        self.chain = new_chain
        self._save_chain()
        return True, "Chain berhasil disinkronisasi"

    # ── Persistence ──────────────────────────────────────────

    def _save_chain(self):
        if not self.chain_file:
            return
        with open(self.chain_file, "w") as f:
            json.dump(self.chain_to_dict(), f, indent=2)

    def _load_chain(self):
        with open(self.chain_file) as f:
            data = json.load(f)
        self.chain = [Block.from_dict(d) for d in data]
        print(f"  [CHAIN] Dimuat dari {self.chain_file} ({len(self.chain)} blok)")

    # ── Serialisasi ──────────────────────────────────────────

    def last_block(self) -> Block:
        return self.chain[-1]

    def chain_to_dict(self) -> list:
        return [block.to_dict() for block in self.chain]


# ─────────────────────────────────────────────────────────────
# WALLET MANAGER — simpan/load daftar wallet ke file JSON
# ─────────────────────────────────────────────────────────────


class WalletManager:
    """
    Simpan dan load wallet dari file JSON.
    File format: { "wallets": [ {name, address, private_key_hex, public_key_hex}, ... ] }

    ⚠️  Di production, private key harus dienkripsi!
    """

    def __init__(self, filepath: str = "wallets.json"):
        self.filepath = filepath
        self.wallets: dict[str, Wallet] = {}  # name → Wallet
        self._load()

    def create_wallet(self, name: str) -> Wallet:
        if name in self.wallets:
            raise ValueError(f"Wallet '{name}' sudah ada")
        w = Wallet(name=name)
        self.wallets[name] = w
        self._save()
        print(f"  [WALLET] Dibuat: {name} → {w.address}")
        return w

    def get_or_create(self, name: str) -> Wallet:
        if name not in self.wallets:
            return self.create_wallet(name)
        return self.wallets[name]

    def get_by_address(self, address: str) -> Wallet | None:
        for w in self.wallets.values():
            if w.address == address:
                return w
        return None

    def _save(self):
        data = {
            "wallets": [
                {
                    "name": w.name,
                    "address": w.address,
                    "private_key_hex": w.private_key_hex,
                    "public_key_hex": w.public_key_hex,
                }
                for w in self.wallets.values()
            ]
        }
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        if not os.path.exists(self.filepath):
            return
        with open(self.filepath) as f:
            data = json.load(f)
        for entry in data.get("wallets", []):
            w = Wallet(name=entry["name"], private_key_hex=entry["private_key_hex"])
            self.wallets[w.name] = w
        print(f"  [WALLET] {len(self.wallets)} wallet dimuat dari {self.filepath}")


# ─────────────────────────────────────────────────────────────
# DEMO / QUICK TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(" BlockchainSim v2 — Demo")
    print("=" * 60)

    # 1. Buat wallet
    wm = WalletManager("demo_wallets.json")
    nico = wm.get_or_create("Nico")
    azza = wm.get_or_create("Azza")
    riyan = wm.get_or_create("Riyan")

    print(f"\nNico  address : {nico.address}")
    print(f"Azza  address : {azza.address}")
    print(f"Riyan address : {riyan.address}")

    # 2. Inisialisasi blockchain
    bc = Blockchain(difficulty=2, chain_file="demo_chain.json")

    # 3. Seed awal: mining reward untuk Nico
    seed_tx = Transaction(Transaction.SYSTEM_ADDRESS, nico.address, 100)
    bc.pending_transactions.append(seed_tx)
    bc.mine_pending(nico.address)
    print(f"\nSaldo Nico setelah mining: {bc.get_balance(nico.address)}")

    # 4. Transaksi Nico → Azza
    tx1 = Transaction(nico.address, azza.address, 30, fee=2)
    tx1.sign_with_wallet(nico)
    ok, msg = bc.add_transaction(tx1)
    print(f"\nTambah tx Nico→Azza: {msg}")

    # 5. Coba kirim melebihi saldo
    tx_lebih = Transaction(azza.address, riyan.address, 999, fee=1)
    # tx_lebih belum punya saldo, harus gagal
    # (tidak sign dulu agar tidak crash — cek saldo dulu)
    tx_lebih.public_key_hex = azza.public_key_hex
    tx_lebih.sign_with_wallet(azza)
    ok2, msg2 = bc.add_transaction(tx_lebih)
    print(f"Coba tx Azza→Riyan 999 koin: {msg2}")

    # 6. Mine
    bc.mine_pending(riyan.address)

    # 7. Tampilkan saldo
    print("\n── Saldo Akhir ──────────────────────────")
    for name, addr in [
        ("Nico", nico.address),
        ("Azza", azza.address),
        ("Riyan", riyan.address),
    ]:
        print(f"  {name:6} ({addr[:12]}...) : {bc.get_balance(addr)} koin")

    # 8. Validasi chain
    ok, msg = bc.is_chain_valid()
    print(f"\nValidasi chain: {'✓' if ok else '✗'} {msg}")
    print(f"Total blok: {len(bc.chain)}")
