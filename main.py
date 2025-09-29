# main.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, date
import csv
import os

from db import init_db, fetch_all_books, fetch_filtered_books, upsert_book, delete_book, delete_all_books, get_unique_categories

# Optional charts
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB = True
except Exception:
    MATPLOTLIB = False

# Initialize DB
init_db()

# Helper to convert a DB row into friendly sentence (based on PDF examples)
def row_to_sentence(row):
    # row: (id, title, subtitle, authors, publisher, published_date, category, distribution_expense)
    _, title, subtitle, authors, publisher, published_date, category, expense = row
    parts = [f"Book '{title}'"]
    if subtitle:
        parts.append(f"({subtitle})")
    if authors:
        parts.append(f"by {authors}")
    if publisher:
        parts.append(f"published by {publisher}")
    if published_date:
        parts.append(f"on {published_date}")
    if category:
        parts.append(f"in {category}")
    parts.append(f"had distribution expense ₹{expense}")
    return " ".join(parts)

class App:
    def __init__(self, root):
        self.root = root
        root.title("Books Distribution Expense Tracker")
        root.geometry("1200x700")

        # Top frame for summary + filters
        top = ttk.Frame(root, padding=8)
        top.pack(fill=tk.X)

        self.total_label = ttk.Label(top, text="Total: ₹0.00", font=("Helvetica", 12, "bold"))
        self.total_label.pack(side=tk.LEFT)

        filter_frame = ttk.Frame(top)
        filter_frame.pack(side=tk.RIGHT)

        ttk.Label(filter_frame, text="Keyword").grid(row=0, column=0, padx=4)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=24)
        search_entry.grid(row=0, column=1, padx=4)

        ttk.Label(filter_frame, text="Category").grid(row=0, column=2, padx=4)
        cats = ["All"] + get_unique_categories()
        self.cat_var = tk.StringVar(value="All")
        cat_cb = ttk.Combobox(filter_frame, values=cats, textvariable=self.cat_var, state="readonly", width=20)
        cat_cb.grid(row=0, column=3, padx=4)

        ttk.Button(filter_frame, text="Filter", command=self.load_rows).grid(row=0, column=4, padx=4)
        ttk.Button(filter_frame, text="Export CSV", command=self.export_csv).grid(row=0, column=5, padx=4)
        ttk.Button(filter_frame, text="Show Chart", command=self.show_chart).grid(row=0, column=6, padx=4)

        # Main splitter frames
        main = ttk.Frame(root, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Left: data entry & actions
        ttk.Label(left, text="Data Entry", font=("Helvetica", 14, "bold")).pack(pady=(0,8))

        ttk.Label(left, text="ID (ISBN)").pack(anchor=tk.W)
        self.id_ent = ttk.Entry(left, width=30)
        self.id_ent.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Title").pack(anchor=tk.W)
        self.title_ent = ttk.Entry(left, width=30)
        self.title_ent.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Subtitle").pack(anchor=tk.W)
        self.subtitle_ent = ttk.Entry(left, width=30)
        self.subtitle_ent.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Authors").pack(anchor=tk.W)
        self.authors_ent = ttk.Entry(left, width=30)
        self.authors_ent.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Publisher").pack(anchor=tk.W)
        self.publisher_ent = ttk.Entry(left, width=30)
        self.publisher_ent.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Published Date (YYYY-MM-DD)").pack(anchor=tk.W)
        self.pubdate = DateEntry(left, width=28, date_pattern='yyyy-mm-dd')
        self.pubdate.set_date(date.today())
        self.pubdate.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Category").pack(anchor=tk.W)
        self.category_ent = ttk.Entry(left, width=30)
        self.category_ent.pack(fill=tk.X, pady=2)

        ttk.Label(left, text="Distribution Expense (₹)").pack(anchor=tk.W)
        self.exp_ent = ttk.Entry(left, width=30)
        self.exp_ent.pack(fill=tk.X, pady=2)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=8)
        ttk.Button(btn_frame, text="Add / Update", command=self.add_or_update).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(btn_frame, text="Clear", command=self.clear_form).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        # Convert to sentence and confirm add (based on PDF's expenseToWordsBeforeAdding)
        ttk.Button(left, text="Preview as Text & Add", command=self.preview_and_add).pack(fill=tk.X, pady=(4,0))

        # Right: Treeview table + action buttons
        cols = ("id","title","subtitle","authors","publisher","published_date","category","distribution_expense")
        self.tree = ttk.Treeview(right, columns=cols, show='headings', selectmode='browse')
        for c in cols:
            self.tree.heading(c, text=c.replace("_"," ").title())
            if c == "title":
                self.tree.column(c, width=260)
            elif c == "distribution_expense":
                self.tree.column(c, width=120, anchor=tk.E)
            else:
                self.tree.column(c, width=140)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        action_frame = ttk.Frame(right)
        action_frame.pack(fill=tk.X, pady=6)
        ttk.Button(action_frame, text="View Selected (Populate Left)", command=self.populate_from_selection).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Convert Selected → Sentence", command=self.selected_to_words).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Delete All", command=self.delete_all).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Refresh", command=self.load_rows).pack(side=tk.LEFT, padx=4)

        # initial load
        self.load_rows()

    def load_rows(self):
        keyword = self.search_var.get().strip() or None
        category = self.cat_var.get()
        if category == "All":
            category = None
        rows = fetch_filtered_books(keyword=keyword, category=category)
        # clear
        for r in self.tree.get_children():
            self.tree.delete(r)
        total = 0.0
        for r in rows:
            self.tree.insert("", tk.END, values=r)
            try:
                total += float(r[7])
            except Exception:
                pass
        self.total_label.config(text=f"Total: ₹{total:,.2f}")

    def clear_form(self):
        self.id_ent.delete(0, tk.END)
        self.title_ent.delete(0, tk.END)
        self.subtitle_ent.delete(0, tk.END)
        self.authors_ent.delete(0, tk.END)
        self.publisher_ent.delete(0, tk.END)
        self.pubdate.set_date(date.today())
        self.category_ent.delete(0, tk.END)
        self.exp_ent.delete(0, tk.END)

    def add_or_update(self):
        book_id = self.id_ent.get().strip()
        title = self.title_ent.get().strip()
        subtitle = self.subtitle_ent.get().strip()
        authors = self.authors_ent.get().strip()
        publisher = self.publisher_ent.get().strip()
        pubdate = self.pubdate.get_date().isoformat()
        category = self.category_ent.get().strip()
        try:
            expense = float(self.exp_ent.get().strip())
        except Exception:
            messagebox.showwarning("Invalid", "Distribution expense must be a number.")
            return
        if not book_id or not title:
            messagebox.showwarning("Missing", "ID and Title are required.")
            return
        upsert_book((book_id, title, subtitle, authors, publisher, pubdate, category, expense))
        messagebox.showinfo("Saved", "Book record added/updated.")
        self.load_rows()
        # refresh category combobox data if needed
        self.clear_form()

    def preview_and_add(self):
        # Create sentence and ask confirm before adding (like PDF)
        book = (
            self.id_ent.get().strip(),
            self.title_ent.get().strip(),
            self.subtitle_ent.get().strip(),
            self.authors_ent.get().strip(),
            self.publisher_ent.get().strip(),
            self.pubdate.get_date().isoformat(),
            self.category_ent.get().strip(),
            self.exp_ent.get().strip()
        )
        if not book[0] or not book[1] or not book[7]:
            messagebox.showwarning("Incomplete", "Please fill ID, Title and Distribution Expense.")
            return
        try:
            float(book[7])
        except:
            messagebox.showwarning("Invalid", "Distribution expense must be numeric.")
            return
        sentence = f"Book '{book[1]}' by {book[3] or 'Unknown'} published by {book[4] or 'Unknown'} on {book[5]} in {book[6] or 'Unknown'} has distribution expense ₹{book[7]}."
        if messagebox.askyesno("Confirm add", f"{sentence}\n\nAdd to database?"):
            upsert_book((book[0], book[1], book[2], book[3], book[4], book[5], book[6], float(book[7])))
            messagebox.showinfo("Added", "Book added.")
            self.load_rows()
            self.clear_form()

    def on_select(self, event):
        pass  # placeholder if needed

    def populate_from_selection(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a row.")
            return
        vals = self.tree.item(sel[0])['values']
        # (id, title, subtitle, authors, publisher, published_date, category, distribution_expense)
        self.id_ent.delete(0, tk.END); self.id_ent.insert(0, vals[0])
        self.title_ent.delete(0, tk.END); self.title_ent.insert(0, vals[1])
        self.subtitle_ent.delete(0, tk.END); self.subtitle_ent.insert(0, vals[2] or "")
        self.authors_ent.delete(0, tk.END); self.authors_ent.insert(0, vals[3] or "")
        self.publisher_ent.delete(0, tk.END); self.publisher_ent.insert(0, vals[4] or "")
        try:
            self.pubdate.set_date(vals[5])
        except Exception:
            pass
        self.category_ent.delete(0, tk.END); self.category_ent.insert(0, vals[6] or "")
        self.exp_ent.delete(0, tk.END); self.exp_ent.insert(0, str(vals[7]))

    def selected_to_words(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a row.")
            return
        vals = self.tree.item(sel[0])['values']
        messagebox.showinfo("Selected as text", row_to_sentence(vals))

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a row.")
            return
        vals = self.tree.item(sel[0])['values']
        book_id = vals[0]
        if messagebox.askyesno("Confirm", f"Delete book '{vals[1]}'?"):
            delete_book(book_id)
            messagebox.showinfo("Deleted", "Record deleted.")
            self.load_rows()

    def delete_all(self):
        if messagebox.askyesno("Confirm", "Delete ALL records from database? This cannot be undone.", icon='warning'):
            delete_all_books()
            messagebox.showinfo("Deleted", "All records deleted.")
            self.load_rows()

    def export_csv(self):
        rows = fetch_filtered_books(keyword=self.search_var.get().strip() or None, category=(None if self.cat_var.get()=="All" else self.cat_var.get()))
        if not rows:
            messagebox.showinfo("None", "No rows to export.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fpath:
            return
        with open(fpath, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id","title","subtitle","authors","publisher","published_date","category","distribution_expense"])
            for r in rows:
                writer.writerow(r)
        messagebox.showinfo("Exported", f"Exported {len(rows)} rows to {fpath}")

    def show_chart(self):
        if not MATPLOTLIB:
            messagebox.showwarning("Missing", "matplotlib required for charts. Install via pip.")
            return
        # aggregate by category
        rows = fetch_filtered_books(keyword=self.search_var.get().strip() or None, category=(None if self.cat_var.get()=="All" else self.cat_var.get()))
        agg = {}
        for r in rows:
            cat = r[6] or "Uncategorized"
            try:
                amt = float(r[7])
            except:
                amt = 0.0
            agg[cat] = agg.get(cat, 0.0) + amt
        if not agg:
            messagebox.showinfo("No data", "No data to chart.")
            return
        # Create simple bar chart
        win = tk.Toplevel(self.root)
        win.title("Distribution expense by category")
        fig = Figure(figsize=(8,4))
        ax = fig.add_subplot(111)
        labels = list(agg.keys())
        values = list(agg.values())
        ax.bar(labels, values)
        ax.set_ylabel("Expense (₹)")
        ax.set_title("Distribution Expense by Category")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
