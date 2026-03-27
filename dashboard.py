"""
Blockchain Node Dashboard — Python Tkinter
Jalankan: python dashboard.py
Pastikan node sudah berjalan di port 5001/5002/5003
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import requests
import json
import datetime

# ── Konfigurasi ────────────────────────────────────────────────────────────────
NODES = {
    "Nico": {"port": 5001, "url": "http://127.0.0.1:5001", "key": "key_nico"},
    "Azza": {"port": 5002, "url": "http://127.0.0.1:5002", "key": "key_azza"},
    "Riyan": {"port": 5003, "url": "http://127.0.0.1:5003", "key": "key_riyan"},
}

# ── Palet warna ────────────────────────────────────────────────────────────────
C = {
    "bg": "#0f1117",
    "bg2": "#1a1d27",
    "bg3": "#232635",
    "border": "#2e3347",
    "accent": "#6366f1",
    "accent2": "#818cf8",
    "gold": "#f59e0b",
    "green": "#22c55e",
    "red": "#ef4444",
    "muted": "#6b7280",
    "text": "#e2e8f0",
    "text2": "#94a3b8",
    "pending_bg": "#2d2006",
    "pending_fg": "#fbbf24",
    "confirm_bg": "#052e16",
    "confirm_fg": "#4ade80",
    "system_bg": "#1e1b4b",
    "system_fg": "#a5b4fc",
}


# ══════════════════════════════════════════════════════════════════════════════
class BlockchainDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Blockchain Dashboard")
        self.geometry("1100x750")
        self.minsize(900, 650)
        self.configure(bg=C["bg"])

        # State
        self.current_node = tk.StringVar(value="Nico")
        self.node_status = {
            n: {"online": False, "chain_len": 0, "pending": 0} for n in NODES
        }
        self.chain_data = []
        self.pending_data = []
        self.logs = []
        self._poll_job = None

        self._setup_styles()
        self._build_ui()
        self._start_polling()

    # ── Styles ─────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.style.configure("Dark.TFrame", background=C["bg"])
        self.style.configure("Card.TFrame", background=C["bg2"], relief="flat")
        self.style.configure(
            "Dark.TLabel",
            background=C["bg"],
            foreground=C["text"],
            font=("Courier New", 11),
        )
        self.style.configure(
            "Card.TLabel",
            background=C["bg2"],
            foreground=C["text"],
            font=("Courier New", 11),
        )
        self.style.configure(
            "Muted.TLabel",
            background=C["bg2"],
            foreground=C["muted"],
            font=("Courier New", 10),
        )
        self.style.configure(
            "Big.TLabel",
            background=C["bg2"],
            foreground=C["text"],
            font=("Courier New", 22, "bold"),
        )
        self.style.configure(
            "Header.TLabel",
            background=C["bg"],
            foreground=C["text"],
            font=("Courier New", 14, "bold"),
        )
        self.style.configure(
            "Section.TLabel",
            background=C["bg2"],
            foreground=C["muted"],
            font=("Courier New", 9),
        )
        self.style.configure(
            "Online.TLabel",
            background=C["bg2"],
            foreground=C["green"],
            font=("Courier New", 11, "bold"),
        )
        self.style.configure(
            "Offline.TLabel",
            background=C["bg2"],
            foreground=C["muted"],
            font=("Courier New", 11),
        )
        self.style.configure(
            "Accent.TLabel",
            background=C["bg"],
            foreground=C["accent2"],
            font=("Courier New", 12, "bold"),
        )

        # Notebook (tabs)
        self.style.configure("TNotebook", background=C["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=C["bg3"],
            foreground=C["muted"],
            font=("Courier New", 11),
            padding=[16, 6],
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", C["accent"]), ("active", C["bg2"])],
            foreground=[("selected", "white"), ("active", C["text"])],
        )

        # Treeview (chain explorer)
        self.style.configure(
            "Chain.Treeview",
            background=C["bg2"],
            foreground=C["text"],
            fieldbackground=C["bg2"],
            rowheight=28,
            font=("Courier New", 10),
        )
        self.style.configure(
            "Chain.Treeview.Heading",
            background=C["bg3"],
            foreground=C["muted"],
            font=("Courier New", 10, "bold"),
            relief="flat",
        )
        self.style.map(
            "Chain.Treeview",
            background=[("selected", C["accent"])],
            foreground=[("selected", "white")],
        )

        # Scrollbar
        self.style.configure(
            "Dark.Vertical.TScrollbar",
            background=C["bg3"],
            troughcolor=C["bg2"],
            arrowcolor=C["muted"],
            borderwidth=0,
        )

        # Entry / Combobox
        self.style.configure(
            "Dark.TCombobox",
            fieldbackground=C["bg3"],
            background=C["bg3"],
            foreground=C["text"],
            selectbackground=C["accent"],
            font=("Courier New", 11),
        )

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top bar
        top = tk.Frame(self, bg=C["bg"], pady=10)
        top.pack(fill="x", padx=16)

        tk.Label(
            top,
            text="⬡ BlockchainSim",
            bg=C["bg"],
            fg=C["accent2"],
            font=("Courier New", 16, "bold"),
        ).pack(side="left")
        tk.Label(
            top,
            text="  distributed node dashboard",
            bg=C["bg"],
            fg=C["muted"],
            font=("Courier New", 11),
        ).pack(side="left")
        self.lbl_time = tk.Label(
            top, text="", bg=C["bg"], fg=C["muted"], font=("Courier New", 10)
        )
        self.lbl_time.pack(side="right")
        self._tick_clock()

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # ── Node tabs
        tab_frame = tk.Frame(self, bg=C["bg"], pady=8)
        tab_frame.pack(fill="x", padx=16)
        tk.Label(
            tab_frame, text="NODE:", bg=C["bg"], fg=C["muted"], font=("Courier New", 10)
        ).pack(side="left", padx=(0, 8))
        self.node_btns = {}
        for name in NODES:
            btn = tk.Button(
                tab_frame,
                text=f"● {name}  :{NODES[name]['port']}",
                bg=C["bg3"],
                fg=C["muted"],
                activebackground=C["accent"],
                activeforeground="white",
                font=("Courier New", 11),
                relief="flat",
                bd=0,
                padx=14,
                pady=6,
                cursor="hand2",
                command=lambda n=name: self._switch_node(n),
            )
            btn.pack(side="left", padx=3)
            self.node_btns[name] = btn
        self._highlight_tab("Nico")

        # ── Main area (left + right)
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=8)

        left = tk.Frame(body, bg=C["bg"], width=340)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

    # ── Left panel ─────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # Stat cards
        stats = self._card(parent, label="")
        stats.pack(fill="x", pady=(0, 8))
        row = tk.Frame(stats, bg=C["bg2"])
        row.pack(fill="x")

        self.stat_frames = {}
        for title, key, color in [
            ("STATUS", "status", C["green"]),
            ("BLOCKS", "chain_len", C["accent2"]),
            ("PENDING", "pending", C["gold"]),
        ]:
            f = tk.Frame(row, bg=C["bg3"], padx=12, pady=10)
            f.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            tk.Label(
                f, text=title, bg=C["bg3"], fg=C["muted"], font=("Courier New", 9)
            ).pack(anchor="w")
            lbl = tk.Label(
                f, text="—", bg=C["bg3"], fg=color, font=("Courier New", 20, "bold")
            )
            lbl.pack(anchor="w")
            self.stat_frames[key] = lbl

        # Send transaction
        tx_card = self._card(parent, label="SEND TRANSACTION")
        tx_card.pack(fill="x", pady=(0, 8))

        tk.Label(
            tx_card,
            text="Receiver",
            bg=C["bg2"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=8)
        self.cmb_receiver = ttk.Combobox(
            tx_card, font=("Courier New", 11), style="Dark.TCombobox", state="readonly"
        )
        self.cmb_receiver.pack(fill="x", padx=8, pady=(2, 8))
        self._update_receiver_list()

        tk.Label(
            tx_card,
            text="Amount (koin)",
            bg=C["bg2"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=8)
        self.ent_amount = tk.Entry(
            tx_card,
            bg=C["bg3"],
            fg=C["text"],
            insertbackground=C["text"],
            font=("Courier New", 12),
            relief="flat",
            bd=6,
        )
        self.ent_amount.pack(fill="x", padx=8, pady=(2, 10))

        self._btn(
            tx_card, "  ↗  Kirim Transaksi", self._send_tx, bg=C["accent"], fg="white"
        ).pack(fill="x", padx=8, pady=(0, 8))

        # Mine & Refresh
        act_card = self._card(parent, label="ACTIONS")
        act_card.pack(fill="x", pady=(0, 8))

        self._btn(
            act_card, "  ⛏  Mine Blok", self._do_mine, bg=C["gold"], fg="#1a1a00"
        ).pack(fill="x", padx=8, pady=(4, 4))
        self._btn(
            act_card, "  ↺  Refresh Data", self._do_refresh, bg=C["bg3"], fg=C["text"]
        ).pack(fill="x", padx=8, pady=(0, 8))

        # Pending list
        pend_card = self._card(parent, label="ANTRIAN PENDING")
        pend_card.pack(fill="both", expand=True)

        self.pend_text = tk.Text(
            pend_card,
            bg=C["bg3"],
            fg=C["text"],
            font=("Courier New", 10),
            relief="flat",
            state="disabled",
            wrap="none",
            height=6,
        )
        self.pend_text.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.pend_text.tag_configure("pending", foreground=C["pending_fg"])
        self.pend_text.tag_configure("system", foreground=C["system_fg"])
        self.pend_text.tag_configure("muted", foreground=C["muted"])

    # ── Right panel ────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        nb = ttk.Notebook(parent, style="TNotebook")
        nb.pack(fill="both", expand=True)

        # Tab 1: Chain Explorer
        chain_tab = tk.Frame(nb, bg=C["bg2"])
        nb.add(chain_tab, text=" ⬡  Chain Explorer ")
        self._build_chain_tab(chain_tab)

        # Tab 2: Network
        net_tab = tk.Frame(nb, bg=C["bg2"])
        nb.add(net_tab, text=" ⇆  Network ")
        self._build_network_tab(net_tab)

        # Tab 3: Activity Log
        log_tab = tk.Frame(nb, bg=C["bg2"])
        nb.add(log_tab, text=" ≡  Activity Log ")
        self._build_log_tab(log_tab)

    def _build_chain_tab(self, parent):
        # Treeview for blocks
        cols = ("#", "hash", "prev", "txs", "nonce", "timestamp")
        self.tree = ttk.Treeview(
            parent,
            columns=cols,
            show="headings",
            style="Chain.Treeview",
            selectmode="browse",
        )
        col_cfg = [
            ("#", 50, "center"),
            ("hash", 180, "w"),
            ("prev", 130, "w"),
            ("txs", 50, "center"),
            ("nonce", 70, "center"),
            ("timestamp", 160, "w"),
        ]
        for col, w, anc in col_cfg:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=w, anchor=anc, stretch=(col == "hash"))

        vsb = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.tree.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        vsb.pack(side="left", fill="y", pady=8, padx=(0, 4))

        # Detail pane (click a block)
        detail_frame = tk.Frame(parent, bg=C["bg3"], width=240)
        detail_frame.pack(side="left", fill="y", padx=(0, 8), pady=8)
        detail_frame.pack_propagate(False)

        tk.Label(
            detail_frame,
            text="BLOCK DETAIL",
            bg=C["bg3"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=10, pady=(10, 4))

        self.detail_text = tk.Text(
            detail_frame,
            bg=C["bg3"],
            fg=C["text"],
            font=("Courier New", 10),
            relief="flat",
            wrap="word",
            state="disabled",
        )
        self.detail_text.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.detail_text.tag_configure("key", foreground=C["muted"])
        self.detail_text.tag_configure("val", foreground=C["text"])
        self.detail_text.tag_configure("hash", foreground=C["accent2"])
        self.detail_text.tag_configure("reward", foreground=C["system_fg"])
        self.detail_text.tag_configure("tx", foreground=C["confirm_fg"])
        self.detail_text.tag_configure("sep", foreground=C["border"])

        self.tree.bind("<<TreeviewSelect>>", self._on_block_select)

    def _build_network_tab(self, parent):
        tk.Label(
            parent,
            text="PEER NODES",
            bg=C["bg2"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.peer_frames = {}
        for name in NODES:
            f = tk.Frame(parent, bg=C["bg3"], pady=14, padx=16)
            f.pack(fill="x", padx=12, pady=5)

            header = tk.Frame(f, bg=C["bg3"])
            header.pack(fill="x")

            dot_lbl = tk.Label(
                header, text="●", bg=C["bg3"], fg=C["muted"], font=("Courier New", 14)
            )
            dot_lbl.pack(side="left")
            tk.Label(
                header,
                text=f"  {name}",
                bg=C["bg3"],
                fg=C["text"],
                font=("Courier New", 13, "bold"),
            ).pack(side="left")
            url_lbl = tk.Label(
                header,
                text=NODES[name]["url"],
                bg=C["bg3"],
                fg=C["muted"],
                font=("Courier New", 10),
            )
            url_lbl.pack(side="right")

            info_lbl = tk.Label(
                f,
                text="tidak terhubung",
                bg=C["bg3"],
                fg=C["muted"],
                font=("Courier New", 10),
            )
            info_lbl.pack(anchor="w", pady=(4, 0))

            self.peer_frames[name] = {"dot": dot_lbl, "info": info_lbl}

    def _build_log_tab(self, parent):
        btn_row = tk.Frame(parent, bg=C["bg2"])
        btn_row.pack(fill="x", padx=10, pady=8)
        self._btn(
            btn_row, "Hapus Log", self._clear_log, bg=C["bg3"], fg=C["muted"]
        ).pack(side="right")

        self.log_text = tk.Text(
            parent,
            bg=C["bg3"],
            fg=C["text"],
            font=("Courier New", 10),
            relief="flat",
            state="disabled",
            wrap="none",
        )
        vsb = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.log_text.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.log_text.configure(yscrollcommand=vsb.set)
        self.log_text.pack(
            side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10)
        )
        vsb.pack(side="left", fill="y", pady=(0, 10), padx=(0, 6))

        self.log_text.tag_configure("ok", foreground=C["green"])
        self.log_text.tag_configure("err", foreground=C["red"])
        self.log_text.tag_configure("warn", foreground=C["gold"])
        self.log_text.tag_configure("info", foreground=C["text2"])
        self.log_text.tag_configure("time", foreground=C["muted"])

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _card(self, parent, label=""):
        wrap = tk.Frame(parent, bg=C["bg2"], padx=0, pady=0)
        if label:
            tk.Label(
                wrap, text=label, bg=C["bg2"], fg=C["muted"], font=("Courier New", 9)
            ).pack(anchor="w", padx=10, pady=(8, 2))
        return wrap

    def _btn(self, parent, text, command, bg=None, fg=None):
        bg = bg or C["bg3"]
        fg = fg or C["text"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=C["accent"],
            activeforeground="white",
            font=("Courier New", 11),
            relief="flat",
            bd=0,
            pady=8,
            cursor="hand2",
        )

    def _highlight_tab(self, name):
        for n, btn in self.node_btns.items():
            if n == name:
                btn.configure(bg=C["accent"], fg="white")
            else:
                btn.configure(bg=C["bg3"], fg=C["muted"])

    def _update_receiver_list(self):
        node = self.current_node.get()
        receivers = [n for n in NODES if n != node]
        self.cmb_receiver["values"] = receivers
        if receivers:
            self.cmb_receiver.set(receivers[0])

    def _tick_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.lbl_time.configure(text=now)
        self.after(1000, self._tick_clock)

    # ── Node switching ─────────────────────────────────────────────────────────
    def _switch_node(self, name):
        self.current_node.set(name)
        self._highlight_tab(name)
        self._update_receiver_list()
        self.chain_data = []
        self.pending_data = []
        self._refresh_chain_ui()
        self._refresh_pending_ui()
        self._do_refresh()

    # ── Polling ────────────────────────────────────────────────────────────────
    def _start_polling(self):
        self._poll()

    def _poll(self):
        threading.Thread(target=self._poll_all_status, daemon=True).start()
        self._poll_job = self.after(5000, self._poll)

    def _poll_all_status(self):
        for name in NODES:
            try:
                r = requests.get(f"{NODES[name]['url']}/", timeout=2)
                d = r.json()
                self.node_status[name] = {
                    "online": True,
                    "chain_len": d["panjang_chain"],
                    "pending": d["pending_transaksi"],
                }
            except Exception:
                self.node_status[name] = {"online": False, "chain_len": 0, "pending": 0}
        self.after(0, self._refresh_status_ui)

    # ── API calls ──────────────────────────────────────────────────────────────
    def _do_refresh(self):
        self._add_log("info", f"Memperbarui data node {self.current_node.get()}...")
        threading.Thread(target=self._fetch_node_data, daemon=True).start()

    def _fetch_node_data(self):
        node = self.current_node.get()
        url = NODES[node]["url"]
        try:
            rc = requests.get(f"{url}/chain", timeout=3)
            rp = requests.get(f"{url}/pending", timeout=3)
            self.chain_data = rc.json().get("chain", [])
            self.pending_data = rp.json().get("antrian", [])
            chain_len = rc.json().get("panjang", len(self.chain_data))
            self.node_status[node]["chain_len"] = chain_len
            self.node_status[node]["pending"] = len(self.pending_data)
            self.node_status[node]["online"] = True
            self.after(0, self._refresh_chain_ui)
            self.after(0, self._refresh_pending_ui)
            self.after(0, self._refresh_status_ui)
            self.after(0, lambda: self._add_log("ok", "Data berhasil diperbarui"))
        except Exception as e:
            self.node_status[node]["online"] = False
            self.after(0, self._refresh_status_ui)
            self.after(
                0, lambda: self._add_log("err", f"Gagal terhubung ke {node}: {e}")
            )

    def _send_tx(self):
        receiver = self.cmb_receiver.get()
        amount = self.ent_amount.get().strip()
        if not receiver or not amount:
            messagebox.showwarning("Input Error", "Isi receiver dan amount!")
            return
        try:
            amount_val = int(amount)
            if amount_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Amount harus angka positif!")
            return

        node = self.current_node.get()
        self._add_log("info", f"Mengirim: {node} → {receiver} ({amount_val} koin)")

        def task():
            try:
                r = requests.post(
                    f"{NODES[node]['url']}/transaksi",
                    json={"receiver": receiver, "amount": amount_val},
                    timeout=5,
                )
                d = r.json()
                if r.ok:
                    self.after(
                        0,
                        lambda: self._add_log(
                            "ok", d.get("pesan", "Transaksi terkirim")
                        ),
                    )
                    self.after(0, lambda: self.ent_amount.delete(0, "end"))
                    self.after(0, self._do_refresh)
                else:
                    self.after(
                        0,
                        lambda: self._add_log("err", d.get("error", "Transaksi gagal")),
                    )
            except Exception as e:
                self.after(0, lambda: self._add_log("err", f"Koneksi gagal: {e}"))

        threading.Thread(target=task, daemon=True).start()

    def _do_mine(self):
        node = self.current_node.get()
        self._add_log("warn", f"Mining blok baru oleh {node}... (harap tunggu)")

        def task():
            try:
                r = requests.post(f"{NODES[node]['url']}/mine", timeout=60)
                d = r.json()
                if r.ok:
                    msg = d.get("pesan", "Blok berhasil di-mine")
                    nonce = d.get("nonce", "?")
                    self.after(
                        0, lambda: self._add_log("ok", f"{msg}  |  nonce: {nonce}")
                    )
                    self.after(0, self._do_refresh)
                else:
                    self.after(
                        0, lambda: self._add_log("err", d.get("error", "Mining gagal"))
                    )
            except Exception as e:
                self.after(
                    0, lambda: self._add_log("err", f"Mining timeout/gagal: {e}")
                )

        threading.Thread(target=task, daemon=True).start()

    # ── UI refresh ─────────────────────────────────────────────────────────────
    def _refresh_status_ui(self):
        node = self.current_node.get()
        status = self.node_status[node]
        online = status["online"]

        self.stat_frames["status"].configure(
            text="ONLINE" if online else "OFFLINE",
            fg=C["green"] if online else C["red"],
        )
        self.stat_frames["chain_len"].configure(text=str(status["chain_len"]))
        self.stat_frames["pending"].configure(text=str(status["pending"]))

        # Update node tab dots
        for name, btn in self.node_btns.items():
            dot = "●" if self.node_status[name]["online"] else "○"
            label = f"{dot} {name}  :{NODES[name]['port']}"
            if name == node:
                btn.configure(text=label, bg=C["accent"], fg="white")
            else:
                btn.configure(
                    text=label,
                    bg=C["bg3"],
                    fg=C["green"] if self.node_status[name]["online"] else C["muted"],
                )

        # Update network tab
        for name, widgets in self.peer_frames.items():
            st = self.node_status[name]
            if st["online"]:
                widgets["dot"].configure(fg=C["green"])
                widgets["info"].configure(
                    text=f"chain: {st['chain_len']} blok   |   pending: {st['pending']}",
                    fg=C["text2"],
                )
            else:
                widgets["dot"].configure(fg=C["muted"])
                widgets["info"].configure(text="tidak terhubung", fg=C["muted"])

    def _refresh_chain_ui(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        for blk in reversed(self.chain_data):
            idx = blk.get("index", "?")
            hash_ = blk.get("hash", "")[:20] + "..."
            prev = blk.get("previous_hash", "")[:14] + "..."
            tx_count = len(blk.get("transactions", []))
            nonce = blk.get("nonce", 0)
            ts = blk.get("timestamp", "")[:19]
            tag = "genesis" if idx == 0 else ""
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(idx, hash_, prev, tx_count, nonce, ts),
                tags=(tag,),
            )

        self.tree.tag_configure("genesis", foreground=C["system_fg"])

    def _refresh_pending_ui(self):
        self.pend_text.configure(state="normal")
        self.pend_text.delete("1.0", "end")
        if not self.pending_data:
            self.pend_text.insert("end", "  antrian kosong\n", "muted")
        else:
            for tx in self.pending_data:
                sender = tx["sender"]
                receiver = tx["receiver"]
                amount = tx["amount"]
                sig = (tx.get("signature") or "")[:12] + "..."
                tag = "system" if sender == "SYSTEM" else "pending"
                line = f"  {sender} → {receiver}  {amount} koin  [{sig}]\n"
                self.pend_text.insert("end", line, tag)
        self.pend_text.configure(state="disabled")

    def _on_block_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        blk = next((b for b in self.chain_data if b["index"] == idx), None)
        if not blk:
            return

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")

        def ins(text, tag="val"):
            self.detail_text.insert("end", text, tag)

        ins(f"BLOCK #{blk['index']}\n", "hash")
        ins("─" * 28 + "\n", "sep")
        ins("hash\n", "key")
        ins(f"{blk.get('hash','')[:24]}\n", "hash")
        ins("prev\n", "key")
        ins(f"{blk.get('previous_hash','')[:24]}\n", "hash")
        ins(f"nonce   ", "key")
        ins(f"{blk.get('nonce',0)}\n")
        ins(f"time    ", "key")
        ins(f"{blk.get('timestamp','')[:19]}\n")
        ins("─" * 28 + "\n", "sep")
        ins(f"TRANSACTIONS ({len(blk.get('transactions',[]))})\n", "key")
        ins("─" * 28 + "\n", "sep")

        for tx in blk.get("transactions", []):
            is_sys = tx["sender"] == "SYSTEM"
            tag = "reward" if is_sys else "tx"
            ins(f"{'⭐ REWARD' if is_sys else '↗ TX'}\n", tag)
            ins(f"  {tx['sender']}\n  → {tx['receiver']}\n")
            ins(f"  {tx['amount']} koin\n")
            sig = (tx.get("signature") or "—")[:16] + "..."
            ins(f"  sig: {sig}\n", "key")
            ins("· · ·\n", "sep")

        self.detail_text.configure(state="disabled")

    # ── Log ────────────────────────────────────────────────────────────────────
    def _add_log(self, level, msg):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = {"ok": "✓", "err": "✗", "warn": "⚠", "info": "·"}.get(level, "·")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{now}  ", "time")
        self.log_text.insert("end", f"{prefix} {msg}\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = BlockchainDashboard()
    app.mainloop()
