# Assignment 02. Blockchain Fundamentals

## Kelompok

| NRP        | Nama                        |
| ---------- | --------------------------- |
| 5027221042 | Nicholas Marco Weinandra    |
| 5027231071 | Azza Farichi Tjahjono       |
| 5025221100 | Riyanda Cavin Sinambela     |
| 5027221067 | Muhammad Rifqi Oktaviansyah |

---

## Struktur Direktori

```
assignment2-blockchain-fundamentals/
├── blockchain.py
├── node.py
├── dashboard.py
├── requirements.txt
└── README.md
```

> File JSON berikut dibuat otomatis saat node pertama kali dijalankan:

> `wallets_<nama>.json` — keypair wallet node  
> `chain_<nama>.json` — chain node (persistent)

---

## Cara Menjalankan

### 1. Install Dependency

```bash
pip install -r requirements.txt
```

`requirements.txt`:

```
flask
requests
ecdsa
```

### 2. Jalankan 3 Node (masing-masing di terminal berbeda)

**Terminal 1 — Node Nico (port 5001)**

```bash
python node.py Nico 5001
```

**Terminal 2 — Node Azza (port 5002)**

```bash
python node.py Azza 5002
```

**Terminal 3 — Node Riyan (port 5003)**

```bash
python node.py Riyan 5003
```

Saat pertama jalan, tiap node akan menampilkan address wallet-nya di terminal:

```
┌─────────────────────────────────────────────
│ Node     : Nico
│ Port     : 5001
│ Address  : xxx...
│ Peers    : ['Azza', 'Riyan']
└─────────────────────────────────────────────
```

### 3. Jalankan Dashboard GUI

```bash
python dashboard_v2.py
```

> **Catatan:** Ketiga node harus berjalan bersamaan agar fitur sinkronisasi bekerja dengan baik.

### Reset Chain

Untuk memulai ulang dari genesis block, hapus file JSON yang dibuat otomatis:

```bash
rm wallets_*.json chain_*.json
```

---

## API Endpoints

| Method | Endpoint             | Deskripsi                                     |
| ------ | -------------------- | --------------------------------------------- |
| GET    | `/`                  | Status node (termasuk address & saldo)        |
| GET    | `/wallet`            | Info wallet node (address, public key, saldo) |
| GET    | `/balances`          | Saldo semua address yang dikenal di chain     |
| POST   | `/transaksi`         | Kirim transaksi baru                          |
| POST   | `/transaksi/terima`  | Terima transaksi dari peer (internal)         |
| POST   | `/mine`              | Mining blok baru                              |
| POST   | `/chain/terima-blok` | Notifikasi blok baru dari peer (internal)     |
| GET    | `/chain`             | Lihat seluruh blockchain                      |
| GET    | `/pending`           | Lihat antrian transaksi pending               |

---

## Fitur Blockchain

### 1. Wallet & Address System

Setiap node memiliki keypair ECDSA (kurva `secp256k1`, sama seperti Bitcoin). Address diturunkan dari public key menggunakan:

```
Address = RIPEMD160(SHA256(public_key))
```

Wallet disimpan secara persisten di file `wallets_<nama>.json` dan dimuat kembali saat node restart. Identitas node tidak lagi menggunakan nama string langsung, melainkan address 40-karakter hex.

```
GET http://127.0.0.1:5001/wallet
```

Contoh response:

```json
{
  "node": "Nico",
  "address": "xxx...",
  "public_key_hex": "xxx...",
  "saldo": 20
}
```

### 2. Real Digital Signature (ECDSA)

Signature transaksi menggunakan ECDSA — bukan lagi `sha256(pesan + private_key)`. Proses verifikasi:

1. Cek signature valid terhadap pesan menggunakan public key pengirim
2. Pastikan public key menghasilkan address yang sesuai dengan `sender` (cegah spoofing)

Kirim transaksi menggunakan `receiver_address`:

```
POST http://127.0.0.1:5001/transaksi
```

Body:

```json
{
  "receiver_address": "xxx...",
  "amount": 10,
  "fee": 1
}
```

Contoh response:

```json
{
  "pesan": "Transaksi 3a7f9c2b... → b2e84f01... (10 koin)",
  "fee": 1,
  "signature": "xxxx...",
  "antrian": 1
}
```

### 3. Validasi Saldo

Sebelum transaksi masuk ke antrian, sistem memverifikasi:

- Saldo address pengirim mencukupi `amount + fee`
- Transaksi pending yang belum di-mine ikut diperhitungkan (cegah double-spend di mempool)

Contoh penolakan karena saldo kurang:

```json
{
  "error": "Saldo tidak cukup: tersedia 5, dibutuhkan 50"
}
```

Cek saldo semua address:

```
GET http://127.0.0.1:5001/balances
```

Contoh response:

```json
{
  "balances": [
    { "address": "xxx...", "name": "Nico", "saldo": 20 },
    { "address": "xxx...", "name": "Azza", "saldo": 9 },
    { "address": "xxx...", "name": "Riyan", "saldo": 10 }
  ]
}
```

### 4. Transaction Fee

Setiap transaksi dapat menyertakan `fee`. Total fee dari semua transaksi dalam satu blok ditambahkan ke reward miner.

```
Reward miner = MINING_REWARD (10 koin) + total fee blok
```

### 5. Mining & Proof of Work

Mine semua transaksi pending menjadi blok baru. Proof of Work mencari nonce yang menghasilkan hash dengan prefix `"000"` (difficulty=3).

```
POST http://127.0.0.1:5001/mine
```

Contoh response:

```json
{
  "pesan": "Blok #1 berhasil di-mine oleh Nico",
  "miner_address": "3a7f9c2b...",
  "nonce": 4821,
  "hash": "000c3f91b2...",
  "jumlah_transaksi": 2,
  "reward": 10,
  "saldo_baru": 20
}
```

### 6. Chain Persistence

Chain disimpan otomatis ke file JSON setelah setiap mining. Saat node restart, chain dimuat kembali sehingga data tidak hilang.

### 7. Sinkronisasi Antar Node

Setelah mining berhasil, blok di-broadcast ke semua peer. Peer menjalankan `replace_chain()` — chain hanya diganti jika chain yang diterima **lebih panjang** dan **seluruh signature valid**.

---

## Perbandingan sebelum vs sesudah

| Fitur             | sebelum                       | sesudah                              |
| ----------------- | ----------------------------- | ------------------------------------ |
| Identitas node    | Nama string (`"Nico"`)        | Wallet address (`"3a7f9c..."`)       |
| Digital signature | `SHA256(pesan + private_key)` | ECDSA secp256k1                      |
| Validasi saldo    | ✗ Tidak ada                   | ✓ Cek saldo sebelum tambah transaksi |
| Transaction fee   | ✗ Tidak ada                   | ✓ Fee masuk ke reward miner          |
| Persistensi chain | ✗ Hilang saat restart         | ✓ Auto simpan/load JSON              |
| Endpoint saldo    | ✗ Tidak ada                   | ✓ `/wallet` dan `/balances`          |
| Mining reward     | 5 koin                        | 10 koin + total fee blok             |

---

## Ringkasan Pengujian

| #   | Fitur                                  | Endpoint                 | Status                |
| --- | -------------------------------------- | ------------------------ | --------------------- |
| 1   | Status node (termasuk address & saldo) | `GET /`                  | ✅ Berhasil           |
| 2   | Info wallet node                       | `GET /wallet`            | ✅ Berhasil           |
| 3   | Saldo semua address                    | `GET /balances`          | ✅ Berhasil           |
| 4   | Kirim transaksi via address            | `POST /transaksi`        | ✅ Berhasil           |
| 5   | Tolak transaksi — saldo kurang         | `POST /transaksi`        | ✅ Berhasil (ditolak) |
| 6   | Tolak transaksi — signature palsu      | `POST /transaksi/terima` | ✅ Berhasil (ditolak) |
| 7   | Mining + fee reward                    | `POST /mine`             | ✅ Berhasil           |
| 8   | Persistensi chain saat restart         | —                        | ✅ Berhasil           |
| 9   | Sinkronisasi antar node                | `GET /chain`             | ✅ Berhasil           |
