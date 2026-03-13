# gui/tab_venduti.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from db.database import get_connection
import os
from datetime import datetime

from logic.venduti import VendutiManager
from utils.gui_utils import ordina_colonna_treeview, mostra_immagine_zoom
import sqlite3

class TabVenduti(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Custom.TFrame")

        self.photo_images = {}  # per tenere in vita le immagini caricate
        self.ordine_colonna = None
        self.ordine_reverse = False
        self.stato_ordinamento = {'colonna': None, 'ascendente': True}

        # modalità di visualizzazione: True = raggruppata per cliente, False = dettaglio per vendita
        self.aggregated = True

        # Crea l'interfaccia
        self._crea_pulsanti()
        self.tree = None
        self.carica_dati()

    def _crea_pulsanti(self):
        """Crea la barra dei pulsanti."""
        btn_frame = tk.Frame(self, bg="#f7f1e1")
        btn_frame.pack(pady=(10, 5), anchor="w", fill="x")

        btn_opts = {
            "font": ("Segoe Print", 10, "bold"),
            "relief": "raised",
            "bd": 2,
            "bg": "#deb887",
            "activebackground": "#d2b48c",
            "fg": "#5a3e1b",
            "activeforeground": "#3e2f1c",
            "cursor": "hand2",
            "padx": 10,
            "pady": 6,
        }

        self.btn_aggiorna = tk.Button(btn_frame, text="🔄 Aggiorna", command=self.carica_dati, **btn_opts)
        self.btn_aggiorna.pack(side="left", padx=6, pady=5)

        self.btn_raggruppa = tk.Button(btn_frame, text="🔁 Vista dettaglio",
                                       command=self.toggle_aggregazione, **btn_opts)
        self.btn_raggruppa.pack(side="left", padx=6, pady=5)

        btn_elimina_opts = btn_opts.copy()
        btn_elimina_opts.update({
            "bg": "#d9534f",
            "activebackground": "#c9302c",
            "fg": "white",
            "activeforeground": "white",
        })
        self.btn_elimina = tk.Button(btn_frame, text="🗑️ Elimina vendita",
                                     command=self.elimina_vendita, **btn_elimina_opts)
        self.btn_elimina.pack(side="left", padx=6, pady=5)

        def on_enter(e):
            e.widget['background'] = '#f0d9b5'

        def on_leave(e):
            if e.widget != self.btn_elimina:
                e.widget['background'] = btn_opts["bg"]

        for btn in [self.btn_aggiorna, self.btn_raggruppa, self.btn_elimina]:
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def carica_dati(self):
        """Popola la tree con i dati del manager."""
        print("\n" + "=" * 60)
        print("🔍 DEBUG - TabVenduti.carica_dati()")
        print("=" * 60)
        print(f"   Modalità aggregata: {self.aggregated}")

        # Distruggi tree precedente se esistente
        if self.tree:
            self.tree.destroy()

        if self.aggregated:
            # Vista aggregata per cliente - ora usa gli ORDINI
            columns = ("Cliente", "Ordini", "Quantità tot.", "Totale (€)", "Ultimo ordine")
            col_widths = {"Cliente": 160, "Ordini": 400, "Quantità tot.": 100,
                          "Totale (€)": 100, "Ultimo ordine": 140}
            print("   📊 Chiamo VendutiManager.get_ordini_aggregati()")
            dati = VendutiManager.get_ordini_aggregati()
        else:
            # Vista dettaglio (per ora lasciamo venduti)
            columns = ("ID", "Data", "Cliente", "Quantità", "Totale", "Unitario",
                       "Costo", "Ricavo", "Progetto", "Note")
            col_widths = {
                "ID": 50, "Data": 140, "Cliente": 120, "Quantità": 80,
                "Totale": 80, "Unitario": 80, "Costo": 80, "Ricavo": 80,
                "Progetto": 200, "Note": 250
            }
            print("   📊 Chiamo VendutiManager.get_vendite_dettaglio()")
            dati = VendutiManager.get_vendite_dettaglio()

        print(f"   📊 Dati ricevuti: {len(dati)} record")

        # Crea nuova tree
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings")
        self.tree.heading("#0", text="🖼️")
        self.tree.column("#0", width=80, anchor="center", stretch=False)

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.ordina_per(c))
            width = col_widths.get(col, 100)
            self.tree.column(col, width=width, anchor="center", stretch=False)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", self.apri_dettaglio)

        # Popola la tree
        if self.aggregated:
            self._popola_tree_aggregata_ordini(dati)  # Nuova funzione
        else:
            self._popola_tree_dettaglio(dati)

        # Riapplica ordinamento se necessario
        if self.ordine_colonna:
            self.ordina_per(self.ordine_colonna, forza=True)

        print("=" * 60)

    def _popola_tree_aggregata_ordini(self, dati):
        """Popola la tree con dati aggregati per cliente (dagli ordini)."""
        for cliente_info in dati:
            self.tree.insert("", "end", text="", values=(
                cliente_info["cliente"],
                cliente_info["items_str"],  # Ora mostra gli ordini
                cliente_info["quantita_totale"],
                f"{cliente_info['totale']:.2f}€",
                cliente_info["ultima_data"] or ""
            ))

    def _popola_tree_aggregata(self, dati):
        """Popola la tree con dati aggregati per cliente."""
        for cliente_info in dati:
            items_str = VendutiManager.format_items_string(cliente_info["items"])
            self.tree.insert("", "end", text="", values=(
                cliente_info["cliente"],
                items_str,
                cliente_info["quantita_totale"],
                f"{cliente_info['totale']:.2f}€",
                cliente_info["ultima_data"] or ""
            ))

    def _popola_tree_dettaglio(self, dati):
        """Popola la tree con dati dettagliati per vendita."""
        from PIL import Image
        resample = getattr(Image, 'Resampling', Image).LANCZOS
        self.photo_images = {}

        for v in dati:
            photo = None
            if v["immagine_percorso"] and os.path.exists(v["immagine_percorso"]):
                try:
                    img = Image.open(v["immagine_percorso"])
                    img = img.resize((32, 32), resample)
                    photo = ImageTk.PhotoImage(img)
                    self.photo_images[v["id"]] = photo
                except Exception as e:
                    print(f"[AVVISO] Impossibile caricare immagine per ID {v['id']}: {e}")

            valori = [
                v["id"], v["data"] or "", v["cliente"] or "", v["quantita"] or 0,
                f"{v['prezzo_totale']:.2f}€" if v['prezzo_totale'] else "N/A",
                f"{v['prezzo_unitario']:.2f}€" if v['prezzo_unitario'] else "N/A",
                f"{v['costo_totale']:.2f}€" if v['costo_totale'] else "N/A",
                f"{v['ricavo']:.2f}€" if v['ricavo'] else "N/A",
                         v["progetto_nome"] or "",
                         v["note"] or ""
            ]

            kwargs = {"parent": "", "index": "end", "text": "", "values": valori}
            if photo:
                kwargs["image"] = photo

            self.tree.insert(**kwargs)

    def ordina_per(self, colonna, forza=False):
        """Ordina la treeview per la colonna specificata."""
        self.stato_ordinamento = ordina_colonna_treeview(
            self.tree, colonna, self.stato_ordinamento
        )
        self.ordine_colonna = self.stato_ordinamento['colonna']
        self.ordine_reverse = not self.stato_ordinamento['ascendente']

    def toggle_aggregazione(self):
        """Alterna tra vista aggregata per cliente e vista dettaglio."""
        self.aggregated = not self.aggregated
        self.btn_raggruppa.config(
            text="🔁 Raggruppa Clienti" if not self.aggregated else "🔁 Vista dettaglio"
        )
        self.carica_dati()

    def apri_dettaglio(self, event=None):
        """Apre il dettaglio della riga selezionata."""
        selezione = self.tree.selection()
        if not selezione:
            messagebox.showinfo("Info", "Seleziona una riga per visualizzarne il dettaglio.")
            return

        vals = self.tree.item(selezione[0])['values']

        if self.aggregated:
            cliente = vals[0]
            self._mostra_dettagli_cliente(cliente)
        else:
            try:
                item_id = int(vals[0])
                # 🔥 Qui possiamo passare anche altri dati se necessario
                dettaglio = DettaglioVendita(self, item_id, self)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile aprire il dettaglio della vendita: {e}")

    def _mostra_dettagli_cliente(self, cliente_nome):
        """Mostra una finestra con i dettagli degli ORDINI del cliente (prezzi originali)."""
        dlg = tk.Toplevel(self)
        dlg.title(f"Ordini per: {cliente_nome}")
        dlg.geometry("1200x600")
        dlg.configure(bg="#f7f1e1")

        # Frame per la treeview con scrollbar
        tree_frame = tk.Frame(dlg, bg="#f7f1e1")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Treeview per gli ordini del cliente
        tv = ttk.Treeview(tree_frame,
                          columns=("ID Ordine", "Data", "Progetti", "Quantità", "Totale Ordine", "Stato"),
                          show="headings", height=15)

        # Scrollbar verticale
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)

        # Scrollbar orizzontale
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tv.xview)
        tv.configure(xscrollcommand=hsb.set)

        # 🔥 CONFIGURAZIONE COLONNE OTTIMIZZATA
        column_config = [
            ("ID Ordine", 60, "center"),  # Più stretto (max 3 cifre)
            ("Data", 100, "center"),  # Invariato
            ("Progetti", 450, "center"),  # Leggermente ridotto
            ("Quantità", 80, "center"),  # Invariato
            ("Totale Ordine", 120, "center"),  # Invariato
            ("Stato", 250, "center")  # 🔥 Più largo per il testo lungo
        ]

        for col, width, anchor in column_config:
            tv.heading(col, text=col)
            tv.column(col, width=width, anchor=anchor)

        # Posizionamento grid
        tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Carica gli ORDINI dal database
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
                  SELECT o.id,
                         o.data_inserimento,
                         o.prezzo_totale,
                         o.stato_pagamento,
                         o.consegnato,
                         GROUP_CONCAT(p.nome, ', ') AS progetti,
                         SUM(po.quantita)           AS quantita_totale
                  FROM ordini o
                           LEFT JOIN progetti_ordinati po ON o.id = po.ordine_id
                           LEFT JOIN progetti p ON po.progetto_id = p.id
                  WHERE o.cliente = ?
                  GROUP BY o.id
                  ORDER BY o.data_inserimento DESC
                  """, (cliente_nome,))

        ordini = c.fetchall()
        conn.close()

        totale_complessivo = 0.0

        for o in ordini:
            # Determina lo stato
            if o["consegnato"]:
                stato = "✅ Consegnato"
            else:
                stato = "⏳ In lavorazione"

            # Aggiungi informazioni pagamento se presenti
            if o["stato_pagamento"] and "PAGATO" in o["stato_pagamento"]:
                stato += f" - {o['stato_pagamento']}"

            tv.insert("", "end", values=(
                o["id"],
                o["data_inserimento"][:10] if o["data_inserimento"] else "",
                o["progetti"] or "-",
                o["quantita_totale"] or 0,
                f"€ {o['prezzo_totale']:.2f}" if o['prezzo_totale'] else "€ 0.00",
                stato
            ))

            if o["prezzo_totale"]:
                totale_complessivo += o["prezzo_totale"]

        # Footer con totale complessivo
        bottom_frame = tk.Frame(dlg, bg="#f7f1e1")
        bottom_frame.pack(fill="x", padx=10, pady=10)

        totale_label = tk.Label(bottom_frame,
                                text=f"Totale complessivo ordini: € {totale_complessivo:.2f}",
                                font=("Segoe UI", 12, "bold"), bg="#f7f1e1", fg="#3366cc")
        totale_label.pack(side="left", padx=10)

        tk.Button(bottom_frame, text="Chiudi", command=dlg.destroy,
                  bg="#f0f0f0", font=("Segoe UI", 10), padx=20).pack(side="right", padx=10)

    def elimina_vendita(self):
        """Elimina la vendita selezionata."""
        if self.aggregated:
            messagebox.showinfo("Info", "Per eliminare una vendita entra nella vista dettaglio.")
            return

        selezione = self.tree.selection()
        if not selezione:
            messagebox.showinfo("Info", "Seleziona una vendita da eliminare.")
            return

        item_id = self.tree.item(selezione[0])['values'][0]

        if messagebox.askyesno("Conferma eliminazione", "Eliminare la vendita selezionata?"):
            try:
                VendutiManager.elimina_vendita(item_id)
                self.carica_dati()
            except Exception as e:
                messagebox.showerror("Errore", str(e))


class DettaglioVendita(tk.Toplevel):
    """Finestra di dettaglio per una singola vendita."""

    def __init__(self, parent, vendita_id, controller):
        super().__init__(parent)
        self.controller = controller
        self.vendita_id = vendita_id

        # Carica i dati dal manager
        self.dati = VendutiManager.get_dettaglio_vendita(vendita_id)
        if not self.dati:
            messagebox.showerror("Errore", "Nessun dato trovato per questa vendita.")
            self.destroy()
            return

        self.title(f"Dettaglio Vendita - {self.dati['progetto_nome']}")
        self.configure(bg="#f7f1e1")
        self.geometry("600x680")
        self.minsize(450, 450)

        self._crea_interfaccia()

    def _crea_interfaccia(self):
        """Crea l'interfaccia della finestra di dettaglio."""
        lbl_font = ("Segoe UI", 11, "bold")
        entry_font = ("Segoe UI", 10)

        # Info principali
        info = [
            f"Progetto: {self.dati['progetto_nome']}",
            f"Cliente: {self.dati['cliente']}",
            f"Data vendita: {self.dati['data']}",
            f"Quantità: {self.dati['quantita']}",
            f"Prezzo totale: {self.dati['prezzo_totale']:.2f}€" if self.dati['prezzo_totale'] else "Prezzo totale: N/A"
        ]

        for testo in info:
            tk.Label(self, text=testo, font=lbl_font, bg="#f7f1e1").pack(pady=3)

        # Immagine
        self.img_label = tk.Label(self, bg="#f7f1e1", relief="sunken")
        self.img_label.pack(pady=5)
        self._carica_immagine()

        btn_img_frame = tk.Frame(self, bg="#f7f1e1")
        btn_img_frame.pack(pady=2)
        tk.Button(btn_img_frame, text="📁 Cambia immagine", command=self._cambia_immagine).pack(side="left", padx=4)
        tk.Button(btn_img_frame, text="❌ Rimuovi immagine", command=self._rimuovi_immagine).pack(side="left", padx=4)

        # Note
        tk.Label(self, text="Note:", font=lbl_font, bg="#f7f1e1").pack(anchor="w", padx=10, pady=(10, 0))
        self.note_text = tk.Text(self, height=10, font=entry_font)
        self.note_text.pack(fill="x", padx=10)
        if self.dati['note']:
            self.note_text.insert("1.0", self.dati['note'])

        # Posizione progetto
        tk.Label(self, text="Posizione progetto:", font=lbl_font, bg="#f7f1e1").pack(anchor="w", padx=10, pady=(10, 0))
        self.percorso_entry = tk.Entry(self, font=entry_font)
        self.percorso_entry.pack(fill="x", padx=10, pady=(0, 5))
        if self.dati['percorso_progetto']:
            self.percorso_entry.insert(0, self.dati['percorso_progetto'])

        posizione_btn_frame = tk.Frame(self, bg="#f7f1e1")
        posizione_btn_frame.pack(pady=(0, 10))
        tk.Button(posizione_btn_frame, text="🔍 Cerca posizione", command=self._cerca_posizione).pack(side="left",
                                                                                                     padx=10)
        tk.Button(posizione_btn_frame, text="📂 Vai a posizione", command=self._vai_a_posizione).pack(side="left",
                                                                                                     padx=10)

        # Pulsanti finali
        btn_frame = tk.Frame(self, bg="#f7f1e1")
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="💾 Salva modifiche", command=self._salva_modifiche).pack(side="left", padx=6)
        tk.Button(btn_frame, text="❌ Chiudi", command=self.destroy).pack(side="left", padx=6)

    def _carica_immagine(self):
        """Carica e mostra l'immagine."""
        if self.dati['immagine_percorso'] and os.path.exists(self.dati['immagine_percorso']):
            try:
                img = Image.open(self.dati['immagine_percorso'])
                img.thumbnail((80, 80), Image.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=self.photo, text="")
            except Exception as e:
                print(f"Errore caricamento immagine: {e}")
                self.img_label.config(image="", text="Nessuna immagine")
        else:
            self.img_label.config(image="", text="Nessuna immagine")

    def _cambia_immagine(self):
        """Cambia l'immagine della vendita."""
        percorso = filedialog.askopenfilename(
            parent=self,
            title="Seleziona immagine",
            filetypes=[("File immagine", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if percorso:
            self.dati['immagine_percorso'] = percorso
            self._carica_immagine()

    def _rimuovi_immagine(self):
        """Rimuove l'immagine della vendita."""
        self.dati['immagine_percorso'] = None
        self._carica_immagine()

    def _cerca_posizione(self):
        """Cerca una posizione per il progetto."""
        posizione = filedialog.askdirectory(parent=self, title="Seleziona posizione progetto")
        if posizione:
            self.percorso_entry.delete(0, tk.END)
            self.percorso_entry.insert(0, posizione)

    def _vai_a_posizione(self):
        """Apre la posizione del progetto nel file manager."""
        percorso = self.percorso_entry.get()
        if percorso and os.path.exists(percorso):
            if os.name == 'nt':
                os.startfile(percorso)
            else:
                import subprocess
                subprocess.run(['xdg-open', percorso])
        else:
            messagebox.showwarning("Attenzione", "Percorso non valido o inesistente.")

    def _salva_modifiche(self):
        """Salva le modifiche apportate."""
        note = self.note_text.get("1.0", "end").strip()
        percorso_progetto = self.percorso_entry.get().strip()

        try:
            VendutiManager.aggiorna_vendita(
                vendita_id=self.vendita_id,
                note=note,
                immagine_percorso=self.dati['immagine_percorso'],
                percorso_progetto=percorso_progetto if percorso_progetto else None
            )
            messagebox.showinfo("Successo", "Modifiche salvate con successo.")
            if hasattr(self.controller, 'carica_dati'):
                self.controller.carica_dati()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Errore", str(e))
