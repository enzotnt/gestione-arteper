# utils/seleziona_componenti.py


import tkinter as tk
from tkinter import ttk, messagebox
from db.database import get_connection

class SelezionaComponentiDialog_logic(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Seleziona Componenti dal Magazzino")
        self.geometry("900x500")
        self.transient(parent)
        self.grab_set()

        self.callback = callback
        self.componenti_selezionati = {}

        self.ordina_per = "nome"
        self.ordine_crescente = True

        self.crea_widget()
        self.carica_magazzino()

    def crea_widget(self):
        self.tree = ttk.Treeview(self, columns=("nome", "unita", "quantita", "costo_unitario"), show="headings")
        self.tree.heading("nome", text="Nome", command=lambda: self.ordina("nome"))
        self.tree.heading("unita", text="Unità", command=lambda: self.ordina("unita"))
        self.tree.heading("quantita", text="Disponibile", command=lambda: self.ordina("quantita"))
        self.tree.heading("costo_unitario", text="Costo unitario", command=lambda: self.ordina("costo_unitario"))
        self.tree.pack(fill=tk.BOTH, expand=True)

        frame_controlli = tk.Frame(self)
        frame_controlli.pack(pady=10)

        tk.Label(frame_controlli, text="Quantità:").grid(row=0, column=0)
        self.entry_quantita = tk.Entry(frame_controlli, width=10)
        self.entry_quantita.grid(row=0, column=1)

        tk.Label(frame_controlli, text="Moltiplicatore:").grid(row=0, column=2)
        self.entry_moltiplicatore = tk.Entry(frame_controlli, width=10)
        self.entry_moltiplicatore.insert(0, "3.0")
        self.entry_moltiplicatore.grid(row=0, column=3)

        btn_aggiungi = tk.Button(frame_controlli, text="Aggiungi", command=self.aggiungi_componente)
        btn_aggiungi.grid(row=0, column=4, padx=10)

        self.box_selezionati = tk.Listbox(self, height=6)
        self.box_selezionati.pack(fill=tk.X, padx=20, pady=5)

        btn_fine = tk.Button(self, text="Conferma", command=self.conferma)
        btn_fine.pack(pady=10)

    def ordina(self, colonna):
        if self.ordina_per == colonna:
            self.ordine_crescente = not self.ordine_crescente
        else:
            self.ordina_per = colonna
            self.ordine_crescente = True
        self.carica_magazzino()

    def carica_magazzino(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"""
            SELECT id, nome, unita, quantita, costo_unitario
            FROM magazzino
            ORDER BY {self.ordina_per} {'ASC' if self.ordine_crescente else 'DESC'}
        """)
        rows = cur.fetchall()
        conn.close()

        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", tk.END, iid=r[0], values=r[1:])

    def aggiungi_componente(self):
        try:
            componente_id = int(self.tree.selection()[0])
        except IndexError:
            messagebox.showwarning("Attenzione", "Seleziona un componente.")
            return

        try:
            qta = float(self.entry_quantita.get())
            m = float(self.entry_moltiplicatore.get())
            if qta <= 0 or m <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Errore", "Inserisci quantità e moltiplicatore validi (>0).")
            return

        self.componenti_selezionati[componente_id] = (qta, m)
        self.aggiorna_lista_selezionati()

    def aggiorna_lista_selezionati(self):
        self.box_selezionati.delete(0, tk.END)
        for comp_id, (qta, m) in self.componenti_selezionati.items():
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT nome FROM magazzino WHERE id = ?", (comp_id,))
            nome = cur.fetchone()[0]
            conn.close()
            self.box_selezionati.insert(tk.END, f"{nome} - Qta: {qta}, Moltiplicatore: {m}")

    def conferma(self):
        if not self.componenti_selezionati:
            messagebox.showwarning("Attenzione", "Nessun componente selezionato.")
            return

        # Converte il dizionario in lista di dizionari per passare alla callback
        lista = []
        for comp_id, (qta, moltiplicatore) in self.componenti_selezionati.items():
            lista.append({
                "componente_id": comp_id,
                "quantita": qta,
                "moltiplicatore": moltiplicatore
            })

        if self.callback:
            self.callback(lista)
        self.destroy()
