import csv
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

APP_TITLE = "VendeBem"
APP_DEVELOPER_SIGNATURE = "Feito por Luiz Lobato Junior • Engenheiro de Software"
DB_FILENAME = "gerenciador_vendas.db"
APP_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
DB_FILE = APP_DIR / DB_FILENAME


def money(value):
    return f"€ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_price(value):
    value = value.strip().replace("€", "").replace(" ", "").replace(",", ".")
    try:
        result = Decimal(value)
        if result < 0:
            raise ValueError
        return float(result)
    except (InvalidOperation, ValueError):
        raise ValueError("Introduza um valor numérico válido e não negativo.")


def calculate_discount(cart, percentage):
    try:
        rate = Decimal(str(percentage).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError("O desconto deve ser um percentual entre 0 e 100.")
    if not rate.is_finite() or rate < 0 or rate > 100:
        raise ValueError("O desconto deve ser um percentual entre 0 e 100.")
    subtotal = sum(
        (Decimal(str(item["price"])) * item["quantity"] for item in cart.values()),
        Decimal("0")
    )
    discount = (subtotal * rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return subtotal, discount, subtotal - discount


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DB_FILE
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT UNIQUE,
                    category TEXT DEFAULT '',
                    cost REAL NOT NULL DEFAULT 0 CHECK(cost >= 0),
                    price REAL NOT NULL CHECK(price >= 0),
                    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sold_at TEXT NOT NULL,
                    total REAL NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT 'Dinheiro',
                    canceled_at TEXT,
                    cancel_reason TEXT,
                    discount_percent REAL NOT NULL DEFAULT 0 CHECK(discount_percent BETWEEN 0 AND 100),
                    discount_amount REAL NOT NULL DEFAULT 0 CHECK(discount_amount >= 0)
                );
                CREATE TABLE IF NOT EXISTS sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL REFERENCES sales(id),
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    unit_price REAL NOT NULL,
                    subtotal REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                INSERT OR IGNORE INTO app_settings(key, value)
                VALUES ('stock_alert_limit', '5');
            """)
            columns = {row[1] for row in self.conn.execute("PRAGMA table_info(sales)")}
            if "canceled_at" not in columns:
                self.conn.execute("ALTER TABLE sales ADD COLUMN canceled_at TEXT")
            if "cancel_reason" not in columns:
                self.conn.execute("ALTER TABLE sales ADD COLUMN cancel_reason TEXT")
            if "discount_percent" not in columns:
                self.conn.execute("ALTER TABLE sales ADD COLUMN discount_percent REAL NOT NULL DEFAULT 0")
            if "discount_amount" not in columns:
                self.conn.execute("ALTER TABLE sales ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0")

    def close(self):
        self.conn.close()

    def get_stock_alert_limit(self):
        row = self.conn.execute(
            "SELECT value FROM app_settings WHERE key='stock_alert_limit'"
        ).fetchone()
        try:
            limit = int(row["value"])
            return limit if limit >= 0 else 5
        except (TypeError, ValueError):
            return 5

    def set_stock_alert_limit(self, limit):
        if not isinstance(limit, int) or limit < 0:
            raise ValueError("O limite de stock deve ser um número inteiro não negativo.")
        with self.conn:
            self.conn.execute(
                "INSERT INTO app_settings(key, value) VALUES ('stock_alert_limit', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(limit),)
            )

    def products(self, search="", low_stock_limit=None):
        term = f"%{search.strip()}%"
        return self.conn.execute("""
            SELECT * FROM products
            WHERE (name LIKE ? OR COALESCE(code, '') LIKE ? OR category LIKE ?)
              AND (? IS NULL OR stock <= ?)
            ORDER BY name COLLATE NOCASE
        """, (term, term, term, low_stock_limit, low_stock_limit)).fetchall()

    def add_product(self, name, code, category, cost, price, stock):
        with self.conn:
            self.conn.execute("""
                INSERT INTO products(name, code, category, cost, price, stock, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, code or None, category, cost, price, stock,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    def update_product(self, product_id, name, code, category, cost, price, stock):
        with self.conn:
            self.conn.execute("""
                UPDATE products
                SET name=?, code=?, category=?, cost=?, price=?, stock=?
                WHERE id=?
            """, (name, code or None, category, cost, price, stock, product_id))

    def delete_product(self, product_id):
        used = self.conn.execute(
            "SELECT 1 FROM sale_items WHERE product_id=? LIMIT 1", (product_id,)
        ).fetchone()
        if used:
            raise ValueError("Este artigo já aparece em vendas. Não pode ser eliminado; pode editar o artigo.")
        with self.conn:
            self.conn.execute("DELETE FROM products WHERE id=?", (product_id,))

    def create_sale(self, cart, payment_method, discount_percent=0):
        if not cart:
            raise ValueError("Adicione pelo menos um artigo à venda.")
        subtotal, discount, total = calculate_discount(cart, discount_percent)
        with self.conn:
            for product_id, item in cart.items():
                row = self.conn.execute(
                    "SELECT name, stock FROM products WHERE id=?", (product_id,)
                ).fetchone()
                if row is None:
                    raise ValueError("Um artigo da venda já não existe.")
                if row["stock"] < item["quantity"]:
                    raise ValueError(f"Stock insuficiente para {row['name']}. Disponível: {row['stock']}.")
            cur = self.conn.execute(
                """INSERT INTO sales(
                    sold_at, total, payment_method, discount_percent, discount_amount
                ) VALUES (?, ?, ?, ?, ?)""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), float(total), payment_method,
                 float(discount_percent), float(discount))
            )
            sale_id = cur.lastrowid
            for product_id, item in cart.items():
                subtotal = item["quantity"] * item["price"]
                self.conn.execute("""
                    INSERT INTO sale_items(sale_id, product_id, product_name, quantity, unit_price, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sale_id, product_id, item["name"], item["quantity"], item["price"], subtotal))
                self.conn.execute(
                    "UPDATE products SET stock=stock-? WHERE id=?",
                    (item["quantity"], product_id)
                )
        return sale_id, float(total)

    def cancel_sale(self, sale_id, reason):
        reason = reason.strip()
        if not reason:
            raise ValueError("Indique o motivo da anulação.")
        with self.conn:
            sale = self.conn.execute(
                "SELECT canceled_at FROM sales WHERE id=?", (sale_id,)
            ).fetchone()
            if sale is None:
                raise ValueError("A venda selecionada não existe.")
            if sale["canceled_at"]:
                raise ValueError("Esta venda já foi anulada.")
            items = self.conn.execute(
                "SELECT product_id, quantity FROM sale_items WHERE sale_id=?", (sale_id,)
            ).fetchall()
            for item in items:
                self.conn.execute(
                    "UPDATE products SET stock=stock+? WHERE id=?",
                    (item["quantity"], item["product_id"])
                )
            canceled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.conn.execute(
                "UPDATE sales SET canceled_at=?, cancel_reason=? WHERE id=?",
                (canceled_at, reason, sale_id)
            )
        return canceled_at

    def sale(self, sale_id):
        return self.conn.execute(
            "SELECT * FROM sales WHERE id=?", (sale_id,)
        ).fetchone()

    def sales(self, search="", date_from="", date_to="", payment_method="", product_search=""):
        conditions = []
        params = []
        if search.strip():
            term = f"%{search.strip()}%"
            conditions.append("(CAST(s.id AS TEXT) LIKE ? OR s.sold_at LIKE ?)")
            params.extend((term, term))
        if date_from:
            conditions.append("s.sold_at >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            conditions.append("s.sold_at <= ?")
            params.append(f"{date_to} 23:59:59")
        if payment_method and payment_method != "Todos":
            conditions.append("s.payment_method = ?")
            params.append(payment_method)
        if product_search.strip():
            conditions.append("""EXISTS (
                SELECT 1 FROM sale_items filtered_items
                WHERE filtered_items.sale_id=s.id AND filtered_items.product_name LIKE ?
            )""")
            params.append(f"%{product_search.strip()}%")
        where = " AND ".join(conditions) if conditions else "1=1"
        return self.conn.execute(f"""
            SELECT s.id, s.sold_at, s.total, s.payment_method,
                   s.canceled_at, s.cancel_reason, s.discount_percent, s.discount_amount,
                   COUNT(si.id) AS lines, COALESCE(SUM(si.quantity), 0) AS units,
                   COALESCE(SUM(si.subtotal), 0) AS subtotal
            FROM sales s LEFT JOIN sale_items si ON si.sale_id=s.id
            WHERE {where}
            GROUP BY s.id ORDER BY s.id DESC
        """, params).fetchall()

    def sale_items(self, sale_id):
        return self.conn.execute(
            "SELECT * FROM sale_items WHERE sale_id=? ORDER BY id", (sale_id,)
        ).fetchall()

    def summary(self, low_stock_limit=5):
        today = datetime.now().strftime("%Y-%m-%d")
        total_today = self.conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM sales WHERE sold_at LIKE ? AND canceled_at IS NULL",
            (today + "%",)
        ).fetchone()[0]
        sales_count = self.conn.execute(
            "SELECT COUNT(*) FROM sales WHERE canceled_at IS NULL"
        ).fetchone()[0]
        product_count = self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        stock_units = self.conn.execute("SELECT COALESCE(SUM(stock),0) FROM products").fetchone()[0]
        low_stock = self.conn.execute(
            "SELECT COUNT(*) FROM products WHERE stock <= ?", (low_stock_limit,)
        ).fetchone()[0]
        return total_today, sales_count, product_count, stock_units, low_stock


class SalesApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x720")
        self.minsize(920, 600)
        self.db = Database()
        self.stock_alert_limit = self.db.get_stock_alert_limit()
        self.selected_product_id = None
        self.cart = {}
        self._configure_style()
        self._build_ui()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Metric.TLabel", font=("TkDefaultFont", 12, "bold"))
        style.configure("Treeview", rowheight=27)
        style.configure("Treeview.Heading", font=("TkDefaultFont", 10, "bold"))
        style.configure("Accent.TButton", font=("TkDefaultFont", 10, "bold"))

    def _build_ui(self):
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Produtos • Stock • Vendas • Histórico").pack(side="right")

        self.metrics = ttk.Frame(self, padding=(12, 0, 12, 12))
        self.metrics.pack(fill="x")
        self.metric_labels = {}
        self.metric_boxes = {}
        for key, title in [
            ("today", "Vendas de hoje"), ("sales", "Vendas registadas"),
            ("products", "Artigos"), ("units", "Unidades em stock"), ("low", "Stock baixo (≤ 5)")
        ]:
            box = ttk.LabelFrame(self.metrics, text=title, padding=10)
            box.pack(side="left", fill="both", expand=True, padx=4)
            self.metric_boxes[key] = box
            label = ttk.Label(box, text="—", style="Metric.TLabel")
            label.pack()
            self.metric_labels[key] = label

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.products_tab = ttk.Frame(self.tabs, padding=10)
        self.sale_tab = ttk.Frame(self.tabs, padding=10)
        self.history_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.products_tab, text="Mercadorias / Stock")
        self.tabs.add(self.sale_tab, text="Registar venda")
        self.tabs.add(self.history_tab, text="Histórico de vendas")

        footer = ttk.Frame(self, padding=(12, 6, 12, 12))
        footer.pack(fill="x")
        ttk.Label(
            footer,
            text=APP_DEVELOPER_SIGNATURE,
            foreground="#4b5563",
            anchor="e"
        ).pack(side="right")

        self._build_products_tab()
        self._build_sale_tab()
        self._build_history_tab()

    def _build_products_tab(self):
        tab = self.products_tab
        form = ttk.LabelFrame(tab, text="Dados da mercadoria", padding=10)
        form.pack(fill="x", pady=(0, 10))
        self.p_name = tk.StringVar()
        self.p_code = tk.StringVar()
        self.p_category = tk.StringVar()
        self.p_cost = tk.StringVar(value="0,00")
        self.p_price = tk.StringVar(value="0,00")
        self.p_stock = tk.StringVar(value="0")
        fields = [
            ("Nome *", self.p_name, 0, 0), ("Código/SKU", self.p_code, 0, 2),
            ("Categoria", self.p_category, 0, 4), ("Custo (€)", self.p_cost, 1, 0),
            ("Preço de venda (€) *", self.p_price, 1, 2), ("Quantidade em stock *", self.p_stock, 1, 4)
        ]
        for label, var, row, col in fields:
            ttk.Label(form, text=label).grid(row=row*2, column=col, sticky="w", padx=5, pady=(3, 0))
            ttk.Entry(form, textvariable=var, width=25).grid(row=row*2+1, column=col, sticky="ew", padx=5, pady=(0, 5))
        for col in (1, 3, 5):
            form.columnconfigure(col, weight=1)
        buttons = ttk.Frame(form)
        buttons.grid(row=4, column=0, columnspan=6, sticky="w", padx=5, pady=4)
        ttk.Button(buttons, text="Guardar artigo", command=self.save_product, style="Accent.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Limpar formulário", command=self.clear_product_form).pack(side="left", padx=6)
        ttk.Button(buttons, text="Eliminar artigo selecionado", command=self.delete_product).pack(side="left", padx=6)

        searchbar = ttk.Frame(tab)
        searchbar.pack(fill="x", pady=(0, 6))
        ttk.Label(searchbar, text="Pesquisar:").pack(side="left")
        self.product_search = tk.StringVar()
        entry = ttk.Entry(searchbar, textvariable=self.product_search, width=35)
        entry.pack(side="left", padx=8)
        entry.bind("<KeyRelease>", lambda _e: self.refresh_products())
        ttk.Button(searchbar, text="Atualizar lista", command=self.refresh_products).pack(side="left")
        self.low_stock_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            searchbar, text="Só stock baixo (≤)", variable=self.low_stock_only,
            command=self.refresh_products
        ).pack(side="left", padx=(12, 4))
        self.stock_limit_var = tk.StringVar(value=str(self.stock_alert_limit))
        stock_limit_input = ttk.Spinbox(
            searchbar, from_=0, to=999999, increment=1, width=7,
            textvariable=self.stock_limit_var, command=self.save_stock_alert_limit
        )
        stock_limit_input.pack(side="left")
        stock_limit_input.bind("<Return>", self.save_stock_alert_limit)
        stock_limit_input.bind("<FocusOut>", self.save_stock_alert_limit)

        cols = ("id", "name", "code", "category", "cost", "price", "stock")
        self.product_tree = ttk.Treeview(tab, columns=cols, show="headings", selectmode="browse")
        headings = {"id":"ID", "name":"Mercadoria", "code":"Código", "category":"Categoria",
                    "cost":"Custo", "price":"Preço venda", "stock":"Stock"}
        widths = {"id":50, "name":250, "code":120, "category":150, "cost":100, "price":110, "stock":80}
        for c in cols:
            self.product_tree.heading(c, text=headings[c])
            self.product_tree.column(c, width=widths[c], anchor="w" if c in ("name","code","category") else "center")
        self.product_tree.pack(fill="both", expand=True)
        self.product_tree.bind("<<TreeviewSelect>>", self.on_product_select)

    def _build_sale_tab(self):
        tab = self.sale_tab
        top = ttk.LabelFrame(tab, text="Adicionar mercadoria à venda", padding=10)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Mercadoria:").grid(row=0, column=0, sticky="w")
        self.sale_product = tk.StringVar()
        self.sale_combo = ttk.Combobox(top, textvariable=self.sale_product, state="readonly", width=55)
        self.sale_combo.grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Label(top, text="Quantidade:").grid(row=0, column=2, padx=(12, 0))
        self.sale_qty = tk.StringVar(value="1")
        ttk.Entry(top, textvariable=self.sale_qty, width=8).grid(row=0, column=3, padx=8)
        ttk.Button(top, text="Adicionar", command=self.add_to_cart).grid(row=0, column=4, padx=4)
        top.columnconfigure(1, weight=1)

        self.cart_tree = ttk.Treeview(tab, columns=("name","quantity","price","subtotal"), show="headings", height=12)
        for c, title, width in [
            ("name","Mercadoria",400), ("quantity","Quantidade",120),
            ("price","Preço unitário",150), ("subtotal","Subtotal",150)
        ]:
            self.cart_tree.heading(c, text=title)
            self.cart_tree.column(c, width=width, anchor="w" if c == "name" else "center")
        self.cart_tree.pack(fill="both", expand=True)
        actions = ttk.Frame(tab, padding=(0, 10))
        actions.pack(fill="x")
        ttk.Button(actions, text="Remover linha selecionada", command=self.remove_cart_item).pack(side="left")
        ttk.Button(actions, text="Editar quantidade", command=self.edit_cart_quantity).pack(side="left", padx=(6, 0))
        ttk.Label(actions, text="Pagamento:").pack(side="left", padx=(20, 5))
        self.payment_method = tk.StringVar(value="Dinheiro")
        ttk.Combobox(actions, textvariable=self.payment_method, values=("Dinheiro", "Cartão", "Transferência", "Outro"),
                     state="readonly", width=18).pack(side="left")
        ttk.Label(actions, text="Desconto (%):").pack(side="left", padx=(16, 5))
        self.discount_percent = tk.StringVar(value="0")
        discount_input = ttk.Spinbox(
            actions, from_=0, to=100, increment=1, textvariable=self.discount_percent,
            width=5, command=self.refresh_cart_totals
        )
        discount_input.pack(side="left")
        discount_input.bind("<KeyRelease>", lambda _event: self.refresh_cart_totals())
        ttk.Button(actions, text="Finalizar venda", command=self.finish_sale, style="Accent.TButton").pack(side="right", padx=8)
        totals = ttk.Frame(tab)
        totals.pack(fill="x", pady=(0, 4))
        self.cart_subtotal_label = ttk.Label(totals, text="Subtotal: € 0,00")
        self.cart_subtotal_label.pack(side="right", padx=8)
        self.cart_discount_label = ttk.Label(totals, text="Desconto: € 0,00")
        self.cart_discount_label.pack(side="right", padx=8)
        self.cart_total_label = ttk.Label(totals, text="TOTAL: € 0,00", style="Title.TLabel")
        self.cart_total_label.pack(side="right", padx=8)
        ttk.Label(tab, text="O stock é reduzido automaticamente quando a venda é finalizada.",
                  foreground="#555").pack(anchor="w", pady=(4, 0))

    def _build_history_tab(self):
        tab = self.history_tab
        filters = ttk.Frame(tab)
        filters.pack(fill="x", pady=(0, 8))
        first_row = ttk.Frame(filters)
        first_row.pack(fill="x", pady=(0, 5))
        ttk.Label(first_row, text="N.º/data:").pack(side="left")
        self.history_search = tk.StringVar()
        ttk.Entry(first_row, textvariable=self.history_search, width=18).pack(side="left", padx=(5, 12))
        ttk.Label(first_row, text="De (AAAA-MM-DD):").pack(side="left")
        self.history_date_from = tk.StringVar()
        ttk.Entry(first_row, textvariable=self.history_date_from, width=12).pack(side="left", padx=(5, 12))
        ttk.Label(first_row, text="Até:").pack(side="left")
        self.history_date_to = tk.StringVar()
        ttk.Entry(first_row, textvariable=self.history_date_to, width=12).pack(side="left", padx=5)
        ttk.Label(first_row, text="Pagamento:").pack(side="left", padx=(12, 5))
        self.history_payment = tk.StringVar(value="Todos")
        ttk.Combobox(
            first_row, textvariable=self.history_payment,
            values=("Todos", "Dinheiro", "Cartão", "Transferência", "Outro"),
            state="readonly", width=16
        ).pack(side="left")

        second_row = ttk.Frame(filters)
        second_row.pack(fill="x")
        ttk.Label(second_row, text="Artigo:").pack(side="left")
        self.history_product = tk.StringVar()
        ttk.Entry(second_row, textvariable=self.history_product, width=28).pack(side="left", padx=(5, 10))
        self.active_history_filters = {
            "search": "", "date_from": "", "date_to": "",
            "payment_method": "Todos", "product_search": ""
        }
        ttk.Button(second_row, text="Aplicar filtros", command=self.apply_history_filters).pack(side="left", padx=3)
        ttk.Button(second_row, text="Limpar", command=self.clear_history_filters).pack(side="left", padx=3)
        ttk.Button(second_row, text="Exportar CSV", command=self.export_history_csv).pack(side="right")
        cols = ("id","date","total","payment","units","status")
        self.history_tree = ttk.Treeview(tab, columns=cols, show="headings")
        for c, title, width in [
            ("id","N.º venda",90), ("date","Data e hora",220), ("total","Total",130),
            ("payment","Pagamento",150), ("units","Unidades",100), ("status","Estado",100)
        ]:
            self.history_tree.heading(c, text=title)
            self.history_tree.column(c, width=width, anchor="center")
        self.history_tree.pack(fill="both", expand=True)
        self.history_tree.bind("<Double-1>", self.show_sale_details)
        self.history_tree.bind("<<TreeviewSelect>>", self._update_cancel_button_state)
        actions = ttk.Frame(tab, padding=(0, 8, 0, 0))
        actions.pack(fill="x")
        self.cancel_sale_button = ttk.Button(
            actions, text="Anular venda selecionada", command=self.cancel_selected_sale, state="disabled"
        )
        self.cancel_sale_button.pack(side="left")
        ttk.Label(actions, text="Duplo clique numa venda para ver os artigos e os dados da anulação.",
                  foreground="#555").pack(side="left", padx=10)

    def apply_history_filters(self):
        date_from = self.history_date_from.get().strip()
        date_to = self.history_date_to.get().strip()
        for label, value in (("inicial", date_from), ("final", date_to)):
            if value:
                try:
                    parsed = datetime.strptime(value, "%Y-%m-%d")
                    if parsed.strftime("%Y-%m-%d") != value:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Data inválida", f"Informe a data {label} no formato AAAA-MM-DD.")
                    return
        if date_from and date_to and date_from > date_to:
            messagebox.showerror("Período inválido", "A data inicial deve ser anterior ou igual à data final.")
            return
        self.active_history_filters = {
            "search": self.history_search.get().strip(),
            "date_from": date_from,
            "date_to": date_to,
            "payment_method": self.history_payment.get(),
            "product_search": self.history_product.get().strip()
        }
        self.refresh_history()

    def clear_history_filters(self):
        self.history_search.set("")
        self.history_date_from.set("")
        self.history_date_to.set("")
        self.history_payment.set("Todos")
        self.history_product.set("")
        self.active_history_filters = {
            "search": "", "date_from": "", "date_to": "",
            "payment_method": "Todos", "product_search": ""
        }
        self.refresh_history()

    def export_history_csv(self):
        rows = self.db.sales(**self.active_history_filters)
        if not rows:
            messagebox.showinfo("Sem resultados", "Não há vendas para exportar com os filtros atuais.")
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Exportar histórico de vendas", defaultextension=".csv",
            filetypes=(("Ficheiro CSV", "*.csv"),), initialfile="historico_vendas.csv"
        )
        if not path:
            return
        columns = (
            "Venda", "Data e hora", "Estado", "Pagamento", "Artigos", "Unidades",
            "Subtotal", "Desconto (%)", "Valor do desconto", "Total", "Motivo da anulação"
        )
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.DictWriter(output, fieldnames=columns, delimiter=";")
                writer.writeheader()
                for row in rows:
                    items = self.db.sale_items(row["id"])
                    article_list = " | ".join(
                        f'{item["product_name"]} x {item["quantity"]}' for item in items
                    )
                    writer.writerow({
                        "Venda": row["id"],
                        "Data e hora": row["sold_at"],
                        "Estado": "Anulada" if row["canceled_at"] else "Concluída",
                        "Pagamento": row["payment_method"],
                        "Artigos": article_list,
                        "Unidades": row["units"],
                        "Subtotal": f'{row["subtotal"]:.2f}'.replace(".", ","),
                        "Desconto (%)": f'{row["discount_percent"]:.2f}'.replace(".", ","),
                        "Valor do desconto": f'{row["discount_amount"]:.2f}'.replace(".", ","),
                        "Total": f'{row["total"]:.2f}'.replace(".", ","),
                        "Motivo da anulação": row["cancel_reason"] or ""
                    })
        except OSError as exc:
            messagebox.showerror("Falha na exportação", f"Não foi possível guardar o ficheiro.\n{exc}")
            return
        messagebox.showinfo("Exportação concluída", f"{len(rows)} venda(s) exportada(s).")

    def save_product(self):
        name = self.p_name.get().strip()
        code = self.p_code.get().strip()
        category = self.p_category.get().strip()
        if not name:
            messagebox.showwarning("Dados em falta", "O nome da mercadoria é obrigatório.")
            return
        try:
            cost = parse_price(self.p_cost.get())
            price = parse_price(self.p_price.get())
            stock = int(self.p_stock.get().strip())
            if stock < 0:
                raise ValueError("A quantidade em stock não pode ser negativa.")
        except ValueError as exc:
            messagebox.showerror("Dados inválidos", str(exc) if str(exc) else "A quantidade deve ser um número inteiro.")
            return
        try:
            if self.selected_product_id is None:
                self.db.add_product(name, code, category, cost, price, stock)
                message = "Mercadoria registada com sucesso."
            else:
                self.db.update_product(self.selected_product_id, name, code, category, cost, price, stock)
                message = "Mercadoria atualizada com sucesso."
        except sqlite3.IntegrityError:
            messagebox.showerror("Código duplicado", "Já existe uma mercadoria com esse código. Use outro código ou deixe-o vazio.")
            return
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Falha ao guardar",
                f"Não foi possível gravar a mercadoria na base de dados.\n{exc}"
            )
            return
        self.clear_product_form()
        self.refresh_all()
        messagebox.showinfo("Concluído", message)

    def clear_product_form(self):
        self.selected_product_id = None
        self.p_name.set("")
        self.p_code.set("")
        self.p_category.set("")
        self.p_cost.set("0,00")
        self.p_price.set("0,00")
        self.p_stock.set("0")
        for item in self.product_tree.selection():
            self.product_tree.selection_remove(item)

    def on_product_select(self, _event=None):
        selection = self.product_tree.selection()
        if not selection:
            return
        values = self.product_tree.item(selection[0], "values")
        self.selected_product_id = int(values[0])
        row = self.db.conn.execute("SELECT * FROM products WHERE id=?", (self.selected_product_id,)).fetchone()
        if row:
            self.p_name.set(row["name"])
            self.p_code.set(row["code"] or "")
            self.p_category.set(row["category"] or "")
            self.p_cost.set(str(row["cost"]).replace(".", ","))
            self.p_price.set(str(row["price"]).replace(".", ","))
            self.p_stock.set(str(row["stock"]))

    def delete_product(self):
        if self.selected_product_id is None:
            messagebox.showwarning("Selecionar artigo", "Selecione um artigo na tabela primeiro.")
            return
        if not messagebox.askyesno("Confirmar", "Tem a certeza de que pretende eliminar este artigo?"):
            return
        try:
            self.db.delete_product(self.selected_product_id)
            self.clear_product_form()
            self.refresh_all()
        except ValueError as exc:
            messagebox.showerror("Não é possível eliminar", str(exc))

    def add_to_cart(self):
        chosen = self.sale_combo.current()
        if chosen < 0:
            messagebox.showwarning("Selecionar artigo", "Escolha uma mercadoria.")
            return
        product_id = self.sale_product_ids[chosen]
        try:
            qty = int(self.sale_qty.get().strip())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Quantidade inválida", "A quantidade deve ser um número inteiro maior que zero.")
            return
        row = self.db.conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            messagebox.showerror("Erro", "A mercadoria já não existe.")
            return
        current_qty = self.cart.get(product_id, {}).get("quantity", 0)
        if current_qty + qty > row["stock"]:
            messagebox.showerror("Stock insuficiente", f"Disponível: {row['stock']} unidade(s). Já adicionadas ao carrinho: {current_qty}.")
            return
        if product_id not in self.cart:
            self.cart[product_id] = {"name": row["name"], "price": row["price"], "quantity": qty}
        else:
            self.cart[product_id]["quantity"] += qty
        self.refresh_cart()

    def remove_cart_item(self):
        selection = self.cart_tree.selection()
        if not selection:
            messagebox.showwarning("Selecionar linha", "Selecione uma linha do carrinho.")
            return
        product_id = int(self.cart_tree.item(selection[0], "tags")[0])
        self.cart.pop(product_id, None)
        self.refresh_cart()

    def edit_cart_quantity(self):
        selection = self.cart_tree.selection()
        if not selection:
            messagebox.showwarning("Selecionar linha", "Selecione uma linha do carrinho.")
            return
        product_id = int(self.cart_tree.item(selection[0], "tags")[0])
        item = self.cart.get(product_id)
        row = self.db.conn.execute(
            "SELECT name, stock FROM products WHERE id=?", (product_id,)
        ).fetchone()
        if item is None or row is None:
            messagebox.showerror("Artigo indisponível", "Atualize o carrinho: este artigo já não existe.")
            return
        if row["stock"] < 1:
            messagebox.showerror("Stock insuficiente", "Este artigo já não tem unidades disponíveis.")
            return
        quantity = simpledialog.askinteger(
            "Editar quantidade", f'Nova quantidade para {row["name"]} (stock: {row["stock"]}):',
            initialvalue=min(item["quantity"], row["stock"]), minvalue=1,
            maxvalue=row["stock"], parent=self
        )
        if quantity is None:
            return
        latest = self.db.conn.execute(
            "SELECT stock FROM products WHERE id=?", (product_id,)
        ).fetchone()
        if latest is None or quantity > latest["stock"]:
            messagebox.showerror("Stock insuficiente", "O stock mudou. Atualize a quantidade e tente novamente.")
            return
        item["quantity"] = quantity
        self.refresh_cart()

    def refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for product_id, item in self.cart.items():
            subtotal = item["quantity"] * item["price"]
            self.cart_tree.insert("", "end", values=(
                item["name"], item["quantity"], money(item["price"]), money(subtotal)
            ), tags=(str(product_id),))
        self.refresh_cart_totals()

    def refresh_cart_totals(self):
        try:
            subtotal, discount, total = calculate_discount(self.cart, self.discount_percent.get())
        except ValueError:
            subtotal = sum(
                (Decimal(str(item["price"])) * item["quantity"] for item in self.cart.values()),
                Decimal("0")
            )
            self.cart_subtotal_label.configure(text=f"Subtotal: {money(subtotal)}")
            self.cart_discount_label.configure(text="Desconto: —")
            self.cart_total_label.configure(text="TOTAL: —")
            return
        self.cart_subtotal_label.configure(text=f"Subtotal: {money(subtotal)}")
        self.cart_discount_label.configure(text=f"Desconto: {money(discount)}")
        self.cart_total_label.configure(text=f"TOTAL: {money(total)}")

    def finish_sale(self):
        if not self.cart:
            messagebox.showwarning("Carrinho vazio", "Adicione mercadorias antes de finalizar.")
            return
        try:
            subtotal, discount, total = calculate_discount(self.cart, self.discount_percent.get())
        except ValueError as exc:
            messagebox.showerror("Desconto inválido", str(exc))
            return
        discount_percent = Decimal(self.discount_percent.get().replace(",", "."))
        confirmation = (
            f"Subtotal: {money(subtotal)}\n"
            f"Desconto ({discount_percent:g}%): -{money(discount)}\n"
            f"Total: {money(total)}\n\nFinalizar venda?"
        )
        if not messagebox.askyesno("Confirmar venda", confirmation):
            return
        try:
            sale_id, total = self.db.create_sale(
                self.cart, self.payment_method.get(), discount_percent
            )
            self.cart.clear()
            self.discount_percent.set("0")
            self.refresh_cart()
            self.refresh_all()
            messagebox.showinfo("Venda registada", f"Venda n.º {sale_id} registada.\nTotal: {money(total)}")
        except ValueError as exc:
            messagebox.showerror("Não foi possível finalizar", str(exc))

    def refresh_products(self):
        self.product_tree.delete(*self.product_tree.get_children())
        limit = self.stock_alert_limit if self.low_stock_only.get() else None
        rows = self.db.products(self.product_search.get(), low_stock_limit=limit)
        for row in rows:
            self.product_tree.insert("", "end", values=(
                row["id"], row["name"], row["code"] or "", row["category"] or "",
                money(row["cost"]), money(row["price"]), row["stock"]
            ))
        self.sale_product_ids = []
        choices = []
        for row in self.db.products():
            if row["stock"] > 0:
                self.sale_product_ids.append(row["id"])
                choices.append(f'{row["name"]} | Stock: {row["stock"]} | {money(row["price"])}')
        self.sale_combo["values"] = choices
        if self.sale_combo.current() >= len(choices):
            self.sale_combo.set("")

    def save_stock_alert_limit(self, _event=None):
        try:
            limit = int(self.stock_limit_var.get().strip())
            self.db.set_stock_alert_limit(limit)
        except ValueError as exc:
            messagebox.showerror("Limite inválido", str(exc))
            self.stock_limit_var.set(str(self.stock_alert_limit))
            return
        self.stock_alert_limit = limit
        self.metric_boxes["low"].configure(text=f"Stock baixo (≤ {limit})")
        self.refresh_products()
        self.refresh_metrics()

    def refresh_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        for row in self.db.sales(**self.active_history_filters):
            self.history_tree.insert("", "end", values=(
                row["id"], row["sold_at"], money(row["total"]), row["payment_method"],
                row["units"], "Anulada" if row["canceled_at"] else "Concluída"
            ))
        self._update_cancel_button_state()

    def _update_cancel_button_state(self, _event=None):
        selection = self.history_tree.selection()
        can_cancel = bool(selection) and self.history_tree.item(selection[0], "values")[5] == "Concluída"
        self.cancel_sale_button.configure(state="normal" if can_cancel else "disabled")

    def cancel_selected_sale(self):
        selection = self.history_tree.selection()
        if not selection:
            return
        sale_id = int(self.history_tree.item(selection[0], "values")[0])
        reason = simpledialog.askstring(
            "Motivo da anulação", f"Indique o motivo para anular a venda n.º {sale_id}:", parent=self
        )
        if reason is None:
            return
        reason = reason.strip()
        if not reason:
            messagebox.showwarning("Motivo obrigatório", "Informe o motivo da anulação.")
            return
        if not messagebox.askyesno(
            "Confirmar anulação",
            f"Anular a venda n.º {sale_id}? O stock dos artigos será reposto.",
            parent=self
        ):
            return
        try:
            canceled_at = self.db.cancel_sale(sale_id, reason)
            self.refresh_all()
            messagebox.showinfo(
                "Venda anulada", f"Venda n.º {sale_id} anulada em {canceled_at}. O stock foi reposto."
            )
        except ValueError as exc:
            messagebox.showerror("Não foi possível anular", str(exc))

    def show_sale_details(self, _event=None):
        selection = self.history_tree.selection()
        if not selection:
            return
        sale_id = int(self.history_tree.item(selection[0], "values")[0])
        sale = self.db.sale(sale_id)
        items = self.db.sale_items(sale_id)
        win = tk.Toplevel(self)
        win.title(f"Detalhes da venda n.º {sale_id}")
        win.geometry("650x350")
        ttk.Label(win, text=f"Venda n.º {sale_id}", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        if sale["canceled_at"]:
            status_text = f"Anulada em {sale['canceled_at']} | Motivo: {sale['cancel_reason']}"
        else:
            status_text = f"Concluída | Pagamento: {sale['payment_method']}"
        ttk.Label(win, text=status_text, wraplength=620).pack(anchor="w", padx=12, pady=(0, 10))
        tree = ttk.Treeview(win, columns=("name","qty","price","subtotal"), show="headings")
        for c, title, width in [
            ("name","Mercadoria",280), ("qty","Quantidade",90),
            ("price","Preço unitário",120), ("subtotal","Subtotal",120)
        ]:
            tree.heading(c, text=title)
            tree.column(c, width=width, anchor="w" if c == "name" else "center")
        tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for item in items:
            tree.insert("", "end", values=(
                item["product_name"], item["quantity"], money(item["unit_price"]), money(item["subtotal"])
            ))
        subtotal = sum(item["subtotal"] for item in items)
        ttk.Label(
            win,
            text=(f"Subtotal: {money(subtotal)}  |  Desconto ({sale['discount_percent']:g}%): "
                  f"-{money(sale['discount_amount'])}  |  Total: {money(sale['total'])}"),
            style="Metric.TLabel"
        ).pack(anchor="e", padx=12, pady=(0, 12))

    def refresh_metrics(self):
        today, sales, products, units, low = self.db.summary(self.stock_alert_limit)
        self.metric_labels["today"].configure(text=money(today))
        self.metric_labels["sales"].configure(text=str(sales))
        self.metric_labels["products"].configure(text=str(products))
        self.metric_labels["units"].configure(text=str(units))
        self.metric_labels["low"].configure(text=str(low))

    def refresh_all(self):
        self.refresh_products()
        self.refresh_history()
        self.refresh_metrics()

    def on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = SalesApp()
    app.mainloop()
