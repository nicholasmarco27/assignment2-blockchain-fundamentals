import sys
import requests
from flask import Flask, request, jsonify
from blockchain import Blockchain, Transaction, Block, PRIVATE_KEYS

# Jalankan dengan: python node.py <nama> <port>
# Contoh: python node.py Nico  5001


if len(sys.argv) != 3:
    print("Usage: python node.py <nama> <port>")
    print("Contoh: python node.py Nico 5001")
    sys.exit(1)

NODE_NAME = sys.argv[1]
NODE_PORT = int(sys.argv[2])

# list semua node di jaringan
ALL_NODES = {
    "Nico":  "http://127.0.0.1:5001",
    "Azza":  "http://127.0.0.1:5002",
    "Riyan": "http://127.0.0.1:5003",
}
PEERS = {name: url for name, url in ALL_NODES.items() if name != NODE_NAME}

app = Flask(__name__)
bc  = Blockchain(difficulty=3)


# Broadcast ke semua peer
def broadcast(endpoint, payload):
    for name, url in PEERS.items():
        try:
            requests.post(f"{url}{endpoint}", json=payload, timeout=3)
        except requests.exceptions.ConnectionError:
            print(f"  [WARNING] Node {name} tidak bisa dihubungi")


# Minta chain dari semua peer, ambil yang terpanjang dan valid
def sinkronisasi():
    diganti = False
    for name, url in PEERS.items():
        try:
            resp = requests.get(f"{url}/chain", timeout=3)
            data = resp.json()
            ok, msg = bc.replace_chain(data["chain"])
            if ok:
                print(f"  [SYNC] Chain diganti dengan chain dari {name} (panjang: {data['panjang']})")
                diganti = True
        except requests.exceptions.ConnectionError:
            pass
    return diganti



# GET /
@app.route("/", methods=["GET"])
def status():
    return jsonify({
        "node":              NODE_NAME,
        "port":              NODE_PORT,
        "panjang_chain":     len(bc.chain),
        "pending_transaksi": len(bc.pending_transactions),
    })


# POST /transaksi
# Kirim transaksi dari node ini ke node lain
@app.route("/transaksi", methods=["POST"])
def kirim_transaksi():
    data     = request.get_json()
    receiver = data.get("receiver")
    amount   = data.get("amount")

    if not receiver or not amount:
        return jsonify({"error": "Butuh 'receiver' dan 'amount'"}), 400

    # Buat transaksi dan tandatangani dengan private key milik node ini
    tx = Transaction(NODE_NAME, receiver, amount)
    tx.sign(PRIVATE_KEYS[NODE_NAME])

    ok, msg = bc.add_transaction(tx)
    if not ok:
        return jsonify({"error": msg}), 400

    # Broadcast transaksi beserta signature-nya ke semua peer
    broadcast("/transaksi/terima", tx.to_dict())

    return jsonify({
        "pesan":     f"Transaksi {NODE_NAME} -> {receiver} ({amount} koin) ditambahkan",
        "signature": tx.signature[:20] + "...",
        "antrian":   len(bc.pending_transactions),
    })


# POST /transaksi/terima
# Terima transaksi dari node lain
@app.route("/transaksi/terima", methods=["POST"])
def terima_transaksi():
    data = request.get_json()

    tx = Transaction(
        sender    = data["sender"],
        receiver  = data["receiver"],
        amount    = data["amount"],
        signature = data["signature"],
    )

    # Validasi digital signature sebelum masuk antrian
    ok, msg = bc.add_transaction(tx)
    if not ok:
        print(f"  [VALIDASI] Transaksi dari {tx.sender} ditolak: {msg}")

    return jsonify({"pesan": msg, "ok": ok})



# POST /mine
# Mining — miner adalah NODE_NAME, dapat reward 5 koin
@app.route("/mine", methods=["POST"])
def mine():
    ok, result = bc.mine_pending(NODE_NAME)

    if not ok:
        return jsonify({"error": result}), 400

    # Broadcast blok baru → peer akan sinkronisasi chain mereka
    broadcast("/chain/terima-blok", result.to_dict())

    return jsonify({
        "pesan":            f"Blok #{result.index} berhasil di-mine oleh {NODE_NAME}",
        "nonce":            result.nonce,
        "hash":             result.hash[:20] + "...",
        "jumlah_transaksi": len(result.transactions),
        "reward":           f"{bc.MINING_REWARD} koin untuk {NODE_NAME}",
    })

# POST /chain/terima-blok
# Notifikasi dari miner bahwa ada blok baru
@app.route("/chain/terima-blok", methods=["POST"])
def terima_blok():
    diganti = sinkronisasi()
    return jsonify({
        "pesan": "Chain disinkronisasi" if diganti else "Chain sudah terbaru",
    })


# GET /chain
# Lihat seluruh isi blockchain node ini
@app.route("/chain", methods=["GET"])
def lihat_chain():
    return jsonify({
        "node":    NODE_NAME,
        "panjang": len(bc.chain),
        "chain":   bc.chain_to_dict(),
    })

# GET /pending
# Lihat antrian transaksi yang belum di-mine
@app.route("/pending", methods=["GET"])
def lihat_pending():
    return jsonify({
        "node":    NODE_NAME,
        "antrian": [tx.to_dict() for tx in bc.pending_transactions],
        "jumlah":  len(bc.pending_transactions),
    })

# main
if __name__ == "__main__":
    print(f"\n  Node '{NODE_NAME}' berjalan di port {NODE_PORT}")
    print(f"  Peers: {list(PEERS.keys())}")
    print(f"  URL: http://127.0.0.1:{NODE_PORT}\n")
    app.run(host="127.0.0.1", port=NODE_PORT, debug=False)