import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import sqlite3
import os
from datetime import datetime
from db.database import get_connection


class TabSpese(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.ordine_colonna = None
        self.ordine_reverse = False

        # Pulsanti
        btn_frame = tk.Frame(self, bg="#f7f1e1")
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="➕ Nuova Spesa", command=self.nuova_spesa).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🗑️ Elimina Spesa", command=self.elimina_spesa).pack(side="left", padx=5)

        # Treeview
        self.tree = ttk.Treeview(self, columns=("Data", "Categoria", "Descrizione", "Importo", "Metodo", "Note"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        colonne = {
            "Data": 100,
            "Categoria": 120,
            "Descrizione": 200,
            "Importo": 100,
            "Metodo": 100,
            "Note": 250,
        }

        for col, width in colonne.items():
            display_text = "Nome" if col == "Descrizione" else col
            self.tree.heading(col, text=display_text, command=lambda c=col: self.ordina_per(c))
            self.tree.column(col, width=width, anchor="center")

        self.tree.bind("<Double-1>", self.modifica_spesa)

        self.carica_spese()

    def carica_spese(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spese_gestione")
        righe = cursor.fetchall()
        conn.close()

        for r in righe:
            self.tree.insert("", "end", iid=r["id"], values=(
                r["data"], r["categoria"], r["descrizione"], f"{r['importo']:.2f}", r["metodo_pagamento"] or "", r["note"] or ""
            ))

    def ordina_per(self, colonna):
        dati = [(self.tree.set(k, colonna), k) for k in self.tree.get_children("")]
        try:
            dati.sort(key=lambda t: float(t[0]) if colonna == "Importo" else t[0], reverse=self.ordine_colonna == colonna and not self.ordine_reverse)
        except ValueError:
            dati.sort(key=lambda t: t[0], reverse=self.ordine_colonna == colonna and not self.ordine_reverse)

        for index, (_, k) in enumerate(dati):
            self.tree.move(k, "", index)

        self.ordine_colonna = colonna
        self.ordine_reverse = not self.ordine_reverse

    def nuova_spesa(self):
        FinestraSpesa(self, titolo="Nuova Spesa")

    def modifica_spesa(self, event=None):
        item_id = self.tree.focus()
        if not item_id:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spese_gestione WHERE id=?", (item_id,))
        spesa = cursor.fetchone()
        conn.close()
        if spesa:
            FinestraSpesa(self, titolo="Modifica Spesa", spesa=spesa)

    def elimina_spesa(self):
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showinfo("Info", "Seleziona una spesa da eliminare.")
            return

        risposta = messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questa spesa?")
        if not risposta:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM spese_gestione WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        self.carica_spese()


class FinestraSpesa(tk.Toplevel):
    def __init__(self, parent, titolo, spesa=None):
        super().__init__(parent)
        self.parent = parent
        self.spesa = spesa
        self.title(titolo)
        self.geometry("500x400")
        self.resizable(False, False)
        self.configure(bg="#f7f1e1")

        self.campi = {}

        def add_row(label_text, key, default=""):
            frame = tk.Frame(self, bg="#f7f1e1")
            frame.pack(fill="x", padx=10, pady=5)
            tk.Label(frame, text=label_text, width=15, anchor="w", bg="#f7f1e1").pack(side="left")
            entry = tk.Entry(frame)
            entry.pack(fill="x", expand=True)
            entry.insert(0, default)
            self.campi[key] = entry

        add_row("Data (YYYY-MM-DD):", "data", self.spesa["data"] if spesa else datetime.now().strftime("%Y-%m-%d"))
        add_row("Categoria:", "categoria", self.spesa["categoria"] if spesa else "")
        add_row("Nome:", "descrizione", self.spesa["descrizione"] if spesa else "")
        add_row("Importo:", "importo", str(self.spesa["importo"]) if spesa else "")
        add_row("Metodo pagamento:", "metodo_pagamento", self.spesa["metodo_pagamento"] if spesa else "")

        # Area note con scorrimento
        tk.Label(self, text="Note:", bg="#f7f1e1").pack(anchor="w", padx=10)
        self.note_text = ScrolledText(self, height=6, wrap="word")
        self.note_text.pack(fill="both", padx=10, pady=(0,10), expand=False)
        if spesa and spesa["note"]:
            self.note_text.insert("1.0", spesa["note"])

        # Pulsanti
        btn_frame = tk.Frame(self, bg="#f7f1e1")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="💾 Salva", command=self.salva).pack(side="left", padx=10)

        if self.spesa:
            tk.Button(
                btn_frame,
                text="🔁 Ricompra",
                command=self.ricompra
            ).pack(side="left", padx=10)

        tk.Button(btn_frame, text="❌ Chiudi", command=self.destroy).pack(side="left", padx=10)


    def ricompra(self):
        try:
            data_oggi = datetime.now().strftime("%Y-%m-%d")

            # aggiorna VISIVAMENTE il campo data
            self.campi["data"].delete(0, "end")
            self.campi["data"].insert(0, data_oggi)

            categoria = self.campi["categoria"].get().strip()
            descrizione = self.campi["descrizione"].get().strip()
            metodo = self.campi["metodo_pagamento"].get().strip()
            note = self.note_text.get("1.0", "end").strip()
            importo = float(self.campi["importo"].get().strip())

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO spese_gestione
                (data, categoria, descrizione, importo, metodo_pagamento, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data_oggi, categoria, descrizione, importo, metodo, note))

            conn.commit()
            conn.close()

            self.parent.carica_spese()

            messagebox.showinfo(
                "Ricompra",
                "Nuova spesa inserita correttamente.",
                parent=self
            )

            self.destroy()

        except ValueError:
            messagebox.showerror("Errore", "Importo non valido.")



    def salva(self):
        try:
            data = self.campi["data"].get().strip()
            categoria = self.campi["categoria"].get().strip()
            descrizione = self.campi["descrizione"].get().strip()
            importo = float(self.campi["importo"].get().strip())
            metodo = self.campi["metodo_pagamento"].get().strip()
            note = self.note_text.get("1.0", "end").strip()

            conn = get_connection()
            cursor = conn.cursor()

            if self.spesa:
                cursor.execute("""
                    UPDATE spese_gestione SET data=?, categoria=?, descrizione=?, importo=?, metodo_pagamento=?, note=?
                    WHERE id=?
                """, (data, categoria, descrizione, importo, metodo, note, self.spesa["id"]))
            else:
                cursor.execute("""
                    INSERT INTO spese_gestione (data, categoria, descrizione, importo, metodo_pagamento, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data, categoria, descrizione, importo, metodo, note))

            conn.commit()
            conn.close()

            self.parent.carica_spese()
            self.destroy()

        except ValueError:
            messagebox.showerror("Errore", "Importo non valido.")
