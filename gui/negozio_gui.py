# gui/negozio_gui.py
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox
from datetime import datetime
import os
import platform
import subprocess

from logic.negozio import NegozioManager, VenditaManager
from utils.mercatini_pdf import esporta_mercatini_pdf
from logic.progetti import Progetto

from utils.helpers import (
    mostra_info, mostra_attenzione, mostra_errore, chiedi_conferma,
    carica_immagine_percorso, db_cursor
)
from utils.gui_utils import (
    ordina_colonna_treeview,
    crea_menu_contestuale,
    crea_finestra_con_treeview,
    mostra_immagine_zoom,
    chiedi_modifica_testo
)

from logic.mercatini import aggiungi_progetti_a_mercatino


class TabNegozio(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(padx=10, pady=10, fill="both", expand=True)

        self.ordina_colonna = None
        self.ordina_asc = True
        self.stato_ordinamento = {'colonna': None, 'ascendente': True}
        self.img_refs = {}  # Riferimenti immagini

        self.mappa_colonne = {
            "ID": "negozio_id",
            "Nome progetto": "nome",
            "Data inserimento": "data_inserimento",
            "Prezzo di vendita (€)": "prezzo",
            "Disponibilità": "disponibili",
            "Venduti": "venduti"
        }


        self.crea_interfaccia()
        self._crea_menu_contestuale()

    # =========================================================================
    # CREAZIONE INTERFACCIA
    # =========================================================================

    def crea_interfaccia(self):
        """Crea tutti gli elementi dell'interfaccia."""
        self._crea_pulsanti()
        self._crea_tabella()
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

        btn_elimina_opts = btn_opts.copy()
        btn_elimina_opts.update({
            "bg": "#d9534f",
            "activebackground": "#c9302c",
            "fg": "white",
            "activeforeground": "white",
        })

        pulsanti = [
            ("💰 Vendi multipli", self.vendi_progetto, btn_opts, False),
            ("🔄 Aggiorna", self.carica_dati, btn_opts, False),
            ("➕ Aggiungi a Mercatino", self.aggiungi_a_mercatino, btn_opts, False),  # <-- MODIFICATO
        ]

        for testo, comando, opts, is_elimina in pulsanti:
            btn = tk.Button(btn_frame, text=testo, command=comando, **opts)
            btn.pack(side="left", padx=6, pady=5)

            if not is_elimina:
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#f0d9b5'))
                btn.bind("<Leave>", lambda e, b=btn, c=opts["bg"]: b.configure(bg=c))
            else:
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#c9302c'))
                btn.bind("<Leave>", lambda e, b=btn, c=opts["bg"]: b.configure(bg=c))

        info_label = tk.Label(btn_frame,
                              text="💡 Seleziona più progetti con Ctrl+click, poi clicca 'Aggiungi a Mercatino'",
                              bg="#f7f1e1", fg="#5a3e1b", font=("Segoe UI", 9, "italic"))
        info_label.pack(side="left", padx=20)

    def _crea_menu_contestuale(self):
        """Crea il menu contestuale per la tabella."""
        voci = [
            ("💰 Vendi (selezione multipla: Ctrl+click)", self.vendi_progetto),  # <-- MODIFICATO
            ("↩️ Rientra", self.rientra_progetto),
            ("📜 Storico vendite", self.mostra_storico_vendite),
            ("📝 Modifica note", self.modifica_note),
            ("🖼️ Mostra immagine", self.mostra_immagine_progetto),
            ("🗑️ Elimina", self.elimina_progetto_selezionato),
        ]
        crea_menu_contestuale(self.tree, voci)

    def _crea_tabella(self):
        """Crea la Treeview per visualizzare i progetti in negozio."""
        style = ttk.Style()
        style.configure("Treeview", rowheight=36, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 11))

        colonne = ("ID", "Nome progetto", "Data inserimento", "Prezzo di vendita (€)", "Disponibilità", "Venduti")

        self.tree = ttk.Treeview(self, columns=colonne, show="tree headings")
        self.tree.heading("#0", text="🖼️")
        self.tree.column("#0", width=80, anchor="center", stretch=False)

        colonne_larghezze = {
            "ID": 50,
            "Nome progetto": 200,
            "Data inserimento": 120,
            "Prezzo di vendita (€)": 140,
            "Disponibilità": 100,
            "Venduti": 80,
        }

        for col in colonne:
            self.tree.heading(col, text=col, command=lambda c=col: self.ordina_per_colonna(c))
            self.tree.column(col, width=colonne_larghezze[col], anchor="center", stretch=False)

        # Configura tag per colori
        self.tree.tag_configure("esaurito", foreground="gray")
        self.tree.tag_configure("disponibile", foreground="black")

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", lambda e: self.mostra_immagine_progetto())

    # =========================================================================
    # CARICAMENTO DATI E ORDINAMENTO
    # =========================================================================

    def carica_dati(self):
        """Carica i dati dal database usando NegozioManager."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Determina il campo di ordinamento
        campo_ordine = None
        if self.ordina_colonna and self.ordina_colonna in self.mappa_colonne:
            campo_ordine = self.mappa_colonne[self.ordina_colonna]

        # Ottieni dati dal manager
        progetti = NegozioManager.get_progetti_in_negozio(
            ordina_per=campo_ordine,
            ordine_asc=self.ordina_asc
        )

        for p in progetti:
            img = carica_immagine_percorso(p["immagine_percorso"], size=(32, 32))
            tag = "esaurito" if p["disponibili"] == 0 else "disponibile"

            iid = self.tree.insert(
                "", "end",
                text="",
                values=(
                    p["negozio_id"],
                    p["nome"],
                    p["data_inserimento"],
                    f"{p['prezzo']:.2f}",
                    p["disponibili"],
                    p["venduti"]
                ),
                tags=(tag,),
                **({"image": img} if img else {})
            )

            if img:
                self.img_refs[iid] = img

    def ordina_per_colonna(self, colonna):
        """Ordina la tabella per la colonna selezionata."""
        self.stato_ordinamento = ordina_colonna_treeview(
            self.tree, colonna, self.stato_ordinamento
        )
        self.ordina_colonna = colonna
        self.ordina_asc = self.stato_ordinamento['ascendente']
        self.carica_dati()

    # =========================================================================
    # UTILITY
    # =========================================================================

    def get_selezione(self):
        """Restituisce i dati della riga selezionata."""
        sel = self.tree.selection()
        if not sel:
            mostra_attenzione("Selezione mancante", "Seleziona un progetto.", parent=self)
            return None

        item = self.tree.item(sel[0])
        return {
            "negozio_id": int(item['values'][0]),
            "nome": item['values'][1],
            "disponibili": int(item['values'][4]),
            "venduti": int(item['values'][5])
        }

    def get_progetto_id_da_negozio(self, negozio_id):
        """Recupera l'ID del progetto dal negozio."""
        with db_cursor() as cur:
            cur.execute("SELECT progetto_id FROM negozio WHERE id = ?", (negozio_id,))
            row = cur.fetchone()
            return row[0] if row else None

    # =========================================================================
    # AZIONI PRINCIPALI
    # =========================================================================

    def stampa_prodotto(self):
        """Esporta in PDF l'elenco prodotti."""
        luogo_data = simpledialog.askstring(
            "Luogo e data mercatino",
            "Inserisci Luogo e Data (es: Piazza X - 14/11/2025):",
            parent=self
        )
        if luogo_data is None:
            return

        prefill_nome = "Tuo Nome"
        prefill_tessera = "12345678"
        prefill_rilasciato = "09/07/2024"
        prefill_comune = "Comune di XXXX"

        # Genera nome file suggerito
        import re
        clean = re.sub(r'[^A-Za-z0-9_\-\s/]', '', luogo_data)
        clean = clean.strip().replace(" ", "_").replace("/", "-")
        suggested_filename = f"{clean}.pdf"

        save_path = filedialog.asksaveasfilename(
            title="Salva elenco mercatino",
            defaultextension=".pdf",
            filetypes=[("PDF file", "*.pdf"), ("All files", "*.*")],
            initialfile=suggested_filename,
            parent=self
        )
        if not save_path:
            return

        try:
            out = esporta_mercatini_pdf(
                output_dir=os.path.dirname(save_path),
                filename=os.path.basename(save_path),
                luogo_data_mercatino=luogo_data,
                prefilled_nome_cognome=prefill_nome,
                prefilled_tessera=prefill_tessera,
                prefilled_rilasciato_il=prefill_rilasciato,
                prefilled_comune=prefill_comune,
                include_totals=True
            )

            mostra_info("Stampa creata", f"File PDF creato:\n{out}", parent=self)
            self._apri_pdf(out)

        except Exception as e:
            mostra_errore("Errore esportazione", f"Si è verificato un errore:\n{e}", parent=self)

    def _apri_pdf(self, percorso):
        """Apre il PDF con il visualizzatore predefinito."""
        try:
            if platform.system() == "Windows":
                os.startfile(percorso)
            elif platform.system() == "Darwin":
                subprocess.call(["open", percorso])
            else:
                subprocess.call(["xdg-open", percorso])
        except Exception:
            pass

    # =========================================================================
    # GESTIONE IMMAGINI E NOTE
    # =========================================================================

    def mostra_immagine_progetto(self):
        """Mostra l'immagine del progetto selezionato."""
        selezione = self.get_selezione()
        if not selezione:
            return

        progetto_id = self.get_progetto_id_da_negozio(selezione["negozio_id"])
        if not progetto_id:
            mostra_attenzione("Attenzione", "Impossibile trovare il progetto associato.", parent=self)
            return

        with db_cursor() as cur:
            cur.execute("SELECT immagine_percorso FROM progetti WHERE id = ?", (progetto_id,))
            row = cur.fetchone()
            if row and row[0] and os.path.exists(row[0]):
                mostra_immagine_zoom(self, row[0], f"Immagine: {selezione['nome']}")
            else:
                mostra_info("Nessuna immagine", f"Il progetto '{selezione['nome']}' non ha un'immagine associata.",
                            parent=self)

    def modifica_note(self):
        """Modifica le note del progetto selezionato."""
        selezione = self.get_selezione()
        if not selezione:
            return

        progetto_id = self.get_progetto_id_da_negozio(selezione["negozio_id"])
        if not progetto_id:
            return

        with db_cursor() as cur:
            cur.execute("SELECT note FROM progetti WHERE id = ?", (progetto_id,))
            row = cur.fetchone()
            nota_corrente = row[0] if row and row[0] else ""

        nuova_nota = chiedi_modifica_testo(
            self,
            f"Modifica note - {selezione['nome']}",
            "Note del progetto:",
            nota_corrente
        )

        if nuova_nota is not None:
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE progetti SET note = ? WHERE id = ?", (nuova_nota, progetto_id))
            mostra_info("Note aggiornate", "Le note sono state modificate con successo.", parent=self)

    def mostra_storico_vendite(self):
        """Mostra lo storico delle vendite del progetto selezionato."""
        selezione = self.get_selezione()
        if not selezione:
            return

        with db_cursor() as cur:
            cur.execute("""
                        SELECT data_vendita, cliente, quantita, prezzo_totale
                        FROM venduti
                        WHERE negozio_id = ?
                        ORDER BY data_vendita DESC
                        """, (selezione["negozio_id"],))
            dati = cur.fetchall()

        if not dati:
            mostra_info("Nessuna vendita", f"Il progetto '{selezione['nome']}' non ha vendite registrate.", parent=self)
            return

        colonne = [
            ("data_vendita", "Data"),
            ("cliente", "Cliente"),
            ("quantita", "Quantità"),
            ("prezzo_totale", "Totale (€)")
        ]

        column_types = {"data_vendita": "date", "prezzo_totale": "numeric"}

        crea_finestra_con_treeview(
            self,
            f"Storico vendite - {selezione['nome']}",
            colonne,
            dati,
            column_types
        )

    # =========================================================================
    # VENDITA PROGETTI
    # =========================================================================

    def vendi_progetto(self):
        """Vendita multipla con controllo omonimia cliente."""
        sel = self.tree.selection()
        if not sel:
            mostra_attenzione("Selezione mancante", "Seleziona uno o più progetti da vendere.", parent=self)
            return

        cliente = simpledialog.askstring("Nome cliente", "Inserisci nome del cliente:", parent=self)
        if not cliente:
            return

        # Gestione omonimia cliente
        cliente = self._gestisci_omonimia_cliente(cliente)
        if cliente is None:
            return

        # Raccogli dati degli items selezionati
        items = self._raccogli_dati_items(sel)
        if not items:
            return

        # Dialog di vendita
        risultato = self._mostra_dialog_vendita(items, cliente)
        if not risultato:
            return

        # Processa la vendita
        self._processa_vendita(risultato, cliente)

    def _gestisci_omonimia_cliente(self, cliente):
        """Gestisce il caso di cliente già esistente."""
        if not NegozioManager.cliente_esiste(cliente):
            return cliente

        scelta = messagebox.askyesnocancel(
            "Cliente esistente",
            f"Il cliente '{cliente}' è già presente nelle vendite.\n\n"
            "Scegli:\n"
            "- Sì: aggiungi i nuovi oggetti a questo cliente\n"
            "- No: crea un nuovo cliente (ti verrà chiesto il nuovo nome)\n"
            "- Annulla: interrompi l'operazione",
            parent=self
        )

        if scelta is None:  # Annulla
            return None
        elif scelta is False:  # No -> nuovo nome
            while True:
                nuovo = simpledialog.askstring("Nuovo nome cliente",
                                               "Inserisci il nome da usare per creare un nuovo cliente:",
                                               parent=self)
                if nuovo is None:
                    return None
                nuovo = nuovo.strip()
                if not nuovo:
                    mostra_attenzione("Nome non valido", "Inserisci un nome non vuoto.", parent=self)
                    continue
                if NegozioManager.cliente_esiste(nuovo):
                    if not messagebox.askyesno("Nome già esistente",
                                               f"Il nome '{nuovo}' esiste già. Vuoi provare un altro nome?",
                                               parent=self):
                        continue
                return nuovo

        return cliente  # Sì -> usa lo stesso

    def _raccogli_dati_items(self, selezione):
        """Raccoglie i dati completi per gli items selezionati."""
        items = []
        for iid in selezione:
            item = self.tree.item(iid)
            negozio_id = int(item['values'][0])
            nome_visibile = item['values'][1]
            disponibili = int(item['values'][4])

            # Recupera dati completi dal manager
            dati_negozio = NegozioManager.get_progetto_da_negozio(negozio_id)
            if not dati_negozio:
                mostra_errore("Errore", f"Progetto non trovato per '{nome_visibile}'", parent=self)
                return None

            # Calcola prezzo dinamico
            progetto_obj = Progetto(carica_da_id=dati_negozio["progetto_id"])
            prezzo_vendita = progetto_obj.calcola_prezzo()

            items.append({
                "negozio_id": negozio_id,
                "progetto_id": dati_negozio["progetto_id"],
                "nome_visibile": nome_visibile,
                "disponibili": disponibili,
                "prezzo_vendita": prezzo_vendita
            })

        return items

    def _mostra_dialog_vendita(self, items, cliente):
        """Mostra il dialog per la vendita multipla."""

        class SellDialog(tk.Toplevel):
            def __init__(self, parent, items, titolo="Vendita multipla"):
                super().__init__(parent)
                self.parent = parent
                self.items = [dict(it) for it in items]
                self.cliente = cliente
                self.result = None
                self.buono_applicato = None
                self.title(titolo)
                self.configure(bg="#f7f1e1")
                self.geometry("920x600")  # Solo aumentato leggermente l'altezza
                self.transient(parent)
                self.grab_set()

                self._crea_interfaccia(cliente)
                self._centra_finestra()

            def _crea_interfaccia(self, cliente):
                """Crea l'interfaccia del dialog."""
                # Intestazione cliente
                tk.Label(self, text=f"Cliente: {cliente}", bg="#f7f1e1",
                         font=("Segoe UI", 10, "bold")).pack(pady=(8, 2))

                # 🔥 Frame per il codice sconto
                frame_sconto = tk.Frame(self, bg="#f7f1e1")
                frame_sconto.pack(fill="x", padx=10, pady=(0, 5))

                tk.Label(frame_sconto, text="Codice sconto:", bg="#f7f1e1",
                         font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))

                self.codice_sconto_var = tk.StringVar()
                self.entry_codice = tk.Entry(frame_sconto, textvariable=self.codice_sconto_var,
                                             width=15)
                self.entry_codice.pack(side="left", padx=5)

                # Pulsante per applicare il codice
                btn_verifica = tk.Button(frame_sconto, text="Applica",
                                         command=self._verifica_codice_sconto,
                                         bg="#e0e0e0")
                btn_verifica.pack(side="left", padx=5)

                # 🔥 Label per mostrare lo stato del codice sconto (AGGIUNTA)
                self.label_sconto = tk.Label(frame_sconto, text="", bg="#f7f1e1",
                                             font=("Segoe UI", 9, "italic"))
                self.label_sconto.pack(side="left", padx=10)

                # Area scrollabile
                container = tk.Frame(self, bg="#f7f1e1")
                container.pack(fill="both", expand=True, padx=10, pady=6)

                canvas = tk.Canvas(container, bg="#f7f1e1", highlightthickness=0)
                scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
                scroll_frame = tk.Frame(canvas, bg="#f7f1e1")
                scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                # Intestazioni colonne
                self._crea_intestazioni(scroll_frame)

                # Righe prodotti
                self.row_widgets = []
                for it in self.items:
                    self._crea_riga_prodotto(scroll_frame, it)

                # Pulsanti in basso
                self._crea_pulsanti_dialog()

            def _verifica_codice_sconto(self):
                """Verifica il codice sconto inserito e applica lo sconto se valido."""
                codice = self.codice_sconto_var.get().strip()

                if not codice:
                    return

                from logic.buoni import BuonoManager

                # Verifica se il buono è valido
                valido, msg, buono = BuonoManager.valida_buono(codice)

                if not valido:
                    messagebox.showerror("Codice non valido", msg, parent=self)
                    self.label_sconto.config(text=msg, fg="red")
                    self.codice_sconto_var.set("")  # Pulisci il campo
                    if hasattr(self, 'buono_applicato'):
                        delattr(self, 'buono_applicato')
                    self._aggiorna_totali()
                    return

                # Salva i dati del buono per usarli dopo
                self.buono_applicato = {
                    'id': buono['id'],
                    'codice': buono['codice'],
                    'tipo': buono['tipo'],
                    'valore_originale': buono['valore_originale'],
                    'valore_residuo': buono['valore_residuo']
                }

                # Mostra messaggio di conferma
                if buono['tipo'] == 'REGALO':
                    msg = f"✓ Buono regalo valido (€{buono['valore_residuo']:.2f} residui)"
                else:
                    msg = f"✓ Buono sconto del {buono['valore_originale']:.0f}% valido"

                self.label_sconto.config(text=msg, fg="green")

                # Aggiorna i totali con lo sconto
                self._aggiorna_totali()

            def _crea_intestazioni(self, parent):
                """Crea la riga di intestazione."""
                header = tk.Frame(parent, bg="#f7f1e1")
                header.pack(fill="x", pady=(0, 2))

                headings = [
                    ("Nome oggetto", 48),
                    ("Disponibili", 10),
                    ("Quantità", 10),
                    ("Prezzo totale (€)", 16),
                    ("Subtotale (€)", 12)
                ]

                for txt, w in headings:
                    tk.Label(header, text=txt, font=("Segoe UI", 10, "bold"),
                             bg="#f7f1e1").pack(side="left", padx=6)

            def _crea_riga_prodotto(self, parent, item):
                """Crea una riga per un prodotto."""
                row = tk.Frame(parent, bg="#fffafa", bd=1, relief="solid")
                row.pack(fill="x", pady=4, padx=2)

                # Nome
                lbl_nome = tk.Label(row, text=item["nome_visibile"],
                                    anchor="w", bg="#fffafa", width=48)
                lbl_nome.pack(side="left", fill="x", expand=True, padx=(6, 4))

                # Disponibili
                lbl_disp = tk.Label(row, text=str(item["disponibili"]),
                                    width=10, bg="#fffafa")
                lbl_disp.pack(side="left", padx=6)

                # Quantità
                q_var = tk.IntVar(value=1 if item["disponibili"] > 0 else 0)
                sb = tk.Spinbox(row, from_=1, to=max(1, item["disponibili"]),
                                textvariable=q_var, width=6)
                sb.pack(side="left", padx=6)

                # Prezzo totale (editabile)
                p_var = tk.DoubleVar(value=item["prezzo_vendita"])
                ent_price = tk.Entry(row, textvariable=p_var, width=14, justify="center")
                ent_price.pack(side="left", padx=6)

                # Subtotale
                sub_lbl = tk.Label(row, text=f"{p_var.get():.2f}€",
                                   width=12, bg="#fffafa")
                sub_lbl.pack(side="left", padx=6)

                # Tracciamento modifiche utente
                user_edited = {"flag": False}
                ent_price.bind("<KeyRelease>", lambda e, ue=user_edited: ue.update({"flag": True}))

                # Callback per aggiornamento
                def on_qty_change(*a, qv=q_var, pv=p_var, up=item["prezzo_vendita"],
                                  ue=user_edited, sl=sub_lbl, it=item):
                    try:
                        q = int(qv.get() or 0)
                    except Exception:
                        q = 0

                    if q < 0 or q > it["disponibili"]:
                        sl.config(text="Q>disp!", fg="red")
                    else:
                        if not ue["flag"]:
                            new_tot = round(up * q, 2)
                            pv.set(new_tot)
                            sl.config(text=f"{new_tot:.2f}€", fg="black")
                        else:
                            try:
                                cur = float(pv.get() or 0.0)
                                sl.config(text=f"{cur:.2f}€", fg="black")
                            except Exception:
                                sl.config(text="0.00€", fg="black")

                def on_price_change(*a, pv=p_var, sl=sub_lbl):
                    try:
                        val = float(pv.get() or 0.0)
                        sl.config(text=f"{val:.2f}€", fg="black")
                    except Exception:
                        sl.config(text="0.00€", fg="black")

                q_var.trace_add("write", on_qty_change)
                p_var.trace_add("write", on_price_change)

                self.row_widgets.append({
                    "negozio_id": item["negozio_id"],
                    "nome_visibile": item["nome_visibile"],
                    "disponibili": item["disponibili"],
                    "q_var": q_var,
                    "p_var": p_var,
                    "sub_lbl": sub_lbl,
                    "unit_price": item["prezzo_vendita"],
                    "user_edited": user_edited
                })

            def _crea_pulsanti_dialog(self):
                """Crea i pulsanti in fondo al dialog con visualizzazione sconto."""
                bottom = tk.Frame(self, bg="#f7f1e1")
                bottom.pack(fill="x", padx=10, pady=8)

                # Frame per i totali
                frame_totali = tk.Frame(bottom, bg="#f7f1e1")
                frame_totali.pack(side="left", fill="x", expand=True)

                # Totale lordo
                tk.Label(frame_totali, text="Totale lordo: €", bg="#f7f1e1",
                         font=("Segoe UI", 9)).pack(side="left", padx=5)
                self.totale_lordo_var = tk.DoubleVar(value=self._calcola_totale())
                tk.Label(frame_totali, textvariable=self.totale_lordo_var,
                         bg="#f7f1e1", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)

                # Sconto
                tk.Label(frame_totali, text="Sconto: €", bg="#f7f1e1",
                         font=("Segoe UI", 9)).pack(side="left", padx=(20, 5))
                self.sconto_var = tk.DoubleVar(value=0.0)
                tk.Label(frame_totali, textvariable=self.sconto_var,
                         bg="#f7f1e1", font=("Segoe UI", 9, "bold"), fg="red").pack(side="left", padx=5)

                # Totale netto (modificabile)
                tk.Label(frame_totali, text="Totale netto: €", bg="#f7f1e1",
                         font=("Segoe UI", 10, "bold")).pack(side="left", padx=(20, 5))
                self.totale_var = tk.DoubleVar(value=self._calcola_totale())
                tk.Entry(frame_totali, textvariable=self.totale_var, width=12,
                         justify="center", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

                # Pulsanti
                frame_btn = tk.Frame(bottom, bg="#f7f1e1")
                frame_btn.pack(side="right")

                tk.Button(frame_btn, text="Conferma", command=self.on_confirm,
                          bg="#90EE90", font=("Segoe UI", 10, "bold")).pack(side="left", padx=6)
                tk.Button(frame_btn, text="Annulla", command=self.on_cancel,
                          bg="#f0f0f0").pack(side="left", padx=6)

                # Aggiorna totali quando cambiano i valori
                for rw in self.row_widgets:
                    rw["p_var"].trace_add("write", lambda *a: self._aggiorna_totali())
                    rw["q_var"].trace_add("write", lambda *a: self._aggiorna_totali())

                self.bind("<Return>", lambda e: self.on_confirm())
                self.bind("<Escape>", lambda e: self.on_cancel())

            def _aggiorna_totali(self):
                """Aggiorna i totali quando cambiano quantità o prezzi."""
                totale_lordo = self._calcola_totale()
                self.totale_lordo_var.set(totale_lordo)

                # Se c'è un buono applicato, ricalcola lo sconto
                if hasattr(self, 'buono_applicato') and self.buono_applicato:
                    if self.buono_applicato['tipo'] == 'REGALO':
                        sconto = min(self.buono_applicato['valore_residuo'], totale_lordo)
                    else:  # SCONTO
                        percentuale = self.buono_applicato['valore_originale']
                        sconto = totale_lordo * (percentuale / 100)

                    self.sconto_var.set(round(sconto, 2))
                    self.totale_var.set(round(totale_lordo - sconto, 2))
                else:
                    self.sconto_var.set(0.0)
                    self.totale_var.set(totale_lordo)

            def _calcola_totale(self):
                """Calcola il totale corrente."""
                tot = 0.0
                for rw in self.row_widgets:
                    try:
                        q = int(rw["q_var"].get() or 0)
                        if q > rw["disponibili"]:
                            continue
                        tot += float(rw["p_var"].get() or 0.0)
                    except Exception:
                        pass
                return round(tot, 2)

            def _centra_finestra(self):
                """Centra la finestra rispetto al parent."""
                self.update_idletasks()
                try:
                    x = self.parent.winfo_rootx() + 30
                    y = self.parent.winfo_rooty() + 30
                    self.geometry(f"+{x}+{y}")
                except Exception:
                    pass

            def on_confirm(self):
                """Conferma la vendita."""
                risultati = []
                for rw in self.row_widgets:
                    try:
                        q = int(rw["q_var"].get() or 0)
                    except Exception:
                        q = 0
                    try:
                        p_tot = float(rw["p_var"].get() or 0.0)
                    except Exception:
                        p_tot = 0.0

                    if q <= 0 or q > rw["disponibili"]:
                        messagebox.showwarning("Quantità non valida",
                                               f"Quantità non valida per {rw['nome_visibile']}",
                                               parent=self)
                        return

                    risultati.append({
                        "negozio_id": rw["negozio_id"],
                        "nome_visibile": rw["nome_visibile"],
                        "quantita": q,
                        "prezzo_totale": round(p_tot, 2),
                        "prezzo_unitario": round((p_tot / q) if q else 0.0, 4)
                    })

                self.result = {
                    "cliente": self.cliente,  # Assicurati che self.cliente sia definito
                    "codice_sconto": self.codice_sconto_var.get().strip(),
                    "buono_applicato": getattr(self, 'buono_applicato', None),
                    "righe": risultati,
                    "totale_lordo": float(self.totale_lordo_var.get() or 0.0),
                    "sconto": float(self.sconto_var.get() or 0.0),  # <-- IMPORTANTE
                    "totale_finale": float(self.totale_var.get() or 0.0)
                }
                self.grab_release()
                self.destroy()

            def on_cancel(self):
                """Annulla la vendita."""
                self.result = None
                self.grab_release()
                self.destroy()

        dlg = SellDialog(self, items, titolo=f"Vendita multipla - Cliente: {cliente}")
        self.wait_window(dlg)
        return getattr(dlg, "result", None)

    def _processa_vendita(self, risultato, cliente):
        """Processa i risultati del dialog di vendita."""
        vendite = risultato["righe"]
        totale_finale = risultato["totale_finale"]
        codice_sconto = risultato.get("codice_sconto", None)
        buono_applicato = risultato.get("buono_applicato", None)
        sconto_applicato = risultato.get("sconto", 0.0)

        # Calcolo proporzionale per aggiustare i prezzi
        totale_vendita = sum(v["prezzo_totale"] for v in vendite)
        proporzione = (totale_finale / totale_vendita) if totale_vendita else 1.0

        for v in vendite:
            v["prezzo_totale"] = round(v["prezzo_totale"] * proporzione, 2)
            v["prezzo_unitario"] = round(v["prezzo_unitario"] * proporzione, 4)

        # Genera nota riepilogativa
        nota_ordine = self._genera_note_ordine(vendite, cliente)

        if codice_sconto:
            nota_ordine = f"Codice sconto: {codice_sconto}\n{nota_ordine}"

        # Variabili per gestire il buono dopo la transazione principale
        buono_da_applicare = buono_applicato
        sconto_da_applicare = sconto_applicato
        vendita_ids_per_buono = []

        # Salva su DB usando i manager
        with db_cursor(commit=True, parent=self) as cur:
            vendita_ids = []

            for vendita in vendite:
                negozio_id = vendita["negozio_id"]
                qta = vendita["quantita"]
                prezzo_unit = vendita["prezzo_unitario"]
                prezzo_tot = vendita["prezzo_totale"]

                # Recupera progetto_id
                cur.execute("SELECT progetto_id FROM negozio WHERE id=?", (negozio_id,))
                r = cur.fetchone()
                if not r:
                    continue
                progetto_id = r[0]

                # Registra vendita usando il manager
                vendita_id = VenditaManager.registra_vendita(
                    negozio_id, progetto_id, cliente, qta,
                    prezzo_tot, prezzo_unit, nota_ordine, codice_sconto
                )

                if vendita_id:
                    vendita_ids.append(vendita_id)

                # Aggiorna quantità nel negozio
                NegozioManager.aggiorna_quantita_negozio(negozio_id, qta)

            # Salva gli ID vendite per applicare il buono dopo
            vendita_ids_per_buono = vendita_ids

        # 🔥 APPLICA IL BUONO DOPO LA TRANSAZIONE PRINCIPALE
        if buono_da_applicare and vendita_ids_per_buono and sconto_da_applicare > 0:
            from logic.buoni import BuonoManager

            success, msg = BuonoManager.applica_utilizzo(
                buono_id=buono_da_applicare['id'],
                importo_utilizzato=sconto_da_applicare,
                vendita_id=vendita_ids_per_buono[0]  # Associa alla prima vendita
            )

            if not success:
                print(f"Errore nell'aggiornamento del buono: {msg}")

        mostra_info("Vendita completata", f"Vendita a '{cliente}' registrata con successo.", parent=self)
        self.carica_dati()

    def _genera_note_ordine(self, vendite, cliente):
        """Genera note riepilogative per l'ordine."""
        righe = [f"Cliente: {cliente}", "Riepilogo ordine:"]
        totale = 0

        for v in vendite:
            righe.append(
                f"- {v['nome_visibile']} → {v['quantita']} x {v['prezzo_unitario']:.2f}€ = {v['prezzo_totale']:.2f}€"
            )
            totale += v['prezzo_totale']

        righe.append(f"Totale ordine: {totale:.2f}€")
        return "\n".join(righe)

    # =========================================================================
    # RIENTRO PROGETTI
    # =========================================================================

    def rientra_progetto(self):
        """Gestisce il rientro di un progetto dal negozio."""
        selezione = self.tree.selection()
        if not selezione:
            mostra_attenzione("Selezione mancante", "Seleziona un progetto da rientrare.", parent=self)
            return

        item = self.tree.item(selezione[0])
        negozio_id = item['values'][0]
        nome_progetto = item['values'][1]

        with db_cursor(commit=True, parent=self) as cur:
            # Recupera dati completi del progetto dal negozio
            cur.execute("""
                        SELECT p.*, n.id as negozio_id, n.progetto_id, n.disponibili, n.venduti
                        FROM negozio n
                                 JOIN progetti p ON n.progetto_id = p.id
                        WHERE n.id = ?
                        """, (negozio_id,))
            row = cur.fetchone()

            if not row:
                mostra_errore("Errore", "Progetto non trovato nel negozio.", parent=self)
                return

            # Estrai dati dalla tupla (adatta gli indici alla tua struttura)
            # Indici basati sulla query SELECT p.*, n.*...
            progetto_orig_id = row[0]  # p.id
            nome_originale = row[1]  # p.nome
            data_creazione_orig = row[2]  # p.data_creazione
            moltiplicatore = row[3]  # p.moltiplicatore
            stato_vendita = row[4]  # p.stato_vendita
            immagine_percorso = row[5]  # p.immagine_percorso
            note = row[6]  # p.note
            percorso = row[7]  # p.percorso
            negozio_id_db = row[8]  # n.id
            progetto_id_negozio = row[9]  # n.progetto_id
            disponibili = row[10]  # n.disponibili
            venduti = row[11]  # n.venduti

            if disponibili == 0:
                mostra_attenzione("Nessuna disponibilità",
                                  f"Il progetto '{nome_progetto}' non ha copie disponibili per il rientro.",
                                  parent=self)
                return

            # Chiedi quante copie rientrare
            qta = simpledialog.askinteger(
                "Quante copie rientrare?",
                f"Inserisci quante copie vuoi rientrare (max {disponibili}):",
                minvalue=1,
                maxvalue=disponibili,
                parent=self
            )
            if qta is None:
                return

            # Determina il nome base per i progetti rientrati
            base = nome_originale.split("_R")[0]
            cur.execute("SELECT COUNT(*) FROM progetti WHERE nome LIKE ?", (f"{base}_R%",))
            numero_base = cur.fetchone()[0]

            data_creazione = datetime.now().strftime("%Y-%m-%d")

            # Crea i nuovi progetti rientrati
            for i in range(qta):
                numero = numero_base + i + 1
                nuovo_nome = f"{base}_R{numero}"

                # Inserisci nuovo progetto
                cur.execute("""
                            INSERT INTO progetti (nome, data_creazione, moltiplicatore, stato_vendita,
                                                  immagine_percorso, note, percorso)
                            VALUES (?, ?, ?, 'RIENTRATO', ?, ?, ?)
                            """, (nuovo_nome, data_creazione, moltiplicatore, immagine_percorso, note, percorso))
                nuovo_progetto_id = cur.lastrowid

                # Copia i componenti dal progetto originale
                cur.execute("""
                            SELECT componente_id, quantita, moltiplicatore
                            FROM componenti_progetto
                            WHERE progetto_id = ?
                            """, (progetto_orig_id,))
                componenti = cur.fetchall()

                for comp in componenti:
                    cur.execute("""
                                INSERT INTO componenti_progetto (progetto_id, componente_id, quantita, moltiplicatore)
                                VALUES (?, ?, ?, ?)
                                """, (nuovo_progetto_id, comp[0], comp[1], comp[2]))

            # Aggiorna le quantità nel negozio
            nuovi_disponibili = disponibili - qta
            nuovi_venduti = venduti + qta

            if nuovi_disponibili == 0:
                cur.execute("DELETE FROM negozio WHERE id = ?", (negozio_id,))
            else:
                cur.execute("""
                            UPDATE negozio
                            SET disponibili = ?,
                                venduti     = ?
                            WHERE id = ?
                            """, (nuovi_disponibili, nuovi_venduti, negozio_id))

        mostra_info("Rientro completato",
                    f"{qta} copie del progetto '{nome_progetto}' sono state rientrate correttamente.",
                    parent=self)
        self.carica_dati()

    # =========================================================================
    # ELIMINAZIONE
    # =========================================================================

    def elimina_progetto_selezionato(self):
        """Elimina il progetto selezionato dal negozio."""
        selezione = self.get_selezione()
        if not selezione:
            return

        if not chiedi_conferma(
                "Conferma eliminazione",
                f"Sei sicuro di voler eliminare il progetto '{selezione['nome']}' dal negozio?",
                parent=self
        ):
            return

        try:
            if NegozioManager.elimina_da_negozio(selezione["negozio_id"]):
                self.tree.delete(self.tree.selection()[0])
                mostra_info("Eliminato", "Progetto eliminato con successo.", parent=self)
            else:
                mostra_errore("Errore", "Impossibile eliminare il progetto.", parent=self)
        except Exception as e:
            mostra_errore("Errore", f"Errore durante l'eliminazione:\n{str(e)}", parent=self)

    def aggiungi_a_mercatino(self):
        """Aggiunge i progetti selezionati al tab Mercatini."""
        sel = self.tree.selection()
        if not sel:
            mostra_attenzione("Selezione mancante",
                              "Seleziona uno o più progetti da aggiungere al mercatino.",
                              parent=self)
            return

        # Raccogli gli ID dei progetti selezionati
        progetti_selezionati = []
        for iid in sel:
            item = self.tree.item(iid)
            negozio_id = int(item['values'][0])

            with db_cursor() as cur:
                cur.execute("SELECT progetto_id FROM negozio WHERE id = ?", (negozio_id,))
                row = cur.fetchone()
                if row:
                    progetti_selezionati.append({
                        "negozio_id": negozio_id,
                        "progetto_id": row[0],
                        "nome": item['values'][1]
                    })

        if not progetti_selezionati:
            return

        self._mostra_dialog_aggiunta_mercatino(progetti_selezionati)

    def _mostra_dialog_aggiunta_mercatino(self, progetti_selezionati):
        """Dialog per confermare e modificare i progetti prima di aggiungerli al mercatino."""
        from logic.mercatini import aggiungi_progetti_a_mercatino  # <-- Funzione specifica per negozio

        progetti_dettagliati = aggiungi_progetti_a_mercatino(progetti_selezionati)

        if not progetti_dettagliati:
            mostra_errore("Errore", "Impossibile recuperare i dettagli dei progetti.", parent=self)
            return

        class AggiuntaMercatinoDialog(tk.Toplevel):
            def __init__(self, parent, progetti):
                super().__init__(parent)
                self.parent = parent
                self.progetti = progetti
                self.result = None
                self.title("Aggiungi a Mercatino")
                self.configure(bg="#f7f1e1")
                self.geometry("800x500")
                self.transient(parent)
                self.grab_set()

                self._crea_interfaccia()
                self._centra_finestra()

            def _crea_interfaccia(self):
                """Crea l'interfaccia del dialog."""
                # Istruzioni
                tk.Label(self, text="Conferma e modifica i progetti da aggiungere al mercatino:",
                         bg="#f7f1e1", font=("Segoe UI", 11, "bold")).pack(pady=(10, 5))

                # Area scrollabile
                container = tk.Frame(self, bg="#f7f1e1")
                container.pack(fill="both", expand=True, padx=10, pady=5)

                canvas = tk.Canvas(container, bg="#f7f1e1", highlightthickness=0)
                scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
                scroll_frame = tk.Frame(canvas, bg="#f7f1e1")
                scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                # Intestazioni
                self._crea_intestazioni(scroll_frame)

                # Righe progetti
                self.row_widgets = []
                for prog in self.progetti:
                    self._crea_riga_progetto(scroll_frame, prog)

                # Pulsanti
                self._crea_pulsanti()

            def _crea_intestazioni(self, parent):
                """Crea le intestazioni."""
                header = tk.Frame(parent, bg="#f7f1e1")
                header.pack(fill="x", pady=(0, 5))

                headings = [
                    ("Nome Progetto", 40),
                    ("Prezzo (€)", 15),
                    ("Quantità", 10),
                    ("Note", 30)
                ]

                for txt, w in headings:
                    tk.Label(header, text=txt, font=("Segoe UI", 10, "bold"),
                             bg="#f7f1e1", width=w).pack(side="left", padx=5)

            def _crea_riga_progetto(self, parent, progetto):
                """Crea una riga modificabile per il progetto."""
                row = tk.Frame(parent, bg="#fffafa", bd=1, relief="solid")
                row.pack(fill="x", pady=2, padx=5)

                # Nome progetto (non modificabile)
                lbl_nome = tk.Label(row, text=progetto["nome"][:40],
                                    anchor="w", bg="#fffafa", width=40)
                lbl_nome.pack(side="left", padx=5, fill="x", expand=True)

                # Prezzo (modificabile, 1 decimale)
                prezzo_var = tk.DoubleVar(value=progetto["prezzo"])
                ent_prezzo = tk.Entry(row, textvariable=prezzo_var, width=12, justify="center")
                ent_prezzo.pack(side="left", padx=5)

                # Quantità (modificabile)
                qta_var = tk.IntVar(value=progetto["quantita"])
                sb_qta = tk.Spinbox(row, from_=1, to=999, textvariable=qta_var, width=8)
                sb_qta.pack(side="left", padx=5)

                # Note (modificabili)
                note_var = tk.StringVar(value=progetto["note"])
                ent_note = tk.Entry(row, textvariable=note_var, width=28)
                ent_note.pack(side="left", padx=5)

                self.row_widgets.append({
                    "progetto_id": progetto["progetto_id"],
                    "nome": progetto["nome"],
                    "prezzo_var": prezzo_var,
                    "qta_var": qta_var,
                    "note_var": note_var
                })

            def _crea_pulsanti(self):
                """Crea i pulsanti."""
                bottom = tk.Frame(self, bg="#f7f1e1")
                bottom.pack(fill="x", padx=10, pady=10)

                tk.Button(bottom, text="Conferma", command=self.on_confirm,
                          bg="#90EE90", font=("Segoe UI", 11, "bold"), padx=20).pack(side="right", padx=5)
                tk.Button(bottom, text="Annulla", command=self.on_cancel,
                          bg="#f0f0f0", font=("Segoe UI", 11), padx=20).pack(side="right", padx=5)

            def on_confirm(self):
                """Conferma e raccoglie i dati."""
                self.result = []
                for rw in self.row_widgets:
                    self.result.append({
                        "progetto_id": rw["progetto_id"],
                        "nome": rw["nome"],
                        "prezzo": round(rw["prezzo_var"].get(), 1),  # Arrotondato a 1 decimale
                        "quantita": rw["qta_var"].get(),
                        "note": rw["note_var"].get()
                    })
                self.destroy()

            def on_cancel(self):
                self.result = None
                self.destroy()

            def _centra_finestra(self):
                self.update_idletasks()
                x = self.parent.winfo_rootx() + 50
                y = self.parent.winfo_rooty() + 50
                self.geometry(f"+{x}+{y}")

        # Mostra il dialog
        dlg = AggiuntaMercatinoDialog(self, progetti_dettagliati)
        self.wait_window(dlg)

        if dlg.result:
            # Passa i risultati al tab Mercatini
            self._invia_a_mercatino(dlg.result)

    def _invia_a_mercatino(self, progetti):
        """Invia i progetti confermati al tab Mercatini."""
        from gui.mercatini_gui import TabMercatini

        # Cerchiamo il notebook risalendo la gerarchia
        parent = self.master
        while parent is not None:
            if isinstance(parent, ttk.Notebook):
                notebook = parent
                break
            parent = parent.master
        else:
            mostra_errore("Errore", "Tab Mercatini non trovato!", parent=self)
            return

        # Cerca il tab mercatini tra i figli del notebook
        for tab_id in notebook.tabs():
            widget = notebook.nametowidget(tab_id)
            if isinstance(widget, TabMercatini):
                widget.aggiungi_progetti(progetti)

                return

        # Se non trova il tab, mostra errore
        mostra_errore("Errore", "Tab Mercatini non trovato!", parent=self)