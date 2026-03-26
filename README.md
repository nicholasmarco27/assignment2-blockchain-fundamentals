# Assignment 02. Blockchain Fundamentals
## Kelompok
| NRP | Nama |
| ------ | ------ |
| 5027221042 | Nicholas Marco Weinandra |
| 5027231071 | Azza Farichi Tjahjono    |
| 50 | Riyan |

## Cara Menjalankan
1. Install Dependency

    ```
    pip install -r requirements.txt
    ```

2. Jalankan Node di 3 Terminal Berbeda
    ```
    python node.py Nico 5001
    python node.py Azza 5002
    python node.py Riyan 5003
    ```

## API Endpoints

| Method | Endpoint | Deskripsi |
| ------ | -------- | --------- |
| GET | `/` | Status node |
| POST | `/transaksi` | Kirim transaksi baru |
| POST | `/transaksi/terima` | Terima transaksi dari peer (internal) |
| POST | `/mine` | Mining blok baru |
| POST | `/chain/terima-blok` | Notifikasi blok baru dari peer (internal) |
| GET | `/chain` | Lihat seluruh blockchain |
| GET | `/pending` | Lihat antrian transaksi pending |

## Fitur Blockchain

### 1. Penambahan Transaksi
Kirim transaksi dari salah satu node. Node akan menandatangani transaksi secara otomatis menggunakan private key miliknya, lalu mem-broadcast ke semua peer.

```
POST http://127.0.0.1:5001/transaksi
```

Body:
```json
{
  "receiver": "Azza",
  "amount": 10
}
```

Contoh response:
```json
{
  "pesan": "Transaksi Nico -> Azza (10 koin) ditambahkan",
  "signature": "a3f9d1c7b2e84f01a9...",
  "antrian": 1
}
```

### 2. Mining
Mine semua transaksi yang ada di antrian menjadi sebuah blok baru. Miner mendapat reward **5 koin** dari sistem. Setelah berhasil, blok di-broadcast ke semua peer agar mereka menyinkronisasi chain.

```
POST http://127.0.0.1:5001/mine
```

Contoh response:
```json
{
  "pesan": "Blok #1 berhasil di-mine oleh Nico",
  "nonce": 3271,
  "hash": "000a4f91b2c3d7e8f1...",
  "jumlah_transaksi": 2,
  "reward": "5 koin untuk Nico"
}
```

### 3. Lihat Blockchain
Melihat seluruh isi blockchain pada node tertentu.

```
GET http://127.0.0.1:5001/chain
```

Contoh response:
```json
{
  "node": "Nico",
  "panjang": 2,
  "chain": [
    {
      "index": 0,
      "timestamp": "...",
      "transactions": [],
      "previous_hash": "0000000000000000",
      "nonce": 0,
      "hash": "..."
    },
    {
      "index": 1,
      "transactions": [...],
      "previous_hash": "...",
      "nonce": 3271,
      "hash": "000a4f91b2c3d7e8f1..."
    }
  ]
}
```

### 4. Lihat Antrian Transaksi
Melihat transaksi yang sudah masuk tapi belum di-mine.

```
GET http://127.0.0.1:5001/pending
```

Contoh response:
```json
{
  "node": "Nico",
  "jumlah": 1,
  "antrian": [
    {
      "sender": "Nico",
      "receiver": "Azza",
      "amount": 10,
      "signature": "a3f9d1c7b2e84f01a9..."
    }
  ]
}
```

### 5. Status Node

```
GET http://127.0.0.1:5001/
```

Contoh response:
```json
{
  "node": "Nico",
  "port": 5001,
  "panjang_chain": 2,
  "pending_transaksi": 0
}
```
