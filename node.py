import sys
import requests
from flask import Flask, request, jsonify
from blockchain import Blockchain, Transaction, WalletManager

if len(sys.argv) != 3:
    print("Usage: python node_v2.py <nama> <port>")
    sys.exit(1)

NODE_NAME = sys.argv[1]
NODE_PORT = int(sys.argv[2])

ALL_NODES = {
    "Nico": "http://127.0.0.1:5001",
    "Azza": "http://127.0.0.1:5002",
    "Riyan": "http://127.0.0.1:5003",
}
PEERS = {name: url for name, url in ALL_NODES.items() if name != NODE_NAME}

app = Flask(__name__)

# Load atau buat wallet untuk node ini
wm = WalletManager(f"wallets_{NODE_NAME.lower()}.json")
wallet = wm.get_or_create(NODE_NAME)
bc = Blockchain(difficulty=3, chain_file=f"chain_{NODE_NAME.lower()}.json")

print(f"\n  ┌─────────────────────────────────────────────")
print(f"  │ Node     : {NODE_NAME}")
print(f"  │ Port     : {NODE_PORT}")
print(f"  │ Address  : {wallet.address}")
print(f"  │ Peers    : {list(PEERS.keys())}")
print(f"  └─────────────────────────────────────────────\n")


# ── Helpers ──────────────────────────────────────────────────


def broadcast(endpoint, payload):
    for name, url in PEERS.items():
        try:
            requests.post(f"{url}{endpoint}", json=payload, timeout=3)
        except requests.exceptions.ConnectionError:
            print(f"  [WARNING] Node {name} tidak bisa dihubungi")


def sinkronisasi():
    diganti = False
    for name, url in PEERS.items():
        try:
            resp = requests.get(f"{url}/chain", timeout=3)
            data = resp.json()
            ok, msg = bc.replace_chain(data["chain"])
            if ok:
                print(
                    f"  [SYNC] Chain diganti dari {name} (panjang: {data['panjang']})"
                )
                diganti = True
        except requests.exceptions.ConnectionError:
            pass
    return diganti


# ── Endpoints ─────────────────────────────────────────────────


@app.route("/", methods=["GET"])
def status():
    return jsonify(
        {
            "node": NODE_NAME,
            "address": wallet.address,
            "port": NODE_PORT,
            "panjang_chain": len(bc.chain),
            "pending_transaksi": len(bc.pending_transactions),
            "saldo": bc.get_balance(wallet.address),
        }
    )


@app.route("/wallet", methods=["GET"])
def info_wallet():
    """Lihat info wallet node ini."""
    return jsonify(
        {
            "node": NODE_NAME,
            "address": wallet.address,
            "public_key_hex": wallet.public_key_hex,
            "saldo": bc.get_balance(wallet.address),
        }
    )


@app.route("/balances", methods=["GET"])
def semua_saldo():
    """Saldo semua address yang dikenal di chain ini."""
    balances = bc.get_all_balances()
    # Coba resolve address ke nama node yang dikenal
    addr_to_name = {wm.wallets[n].address: n for n in wm.wallets}
    result = []
    for addr, bal in balances.items():
        result.append(
            {
                "address": addr,
                "name": addr_to_name.get(addr, "unknown"),
                "saldo": bal,
            }
        )
    result.sort(key=lambda x: x["saldo"], reverse=True)
    return jsonify({"balances": result})


@app.route("/transaksi", methods=["POST"])
def kirim_transaksi():
    """
    Kirim transaksi dari node ini.
    Body JSON: { "receiver_address": "...", "amount": 10, "fee": 1 }
    """
    data = request.get_json()
    receiver_address = data.get("receiver_address")
    amount = data.get("amount")
    fee = data.get("fee", 1)  # default fee 1 koin

    if not receiver_address or not amount:
        return jsonify({"error": "Butuh 'receiver_address' dan 'amount'"}), 400

    tx = Transaction(
        sender=wallet.address,
        receiver=receiver_address,
        amount=amount,
        fee=fee,
    )
    tx.sign_with_wallet(wallet)

    ok, msg = bc.add_transaction(tx)
    if not ok:
        return jsonify({"error": msg}), 400

    # Broadcast ke peer
    broadcast("/transaksi/terima", tx.to_dict())

    return jsonify(
        {
            "pesan": f"Transaksi {wallet.address[:12]}... → {receiver_address[:12]}... ({amount} koin)",
            "fee": fee,
            "signature": tx.signature[:20] + "...",
            "antrian": len(bc.pending_transactions),
        }
    )


@app.route("/transaksi/terima", methods=["POST"])
def terima_transaksi():
    data = request.get_json()
    tx = Transaction.from_dict(data)
    ok, msg = bc.add_transaction(tx)
    if not ok:
        print(f"  [VALIDASI] Transaksi dari {tx.sender[:12]}... ditolak: {msg}")
    return jsonify({"pesan": msg, "ok": ok})


@app.route("/mine", methods=["POST"])
def mine():
    ok, result = bc.mine_pending(wallet.address)
    if not ok:
        return jsonify({"error": result}), 400

    broadcast("/chain/terima-blok", result.to_dict())

    return jsonify(
        {
            "pesan": f"Blok #{result.index} berhasil di-mine oleh {NODE_NAME}",
            "miner_address": wallet.address,
            "nonce": result.nonce,
            "hash": result.hash[:20] + "...",
            "jumlah_transaksi": len(result.transactions),
            "reward": bc.MINING_REWARD,
            "saldo_baru": bc.get_balance(wallet.address),
        }
    )


@app.route("/chain/terima-blok", methods=["POST"])
def terima_blok():
    diganti = sinkronisasi()
    return jsonify(
        {
            "pesan": "Chain disinkronisasi" if diganti else "Chain sudah terbaru",
        }
    )


@app.route("/chain", methods=["GET"])
def lihat_chain():
    return jsonify(
        {
            "node": NODE_NAME,
            "panjang": len(bc.chain),
            "chain": bc.chain_to_dict(),
        }
    )


@app.route("/pending", methods=["GET"])
def lihat_pending():
    return jsonify(
        {
            "node": NODE_NAME,
            "antrian": [tx.to_dict() for tx in bc.pending_transactions],
            "jumlah": len(bc.pending_transactions),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=NODE_PORT, debug=False)
