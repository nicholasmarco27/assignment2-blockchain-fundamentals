import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import datetime

NODES = {
    "Nico": {"port": 5001, "url": "http://127.0.0.1:5001"},
    "Azza": {"port": 5002, "url": "http://127.0.0.1:5002"},
    "Riyan": {"port": 5003, "url": "http://127.0.0.1:5003"},
}

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
    "pending_fg": "#fbbf24",
    "system_fg": "#a5b4fc",
    "confirm_fg": "#4ade80",
}


class ToolTip:
    """Tooltip sederhana untuk menampilkan address penuh."""

    def __init__(self, widget, text_var):
        self.widget = widget
        self.text_var = text_var
        self.tip_win = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        txt = self.text_var() if callable(self.text_var) else self.text_var
        if not txt:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=txt,
            bg="#1e2130",
            fg=C["accent2"],
            font=("Courier New", 9),
            relief="flat",
            padx=8,
            pady=4,
        ).pack()

    def hide(self, _=None):
        if self.tip_win:
            self.tip_win.destroy()
            self.tip_win = None


class BlockchainDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Blockchain Dashboard v2")
        self.geometry("1180x780")
        self.minsize(960, 680)
        self.configure(bg=C["bg"])

        self.current_node = tk.StringVar(value="Nico")
        self.node_status = {
            n: {
                "online": False,
                "chain_len": 0,
                "pending": 0,
                "saldo": 0,
                "address": "",
            }
            for n in NODES
        }
        self.chain_data = []
        self.pending_data = []
        self.balance_data = []
        # address → name cache (diisi dari /wallet endpoint tiap node)
        self.addr_to_name: dict[str, str] = {}

        self._setup_styles()
        self._build_ui()
        self._start_polling()

    # ── Styles ─────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        for name, bg, fg, font_ in [
            ("Dark.TFrame", C["bg"], C["text"], ("Courier New", 11)),
            ("Card.TFrame", C["bg2"], C["text"], ("Courier New", 11)),
        ]:
            s.configure(name, background=bg)

        s.configure("TNotebook", background=C["bg"], borderwidth=0)
        s.configure(
            "TNotebook.Tab",
            background=C["bg3"],
            foreground=C["muted"],
            font=("Courier New", 11),
            padding=[16, 6],
        )
        s.map(
            "TNotebook.Tab",
            background=[("selected", C["accent"]), ("active", C["bg2"])],
            foreground=[("selected", "white"), ("active", C["text"])],
        )

        s.configure(
            "Chain.Treeview",
            background=C["bg2"],
            foreground=C["text"],
            fieldbackground=C["bg2"],
            rowheight=28,
            font=("Courier New", 10),
        )
        s.configure(
            "Chain.Treeview.Heading",
            background=C["bg3"],
            foreground=C["muted"],
            font=("Courier New", 10, "bold"),
            relief="flat",
        )
        s.map(
            "Chain.Treeview",
            background=[("selected", C["accent"])],
            foreground=[("selected", "white")],
        )

        s.configure(
            "Dark.Vertical.TScrollbar",
            background=C["bg3"],
            troughcolor=C["bg2"],
            arrowcolor=C["muted"],
            borderwidth=0,
        )
        s.configure(
            "Dark.TCombobox",
            fieldbackground=C["bg3"],
            background=C["bg3"],
            foreground=C["text"],
            selectbackground=C["accent"],
            font=("Courier New", 11),
        )

    # ── Build UI ───────────────────────────────────────────────
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=C["bg"], pady=10)
        top.pack(fill="x", padx=16)
        tk.Label(
            top,
            text="⬡ BlockchainSim v2",
            bg=C["bg"],
            fg=C["accent2"],
            font=("Courier New", 16, "bold"),
        ).pack(side="left")
        tk.Label(
            top,
            text="  address · ecdsa · balance",
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

        # Node tabs
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

        # Body
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=8)
        left = tk.Frame(body, bg=C["bg"], width=340)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        self._build_left(left)
        self._build_right(right)

    # ── Left panel ─────────────────────────────────────────────
    def _build_left(self, parent):
        # Stat cards
        stats = self._card(parent)
        stats.pack(fill="x", pady=(0, 8))
        row = tk.Frame(stats, bg=C["bg2"])
        row.pack(fill="x")
        self.stat_frames = {}
        for title, key, color in [
            ("STATUS", "status", C["green"]),
            ("BLOCKS", "chain_len", C["accent2"]),
            ("SALDO", "saldo", C["gold"]),
        ]:
            f = tk.Frame(row, bg=C["bg3"], padx=12, pady=10)
            f.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            tk.Label(
                f, text=title, bg=C["bg3"], fg=C["muted"], font=("Courier New", 9)
            ).pack(anchor="w")
            lbl = tk.Label(
                f, text="—", bg=C["bg3"], fg=color, font=("Courier New", 18, "bold")
            )
            lbl.pack(anchor="w")
            self.stat_frames[key] = lbl

        # Address card
        addr_card = self._card(parent, "WALLET ADDRESS")
        addr_card.pack(fill="x", pady=(0, 8))
        self.lbl_address = tk.Label(
            addr_card,
            text="—",
            bg=C["bg2"],
            fg=C["accent2"],
            font=("Courier New", 10),
            wraplength=300,
            justify="left",
        )
        self.lbl_address.pack(anchor="w", padx=10, pady=(2, 8))
        self._addr_full = ""
        ToolTip(self.lbl_address, lambda: self._addr_full)

        # Send tx
        tx_card = self._card(parent, "SEND TRANSACTION")
        tx_card.pack(fill="x", pady=(0, 8))
        tk.Label(
            tx_card,
            text="Receiver Address",
            bg=C["bg2"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=8)
        self.cmb_receiver = ttk.Combobox(
            tx_card, font=("Courier New", 10), style="Dark.TCombobox", state="readonly"
        )
        self.cmb_receiver.pack(fill="x", padx=8, pady=(2, 4))
        self.lbl_recv_name = tk.Label(
            tx_card, text="", bg=C["bg2"], fg=C["muted"], font=("Courier New", 9)
        )
        self.lbl_recv_name.pack(anchor="w", padx=10)

        tk.Label(
            tx_card, text="Amount", bg=C["bg2"], fg=C["muted"], font=("Courier New", 9)
        ).pack(anchor="w", padx=8, pady=(6, 0))
        self.ent_amount = tk.Entry(
            tx_card,
            bg=C["bg3"],
            fg=C["text"],
            insertbackground=C["text"],
            font=("Courier New", 12),
            relief="flat",
            bd=6,
        )
        self.ent_amount.pack(fill="x", padx=8, pady=(2, 4))

        tk.Label(
            tx_card,
            text="Fee (default 1)",
            bg=C["bg2"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=8)
        self.ent_fee = tk.Entry(
            tx_card,
            bg=C["bg3"],
            fg=C["text"],
            insertbackground=C["text"],
            font=("Courier New", 12),
            relief="flat",
            bd=6,
        )
        self.ent_fee.insert(0, "1")
        self.ent_fee.pack(fill="x", padx=8, pady=(2, 8))

        self._btn(
            tx_card, "  ↗  Kirim Transaksi", self._send_tx, bg=C["accent"], fg="white"
        ).pack(fill="x", padx=8, pady=(0, 8))

        self.cmb_receiver.bind("<<ComboboxSelected>>", self._on_receiver_select)

        # Actions
        act_card = self._card(parent, "ACTIONS")
        act_card.pack(fill="x", pady=(0, 8))
        self._btn(
            act_card, "  ⛏  Mine Blok", self._do_mine, bg=C["gold"], fg="#1a1a00"
        ).pack(fill="x", padx=8, pady=(4, 4))
        self._btn(
            act_card, "  ↺  Refresh Data", self._do_refresh, bg=C["bg3"], fg=C["text"]
        ).pack(fill="x", padx=8, pady=(0, 8))

        # Pending
        pend_card = self._card(parent, "ANTRIAN PENDING")
        pend_card.pack(fill="both", expand=True)
        self.pend_text = tk.Text(
            pend_card,
            bg=C["bg3"],
            fg=C["text"],
            font=("Courier New", 10),
            relief="flat",
            state="disabled",
            wrap="none",
            height=5,
        )
        self.pend_text.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.pend_text.tag_configure("pending", foreground=C["pending_fg"])
        self.pend_text.tag_configure("system", foreground=C["system_fg"])
        self.pend_text.tag_configure("muted", foreground=C["muted"])

    # ── Right panel ────────────────────────────────────────────
    def _build_right(self, parent):
        nb = ttk.Notebook(parent, style="TNotebook")
        nb.pack(fill="both", expand=True)

        chain_tab = tk.Frame(nb, bg=C["bg2"])
        balance_tab = tk.Frame(nb, bg=C["bg2"])
        net_tab = tk.Frame(nb, bg=C["bg2"])
        log_tab = tk.Frame(nb, bg=C["bg2"])

        nb.add(chain_tab, text=" ⬡  Chain Explorer ")
        nb.add(balance_tab, text=" ₿  Balances ")
        nb.add(net_tab, text=" ⇆  Network ")
        nb.add(log_tab, text=" ≡  Activity Log ")

        self._build_chain_tab(chain_tab)
        self._build_balance_tab(balance_tab)
        self._build_network_tab(net_tab)
        self._build_log_tab(log_tab)

    def _build_chain_tab(self, parent):
        cols = ("#", "hash", "prev", "txs", "nonce", "timestamp")
        self.tree = ttk.Treeview(
            parent,
            columns=cols,
            show="headings",
            style="Chain.Treeview",
            selectmode="browse",
        )
        for col, w, anc in [
            ("#", 50, "center"),
            ("hash", 180, "w"),
            ("prev", 130, "w"),
            ("txs", 50, "center"),
            ("nonce", 70, "center"),
            ("timestamp", 160, "w"),
        ]:
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

        detail_frame = tk.Frame(parent, bg=C["bg3"], width=260)
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
        for tag, fg in [
            ("key", C["muted"]),
            ("hash", C["accent2"]),
            ("reward", C["system_fg"]),
            ("tx", C["confirm_fg"]),
            ("sep", C["border"]),
        ]:
            self.detail_text.tag_configure(tag, foreground=fg)
        self.tree.bind("<<TreeviewSelect>>", self._on_block_select)

    def _build_balance_tab(self, parent):
        tk.Label(
            parent,
            text="SALDO SEMUA ADDRESS",
            bg=C["bg2"],
            fg=C["muted"],
            font=("Courier New", 9),
        ).pack(anchor="w", padx=14, pady=(12, 4))

        cols = ("name", "address", "saldo")
        self.bal_tree = ttk.Treeview(
            parent,
            columns=cols,
            show="headings",
            style="Chain.Treeview",
            selectmode="browse",
        )
        for col, w, txt in [
            ("name", 100, "NAMA"),
            ("address", 320, "ADDRESS"),
            ("saldo", 100, "SALDO"),
        ]:
            self.bal_tree.heading(col, text=txt)
            self.bal_tree.column(
                col,
                width=w,
                anchor="w" if col == "address" else "center",
                stretch=(col == "address"),
            )
        vsb2 = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.bal_tree.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.bal_tree.configure(yscrollcommand=vsb2.set)
        self.bal_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        vsb2.pack(side="left", fill="y", pady=8, padx=(0, 8))
        self.bal_tree.tag_configure("rich", foreground=C["gold"])
        self.bal_tree.tag_configure("normal", foreground=C["text"])
        self.bal_tree.tag_configure("zero", foreground=C["muted"])

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
            addr_lbl = tk.Label(
                f,
                text="address: —",
                bg=C["bg3"],
                fg=C["accent2"],
                font=("Courier New", 9),
            )
            addr_lbl.pack(anchor="w", pady=(2, 0))
            info_lbl = tk.Label(
                f,
                text="tidak terhubung",
                bg=C["bg3"],
                fg=C["muted"],
                font=("Courier New", 10),
            )
            info_lbl.pack(anchor="w", pady=(2, 0))
            self.peer_frames[name] = {
                "dot": dot_lbl,
                "info": info_lbl,
                "addr": addr_lbl,
            }

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
        for tag, fg in [
            ("ok", C["green"]),
            ("err", C["red"]),
            ("warn", C["gold"]),
            ("info", C["text2"]),
            ("time", C["muted"]),
        ]:
            self.log_text.tag_configure(tag, foreground=fg)

    # ── Helpers ────────────────────────────────────────────────
    def _card(self, parent, label=""):
        wrap = tk.Frame(parent, bg=C["bg2"])
        if label:
            tk.Label(
                wrap, text=label, bg=C["bg2"], fg=C["muted"], font=("Courier New", 9)
            ).pack(anchor="w", padx=10, pady=(8, 2))
        return wrap

    def _btn(self, parent, text, command, bg=None, fg=None):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg or C["bg3"],
            fg=fg or C["text"],
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
            btn.configure(
                bg=C["accent"] if n == name else C["bg3"],
                fg="white" if n == name else C["muted"],
            )

    def _tick_clock(self):
        self.lbl_time.configure(
            text=datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        )
        self.after(1000, self._tick_clock)

    def _short_addr(self, addr: str) -> str:
        if not addr or len(addr) < 16:
            return addr
        return addr[:8] + "..." + addr[-6:]

    # ── Node switching ─────────────────────────────────────────
    def _switch_node(self, name):
        self.current_node.set(name)
        self._highlight_tab(name)
        self.chain_data = []
        self.pending_data = []
        self._refresh_chain_ui()
        self._refresh_pending_ui()
        self._do_refresh()

    def _update_receiver_list(self):
        node = self.current_node.get()
        node_url = NODES[node]["url"]
        # Gunakan address dari node lain yang sudah diketahui
        options = []
        for n, st in self.node_status.items():
            if n != node and st["address"]:
                options.append(st["address"])
        self.cmb_receiver["values"] = options
        if options:
            self.cmb_receiver.set(options[0])
            self._on_receiver_select()

    def _on_receiver_select(self, _=None):
        addr = self.cmb_receiver.get()
        name = self.addr_to_name.get(addr, "unknown")
        self.lbl_recv_name.configure(text=f"  → {name}  ({self._short_addr(addr)})")

    # ── Polling ────────────────────────────────────────────────
    def _start_polling(self):
        self._poll()

    def _poll(self):
        threading.Thread(target=self._poll_all_status, daemon=True).start()
        self.after(5000, self._poll)

    def _poll_all_status(self):
        for name in NODES:
            try:
                r = requests.get(f"{NODES[name]['url']}/", timeout=2)
                d = r.json()
                self.node_status[name] = {
                    "online": True,
                    "chain_len": d["panjang_chain"],
                    "pending": d["pending_transaksi"],
                    "saldo": d.get("saldo", 0),
                    "address": d.get("address", ""),
                }
                addr = d.get("address", "")
                if addr:
                    self.addr_to_name[addr] = name
            except Exception:
                self.node_status[name] = {
                    "online": False,
                    "chain_len": 0,
                    "pending": 0,
                    "saldo": 0,
                    "address": "",
                }
        self.after(0, self._refresh_status_ui)
        self.after(0, self._update_receiver_list)

    # ── API calls ──────────────────────────────────────────────
    def _do_refresh(self):
        self._add_log("info", f"Memperbarui data node {self.current_node.get()}...")
        threading.Thread(target=self._fetch_node_data, daemon=True).start()

    def _fetch_node_data(self):
        node = self.current_node.get()
        url = NODES[node]["url"]
        try:
            rc = requests.get(f"{url}/chain", timeout=3)
            rp = requests.get(f"{url}/pending", timeout=3)
            rb = requests.get(f"{url}/balances", timeout=3)
            self.chain_data = rc.json().get("chain", [])
            self.pending_data = rp.json().get("antrian", [])
            self.balance_data = rb.json().get("balances", [])
            # update addr_to_name dari balance data
            for entry in self.balance_data:
                if entry.get("name") != "unknown":
                    self.addr_to_name[entry["address"]] = entry["name"]
            self.after(0, self._refresh_chain_ui)
            self.after(0, self._refresh_pending_ui)
            self.after(0, self._refresh_balance_ui)
            self.after(0, lambda: self._add_log("ok", "Data berhasil diperbarui"))
        except Exception as e:
            self.after(0, lambda: self._add_log("err", f"Gagal terhubung: {e}"))

    def _send_tx(self):
        receiver = self.cmb_receiver.get()
        amount = self.ent_amount.get().strip()
        fee = self.ent_fee.get().strip() or "1"
        if not receiver or not amount:
            messagebox.showwarning("Input Error", "Isi receiver address dan amount!")
            return
        try:
            amount_val = int(amount)
            fee_val = int(fee)
            if amount_val <= 0 or fee_val < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Amount dan fee harus angka positif!")
            return

        node = self.current_node.get()
        self._add_log(
            "info",
            f"Mengirim: {node} → {self._short_addr(receiver)} ({amount_val} koin, fee: {fee_val})",
        )

        def task():
            try:
                r = requests.post(
                    f"{NODES[node]['url']}/transaksi",
                    json={
                        "receiver_address": receiver,
                        "amount": amount_val,
                        "fee": fee_val,
                    },
                    timeout=5,
                )
                d = r.json()
                if r.ok:
                    self.after(
                        0, lambda: self._add_log("ok", d.get("pesan", "Terkirim"))
                    )
                    self.after(0, lambda: self.ent_amount.delete(0, "end"))
                    self.after(0, self._do_refresh)
                else:
                    self.after(0, lambda: self._add_log("err", d.get("error", "Gagal")))
            except Exception as e:
                self.after(0, lambda: self._add_log("err", f"Koneksi gagal: {e}"))

        threading.Thread(target=task, daemon=True).start()

    def _do_mine(self):
        node = self.current_node.get()
        self._add_log("warn", f"Mining blok baru oleh {node}...")

        def task():
            try:
                r = requests.post(f"{NODES[node]['url']}/mine", timeout=60)
                d = r.json()
                if r.ok:
                    msg = d.get("pesan", "Blok di-mine")
                    nonce = d.get("nonce", "?")
                    saldo = d.get("saldo_baru", "?")
                    self.after(
                        0,
                        lambda: self._add_log(
                            "ok", f"{msg}  |  nonce:{nonce}  |  saldo baru:{saldo}"
                        ),
                    )
                    self.after(0, self._do_refresh)
                else:
                    self.after(
                        0, lambda: self._add_log("err", d.get("error", "Mining gagal"))
                    )
            except Exception as e:
                self.after(0, lambda: self._add_log("err", f"Mining gagal: {e}"))

        threading.Thread(target=task, daemon=True).start()

    # ── UI refresh ─────────────────────────────────────────────
    def _refresh_status_ui(self):
        node = self.current_node.get()
        status = self.node_status[node]
        online = status["online"]

        self.stat_frames["status"].configure(
            text="ONLINE" if online else "OFFLINE",
            fg=C["green"] if online else C["red"],
        )
        self.stat_frames["chain_len"].configure(text=str(status["chain_len"]))
        self.stat_frames["saldo"].configure(text=str(status["saldo"]))

        addr = status["address"]
        self._addr_full = addr
        self.lbl_address.configure(text=self._short_addr(addr) if addr else "—")

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

        for name, widgets in self.peer_frames.items():
            st = self.node_status[name]
            if st["online"]:
                widgets["dot"].configure(fg=C["green"])
                addr_short = self._short_addr(st["address"]) if st["address"] else "—"
                widgets["addr"].configure(
                    text=f"address: {addr_short}", fg=C["accent2"]
                )
                widgets["info"].configure(
                    text=f"chain: {st['chain_len']} blok   |   pending: {st['pending']}   |   saldo: {st['saldo']}",
                    fg=C["text2"],
                )
            else:
                widgets["dot"].configure(fg=C["muted"])
                widgets["addr"].configure(text="address: —", fg=C["muted"])
                widgets["info"].configure(text="tidak terhubung", fg=C["muted"])

    def _refresh_chain_ui(self):
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
                is_sys = sender == "0" * 40
                tag = "system" if is_sys else "pending"
                s_name = self.addr_to_name.get(sender, self._short_addr(sender))
                r_name = self.addr_to_name.get(receiver, self._short_addr(receiver))
                line = f"  {s_name} → {r_name}  {tx['amount']} koin  fee:{tx.get('fee',0)}\n"
                self.pend_text.insert("end", line, tag)
        self.pend_text.configure(state="disabled")

    def _refresh_balance_ui(self):
        for item in self.bal_tree.get_children():
            self.bal_tree.delete(item)
        for entry in self.balance_data:
            addr = entry["address"]
            name = entry.get("name", self.addr_to_name.get(addr, "unknown"))
            saldo = entry["saldo"]
            tag = "rich" if saldo > 50 else ("zero" if saldo == 0 else "normal")
            self.bal_tree.insert(
                "", "end", values=(name, addr, f"{saldo} koin"), tags=(tag,)
            )

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
        ins(f"{blk.get('nonce', 0)}\n")
        ins(f"time    ", "key")
        ins(f"{blk.get('timestamp','')[:19]}\n")
        ins("─" * 28 + "\n", "sep")
        ins(f"TRANSACTIONS ({len(blk.get('transactions', []))})\n", "key")
        ins("─" * 28 + "\n", "sep")
        for tx in blk.get("transactions", []):
            is_sys = tx["sender"] == "0" * 40
            tag = "reward" if is_sys else "tx"
            s_name = self.addr_to_name.get(tx["sender"], self._short_addr(tx["sender"]))
            r_name = self.addr_to_name.get(
                tx["receiver"], self._short_addr(tx["receiver"])
            )
            ins(f"{'⭐ REWARD' if is_sys else '↗ TX'}\n", tag)
            ins(f"  {s_name}\n  → {r_name}\n")
            ins(f"  {tx['amount']} koin  fee:{tx.get('fee',0)}\n")
            sig = (tx.get("signature") or "—")[:16] + "..."
            ins(f"  sig: {sig}\n", "key")
            ins("· · ·\n", "sep")
        self.detail_text.configure(state="disabled")

    # ── Log ─────────────────────────────────────────────────────
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


if __name__ == "__main__":
    app = BlockchainDashboard()
    app.mainloop()
