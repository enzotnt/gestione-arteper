# gui/progetti_gui.py
# Interfaccia per la gestione dei progetti - VERSIONE OTTIMIZZATA

import tkinter as tk
from tkinter import ttk, simpledialog, Toplevel, Text, filedialog, messagebox
from datetime import datetime
import os
import subprocess
import platform

from PIL import Image, ImageTk

from utils.gui_utils import crea_menu_contestuale

from logic.progetti import Progetto
from utils.seleziona_componenti import SelezionaComponentiDialog_logic
from utils.helpers import (
    # Funzioni già esistenti
    mostra_errore, mostra_info, mostra_attenzione, chiedi_conferma,
    carica_immagine_percorso, crea_finestra_zoom_immagine,
    treeview_sort_column,

    # Nuove funzioni da aggiungere a helpers.py
    db_cursor, format_currency, conferma_e_esegui
)


# =============================================================================
# CLASSE PRINCIPALE: TabProgetti
# =============================================================================

class TabProgetti(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f7f1e1")

        self.progetti = []
        self.img_cache = {}
        self.ordina_per = "id"
        self.ordine_crescente = True
        self.column_types = {
            "id": "numeric",
            "prezzo": "numeric",
            "costo": "numeric",
            "ricavo": "numeric",
            "data": "date"
        }

        self._crea_pulsanti()
        self._crea_tabella()
        self._crea_menu_contestuale()
        self.carica_progetti()

    def _crea_pulsanti(self):
        """Crea i pulsanti con configurazione centralizzata."""
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

        pulsanti = [
            ("➕ Aggiungi Progetto", self.aggiungi_progetto, "#deb887"),
            ("🔄 Aggiorna", self.carica_progetti, "#deb887"),
            ("🎪 Aggiungi a Mercatino", self.aggiungi_a_mercatino, "#deb887"),  # <-- NUOVO
        ]

        frm_top = tk.Frame(self, bg="#f7f1e1")
        frm_top.pack(fill='x', pady=(10, 5))

        for testo, comando, bg in pulsanti:
            btn = tk.Button(frm_top, text=testo, command=comando, **btn_opts)
            btn.configure(bg=bg, activebackground=self._lighten_color(bg))
            btn.pack(side='left', padx=6, pady=5)

            if bg != "#d9534f":
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#f0d9b5'))
                btn.bind("<Leave>", lambda e, b=btn, c=bg: b.configure(bg=c))

        # 🔥 AGGIUNGI L'ETICHETTA INFORMATIVA
        info_label = tk.Label(frm_top,
                              text="💡 Seleziona più progetti con Ctrl+click, poi clicca 'Aggiungi a Mercatino'",
                              bg="#f7f1e1", fg="#5a3e1b", font=("Segoe UI", 9, "italic"))
        info_label.pack(side="left", padx=20)

    def _lighten_color(self, color):
        """Schiarisce un colore (versione semplice)."""
        return '#f0d9b5'

    def _crea_tabella(self):
        """Crea la Treeview per i progetti."""
        columns = ("id", "data", "nome", "stato", "prezzo", "costo", "ricavo", "note")

        style = ttk.Style()
        style.configure("Treeview", rowheight=36, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 11))

        self.tree = ttk.Treeview(self, columns=columns, show='tree headings', selectmode='extended')
        self.tree.column("#0", width=40, anchor='center')
        self.tree.heading("#0", text="🖼️")

        colonne_config = {
            "id": {"text": "ID", "width": 50, "anchor": 'center'},
            "data": {"text": "Data Creazione", "width": 130, "anchor": 'center'},
            "nome": {"text": "Nome Progetto", "width": 250, "anchor": 'center'},
            "stato": {"text": "Venduto", "width": 60, "anchor": 'center'},
            "prezzo": {"text": "Prezzo (€)", "width": 80, "anchor": 'center'},
            "costo": {"text": "Costo (€)", "width": 80, "anchor": 'center'},
            "ricavo": {"text": "Ricavo (€)", "width": 80, "anchor": 'center'},
            "note": {"text": "Note", "width": 200, "anchor": 'center'},
        }

        for col, conf in colonne_config.items():
            self.tree.heading(col, text=conf["text"], command=lambda c=col: self.ordina(c))
            self.tree.column(col, width=conf["width"], anchor=conf["anchor"])

        self.tree.pack(fill='both', expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.modifica_progetto)

    def visualizza_magazzino(self):
        """Aggiorna la tabella con i dati del magazzino."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        self.immagini.clear()
        self.percorsi_immagini.clear()

        try:
            componenti = magazzino.get_lista_componenti()
            for comp in componenti:
                self._aggiungi_riga_tabella(comp)
        except Exception as e:
            mostra_errore("Errore", f"Impossibile caricare i componenti: {e}")

    def _crea_menu_contestuale(self):
        """Crea il menu contestuale specifico per i progetti."""
        voci = [
            ("✏️ Modifica progetto", lambda: self.modifica_progetto(None)),
            ("📝 Modifica note", self.aggiorna_note),
            ("📄 Duplica progetto", self.duplica_progetto),
            ("📜 Mostra storico", self.mostra_storico),
            ("📂 Vai a posizione", self.apri_cartella_progetto),
            ("🛍️ Al negozio", self.vendi_progetto),
            ("🗑️ Elimina progetto", self.elimina_progetto),
        ]
        crea_menu_contestuale(self.tree, voci)

    # =========================================================================
    # METODI DI UTILITY
    # =========================================================================

    def aggiungi_a_mercatino(self):
        """Aggiunge i progetti selezionati al tab Mercatini."""
        selected = self.tree.selection()
        if not selected:
            from utils.helpers import mostra_attenzione
            mostra_attenzione("Seleziona Progetti", "Seleziona uno o più progetti dalla lista.", parent=self)
            return

        # Raccogli gli ID dei progetti selezionati
        progetti_selezionati = []
        for item_id in selected:
            item = self.tree.item(item_id)
            progetto_id = item['values'][0]
            nome = item['values'][2]

            progetti_selezionati.append({
                "progetto_id": progetto_id,
                "nome": nome
            })

        self._mostra_dialog_aggiunta_mercatino(progetti_selezionati)

    def _mostra_dialog_aggiunta_mercatino(self, progetti_selezionati):
        """Dialog per confermare e modificare i progetti prima di aggiungerli al mercatino."""
        from logic.mercatini import prepara_progetto_da_progetti

        # Prepara i dati iniziali
        progetti_da_mostrare = []
        for prog in progetti_selezionati:
            # Calcola prezzo base
            from logic.progetti import Progetto
            p = Progetto(carica_da_id=prog["progetto_id"])
            prezzo = round(p.calcola_prezzo(), 1)

            progetti_da_mostrare.append({
                "progetto_id": prog["progetto_id"],
                "nome": prog["nome"],
                "prezzo": prezzo,
                "quantita": 1,
                "note": p.note if p.note else ""
            })

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

                # Nome progetto
                lbl_nome = tk.Label(row, text=progetto["nome"][:40],
                                    anchor="w", bg="#fffafa", width=40)
                lbl_nome.pack(side="left", padx=5, fill="x", expand=True)

                # Prezzo (modificabile)
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
                        "prezzo": round(rw["prezzo_var"].get(), 1),
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
        dlg = AggiuntaMercatinoDialog(self, progetti_da_mostrare)
        self.wait_window(dlg)

        if dlg.result:
            self._invia_a_mercatino(dlg.result)

    def _invia_a_mercatino(self, items):
        """Invia gli items al tab Mercatini (IDENTICO a negozio_gui.py)."""
        from gui.mercatini_gui import TabMercatini

        # Cerchiamo il notebook risalendo la gerarchia
        parent = self.master
        while parent is not None:
            if isinstance(parent, ttk.Notebook):
                notebook = parent
                break
            parent = parent.master
        else:
            from utils.helpers import mostra_errore
            mostra_errore("Errore", "Tab Mercatini non trovato!", parent=self)
            return

        # Cerca il tab mercatini tra i figli del notebook
        for tab_id in notebook.tabs():
            widget = notebook.nametowidget(tab_id)
            if isinstance(widget, TabMercatini):
                widget.aggiungi_progetti(items)
                return

        from utils.helpers import mostra_errore
        mostra_errore("Errore", "Tab Mercatini non trovato!", parent=self)

    def get_componenti(self, progetto_id):
        """Recupera i componenti di un progetto per calcoli."""
        with db_cursor(parent=self) as cur:
            cur.execute("""
                        SELECT cp.quantita, m.costo_unitario
                        FROM componenti_progetto cp
                                 JOIN magazzino m ON cp.componente_id = m.id
                        WHERE cp.progetto_id = ?
                        """, (progetto_id,))
            return cur.fetchall()

    def get_progetto_selezionato(self):
        """Restituisce l'oggetto Progetto selezionato o None."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Seleziona Progetto", "Seleziona un progetto dalla lista.")
            return None

        item = self.tree.item(selected[0])
        progetto_id = item['values'][0]

        for p in self.progetti:
            if p.id == progetto_id:
                return p
        return None

    def ordina(self, col):
        """Ordina la tabella per colonna usando la funzione di helpers."""
        treeview_sort_column(self.tree, col, not self.ordine_crescente, self.column_types)
        self.ordine_crescente = not self.ordine_crescente
        self.ordina_per = col

    # =========================================================================
    # CARICAMENTO DATI
    # =========================================================================

    def carica_progetti(self):
        """Carica i progetti dal database usando il context manager."""
        self.tree.delete(*self.tree.get_children())
        self.progetti.clear()
        self.img_cache.clear()

        with db_cursor(parent=self) as cur:
            cur.execute("""
                        SELECT id,
                               data_creazione,
                               nome,
                               stato_vendita,
                               moltiplicatore,
                               note,
                               immagine_percorso,
                               percorso
                        FROM progetti
                        """)

            for row in cur.fetchall():
                p = Progetto(
                    id=row[0],
                    data_creazione=row[1],
                    nome=row[2],
                    stato=row[3],
                    moltiplicatore=row[4],
                    note=row[5],
                    immagine_percorso=row[6],
                    percorso=row[7]
                )
                self.progetti.append(p)
                self._aggiungi_riga_tabella(p)

    def _aggiungi_riga_tabella(self, p):
        """Aggiunge una riga alla tabella per un progetto."""
        prezzo = p.calcola_prezzo()
        componenti = self.get_componenti(p.id)
        costo = sum(q * cu for q, cu in componenti)
        ricavo = prezzo - costo if prezzo else 0

        # Carica immagine usando l'helper
        photo = carica_immagine_percorso(p.immagine_percorso, size=(32, 32))
        if photo:
            self.img_cache[p.id] = photo

        valori = (
            str(p.id),
            str(p.data_creazione or ""),
            str(p.nome or ""),
            str(p.stato or ""),
            f"{prezzo:.2f}",
            f"{costo:.2f}",
            f"{ricavo:.2f}",
            str(p.note or "")
        )

        kwargs = {'text': '', 'values': valori}
        if photo:
            kwargs['image'] = photo

        self.tree.insert('', 'end', **kwargs)

    # =========================================================================
    # AZIONI SUI PROGETTI
    # =========================================================================

    def aggiungi_progetto(self):
        """Apre il dialogo per aggiungere un nuovo progetto."""
        nome = simpledialog.askstring("Nuovo Progetto", "Inserisci nome progetto:")
        if not nome or not isinstance(nome, str):
            return

        def callback_componenti(componenti_selezionati, immagine=None, percorso=None):
            if not componenti_selezionati:
                return

            try:
                componenti = [
                    (comp["componente_id"], comp["quantita"], comp["moltiplicatore"])
                    for comp in componenti_selezionati
                ]
                p = Progetto.crea_progetto(nome, componenti, immagine=immagine, percorso=percorso)
                if p:
                    self.carica_progetti()
                    mostra_info("Successo", f"Progetto '{nome}' creato con successo.")
            except Exception as e:
                mostra_errore("Errore", f"Errore nella creazione del progetto:\n{e}")

        SelezionaComponentiDialog_logic(self, callback=callback_componenti)

    def elimina_progetto(self):
        """Elimina il progetto selezionato con conferma."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        def esegui_eliminazione():
            p.elimina()
            self.carica_progetti()

        conferma_e_esegui(
            "Elimina Progetto",
            f"Sei sicuro di eliminare il progetto '{p.nome}'?\nI componenti non restituiti andranno persi!",
            esegui_eliminazione
        )

    def duplica_progetto(self):
        """Duplica il progetto selezionato."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        nuovo_nome = simpledialog.askstring(
            "Duplica Progetto",
            "Inserisci nome per progetto duplicato:",
            initialvalue=p.nome + "001"
        )
        if not nuovo_nome or not isinstance(nuovo_nome, str):
            return

        try:
            p2 = p.duplica(nuovo_nome)
            if p2:
                self.carica_progetti()
                mostra_info("Duplicazione riuscita", f"Progetto duplicato come '{nuovo_nome}'.")
        except Exception as e:
            mostra_errore("Errore Duplicazione", str(e))

    def mostra_storico(self):
        """Mostra lo storico del progetto selezionato."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        try:
            storico = p.get_storico()

            if not storico:
                from utils.helpers import mostra_info
                mostra_info("Storico vuoto", f"Nessun movimento per il progetto '{p.nome}'.")
                return

            # Formatta i dati per la visualizzazione
            dati_formattati = []
            for data, azione, dettagli in storico:
                # Formatta la data se vuoi (opzionale)
                # from datetime import datetime
                # data_formattata = datetime.strptime(data, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                dati_formattati.append((
                    data,  # o data_formattata
                    azione,
                    dettagli or ""
                ))

            colonne = [
                ("data", "Data"),
                ("azione", "Azione"),
                ("dettagli", "Dettagli"),
            ]

            column_types = {"data": "date"}

            from utils.gui_utils import crea_finestra_con_treeview
            crea_finestra_con_treeview(
                self,
                f"Storico: {p.nome}",
                colonne,
                dati_formattati,
                column_types
            )

        except Exception as e:
            from utils.helpers import mostra_errore
            mostra_errore("Errore", f"Impossibile caricare lo storico: {e}")

    def mostra_immagine(self):
        """Mostra l'immagine del progetto selezionato."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        if not p.immagine_percorso or not os.path.isfile(p.immagine_percorso):
            from utils.helpers import mostra_info
            mostra_info("Nessuna immagine", f"Il progetto '{p.nome}' non ha un'immagine associata.")
            return

        # Usa la funzione da gui_utils
        from utils.gui_utils import mostra_immagine_zoom
        mostra_immagine_zoom(self, p.immagine_percorso, f"Immagine: {p.nome}")

    def aggiorna_note(self):
        """Aggiorna le note del progetto selezionato."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        def salva_note():
            testo = txt.get("1.0", "end").strip()
            try:
                p.aggiorna_note(testo)
                self.carica_progetti()
                top.destroy()
            except Exception as e:
                mostra_errore("Errore", f"Errore nel salvataggio note: {e}")

        top = Toplevel(self)
        top.title(f"Note Progetto: {p.nome}")
        top.geometry("600x400")
        top.transient(self)

        txt = Text(top, width=50, height=15, font=("Segoe UI", 10))
        txt.pack(padx=10, pady=10, fill='both', expand=True)
        txt.insert("1.0", p.note or "")

        ttk.Button(top, text="Salva Note", command=salva_note).pack(pady=5)

    def modifica_progetto(self, event):
        """Apre il dialogo per modificare il progetto."""
        p = self.get_progetto_selezionato()
        if not p:
            return
        ModificaProgettoDialog(self, p, self.carica_progetti)

    def apri_cartella_progetto(self):
        """Apre il file manager nella cartella del progetto."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        if not p.percorso or not os.path.isdir(p.percorso):
            mostra_attenzione(
                "Percorso non valido",
                "Il percorso del progetto non è stato definito o non esiste."
            )
            return

        try:
            if platform.system() == "Windows":
                os.startfile(p.percorso)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", p.percorso])
            else:  # Linux/Unix
                subprocess.Popen(["xdg-open", p.percorso])
        except Exception as e:
            mostra_errore("Errore", f"Impossibile aprire la cartella:\n{e}")

    def vendi_progetto(self):
        """Mette in vendita il progetto selezionato."""
        p = self.get_progetto_selezionato()
        if not p:
            return

        copie = simpledialog.askinteger("Vendi progetto", "Numero di copie da mettere in vendita:", minvalue=1)
        if copie is None:
            return

        try:
            with db_cursor(commit=True, parent=self) as cur:
                # Ottieni i componenti del progetto
                cur.execute(
                    "SELECT componente_id, quantita, moltiplicatore FROM componenti_progetto WHERE progetto_id = ?",
                    (p.id,)
                )
                componenti = cur.fetchall()

                # Verifica disponibilità
                componenti_insufficienti = []
                for comp_id, quantita, moltiplicatore in componenti:
                    totale_richiesto = quantita * copie
                    cur.execute("SELECT quantita, nome FROM magazzino WHERE id = ?", (comp_id,))
                    result = cur.fetchone()
                    if not result or result[0] < totale_richiesto:
                        nome = result[1] if result else "Sconosciuto"
                        componenti_insufficienti.append((comp_id, nome))

                if componenti_insufficienti:
                    messaggio = "Componenti insufficienti:\n" + "\n".join(
                        f"ID {cid} - {nome}" for cid, nome in componenti_insufficienti
                    )
                    mostra_errore("Errore", messaggio)
                    return

                # Scala componenti
                for comp_id, quantita, moltiplicatore in componenti:
                    totale_richiesto = quantita * copie
                    cur.execute("UPDATE magazzino SET quantita = quantita - ? WHERE id = ?",
                                (totale_richiesto, comp_id))

                # Calcola prezzo
                prezzo_unitario = p.calcola_prezzo()

                # Verifica se esiste già in negozio
                cur.execute("SELECT id, disponibili FROM negozio WHERE nome_progetto_negozio = ?", (p.nome,))
                esistente = cur.fetchone()

                data_inserimento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if esistente:
                    negozio_id, disponibili_attuali = esistente
                    nuove_disponibili = disponibili_attuali + copie
                    cur.execute("""
                                UPDATE negozio
                                SET disponibili      = ?,
                                    prezzo_vendita   = ?,
                                    data_inserimento = ?
                                WHERE id = ?
                                """, (nuove_disponibili, prezzo_unitario, data_inserimento, negozio_id))
                else:
                    cur.execute("""
                                INSERT INTO negozio (progetto_id, nome_progetto_negozio, data_inserimento,
                                                     prezzo_vendita, disponibili, venduti)
                                VALUES (?, ?, ?, ?, ?, 0)
                                """, (p.id, p.nome, data_inserimento, prezzo_unitario, copie))

                # Aggiorna stato progetto
                cur.execute("UPDATE progetti SET stato_vendita = 'IN VENDITA' WHERE id = ?", (p.id,))

                mostra_info("Successo", f"{copie} copie del progetto sono ora in vendita a €{prezzo_unitario:.2f} cad.")
                self.carica_progetti()

        except Exception as e:
            mostra_errore("Errore", f"Errore durante la vendita: {e}")


# =============================================================================
# DIALOGO MODIFICA PROGETTO
# =============================================================================

class ModificaProgettoDialog(tk.Toplevel):
    def __init__(self, parent, progetto, on_close_callback):
        super().__init__(parent)
        self.title(f"Modifica Progetto: {progetto.nome}")
        self.progetto = progetto
        self.on_close_callback = on_close_callback
        self.geometry("950x700")
        self.transient(parent)

        self.percorso_immagine = getattr(progetto, 'immagine_percorso', None)
        self.percorso_destinazione = getattr(progetto, 'percorso', '')
        self.immagine_tk = None

        self.crea_interfaccia()
        self.carica_componenti_progetto()
        self.carica_componenti_magazzino()

        self.after(100, self._set_grab)

    def _set_grab(self):
        """Imposta il grab in modo sicuro."""
        try:
            self.grab_set()
        except tk.TclError:
            self.after(100, self._set_grab)

    def crea_interfaccia(self):
        """Crea l'interfaccia del dialogo."""
        # --- Campi nome e moltiplicatore ---
        frame_top = ttk.Frame(self)
        frame_top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.grid_columnconfigure(0, weight=1)

        ttk.Label(frame_top, text="Nome Progetto:").grid(row=0, column=0, sticky="w")
        self.nome_var = tk.StringVar(value=self.progetto.nome)
        ttk.Entry(frame_top, textvariable=self.nome_var, width=40).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(frame_top, text="Moltiplicatore:").grid(row=1, column=0, sticky="w")
        self.moltiplicatore_var = tk.DoubleVar(value=getattr(self.progetto, "moltiplicatore", 3.0))
        ttk.Entry(frame_top, textvariable=self.moltiplicatore_var, width=10).grid(row=1, column=1, sticky="w", padx=5)

        # Pulsanti per immagine e percorso
        ttk.Button(frame_top, text="Cambia/Aggiungi Immagine", command=self.scegli_immagine).grid(
            row=0, column=2, rowspan=2, padx=10)
        ttk.Button(frame_top, text="Aggiungi/Modifica Percorso", command=self.scegli_percorso).grid(
            row=2, column=2, columnspan=2, padx=10, pady=5, sticky="w")

        # Anteprima immagine
        self.label_immagine = ttk.Label(frame_top)
        self.label_immagine.grid(row=0, column=3, rowspan=2, padx=10)
        self.aggiorna_anteprima_immagine()

        # --- Frame centrale per liste affiancate ---
        frame_centrale = ttk.Frame(self)
        frame_centrale.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Sinistra: componenti progetto
        frame_progetto = ttk.Frame(frame_centrale)
        frame_progetto.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        frame_centrale.grid_columnconfigure(0, weight=1)
        frame_centrale.grid_rowconfigure(0, weight=1)

        ttk.Label(frame_progetto, text="Componenti nel progetto").pack(anchor='w')
        cols_comp = ("nome", "quantita", "costo_unitario", "moltiplicatore", "totale")
        self.tree_comp = ttk.Treeview(frame_progetto, columns=cols_comp, show='headings', height=20)
        self.tree_comp.pack(fill='both', expand=True)

        for col in cols_comp:
            self.tree_comp.heading(col, text=col.capitalize())

        self.tree_comp.column("nome", width=180)
        self.tree_comp.column("quantita", width=80, anchor='center')
        self.tree_comp.column("costo_unitario", width=100, anchor='e')
        self.tree_comp.column("moltiplicatore", width=100, anchor='center')
        self.tree_comp.column("totale", width=100, anchor='e')
        self.tree_comp.bind("<Double-1>", self.modifica_moltiplicatore)

        # Destra: componenti magazzino
        frame_magazzino = ttk.Frame(frame_centrale)
        frame_magazzino.grid(row=0, column=1, sticky="nsew")
        frame_centrale.grid_columnconfigure(1, weight=1)

        ttk.Label(frame_magazzino, text="Componenti disponibili in magazzino").pack(anchor='w')
        cols_mag = ("nome", "quantita", "costo_unitario")
        self.tree_magazzino = ttk.Treeview(frame_magazzino, columns=cols_mag, show='headings', height=20)
        self.tree_magazzino.pack(fill='both', expand=True)

        for col in cols_mag:
            self.tree_magazzino.heading(col, text=col.capitalize())

        self.tree_magazzino.column("nome", width=180)
        self.tree_magazzino.column("quantita", width=80, anchor='center')
        self.tree_magazzino.column("costo_unitario", width=100, anchor='e')

        # --- Pulsanti in basso ---
        frame_bottom = ttk.Frame(self)
        frame_bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        frm_btn = ttk.Frame(frame_bottom)
        frm_btn.pack()

        ttk.Button(frm_btn, text="Aggiungi Componente", command=self.aggiungi_componente).pack(side='left', padx=5)
        ttk.Button(frm_btn, text="Rimuovi Componente", command=self.rimuovi_componente).pack(side='left', padx=5)
        ttk.Button(frm_btn, text="Salva modifiche", command=self.salva_modifiche).pack(side='left', padx=5)

    # =========================================================================
    # METODI PER IMMAGINI E PERCORSO
    # =========================================================================

    def aggiorna_anteprima_immagine(self):
        """Aggiorna l'anteprima dell'immagine."""
        if self.percorso_immagine and os.path.exists(self.percorso_immagine):
            try:
                img = Image.open(self.percorso_immagine)
                img.thumbnail((120, 120))
                self.immagine_tk = ImageTk.PhotoImage(img)
                self.label_immagine.config(image=self.immagine_tk)
            except Exception:
                self.label_immagine.config(text="Errore immagine")
        else:
            self.label_immagine.config(image='', text="Nessuna immagine")

    def scegli_immagine(self):
        """Apre il dialogo per selezionare un'immagine."""
        filetypes = [("Immagini", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Tutti i file", "*.*")]
        filename = filedialog.askopenfilename(title="Seleziona immagine", filetypes=filetypes, parent=self)
        if filename:
            self.percorso_immagine = filename
            self.aggiorna_anteprima_immagine()

    def scegli_percorso(self):
        """Apre il dialogo per selezionare un percorso."""
        percorso = filedialog.askdirectory(title="Seleziona cartella di destinazione", parent=self)
        if percorso:
            self.percorso_destinazione = percorso

    # =========================================================================
    # CARICAMENTO DATI
    # =========================================================================

    def carica_componenti_progetto(self):
        """Carica i componenti del progetto nella Treeview."""
        self.tree_comp.delete(*self.tree_comp.get_children())

        with db_cursor(parent=self) as cur:
            cur.execute("""
                        SELECT m.nome, cp.quantita, m.costo_unitario, cp.moltiplicatore
                        FROM componenti_progetto cp
                                 JOIN magazzino m ON cp.componente_id = m.id
                        WHERE cp.progetto_id = ?
                        """, (self.progetto.id,))

            for nome, quantita, costo_unitario, moltiplicatore in cur.fetchall():
                totale = quantita * costo_unitario * moltiplicatore
                self.tree_comp.insert('', 'end', values=(
                    nome,
                    f"{quantita:.2f}",
                    f"{costo_unitario:.2f}",
                    f"{moltiplicatore:.2f}",
                    f"{totale:.2f}"
                ))

    def carica_componenti_magazzino(self):
        """Carica i componenti del magazzino nella Treeview."""
        self.tree_magazzino.delete(*self.tree_magazzino.get_children())

        with db_cursor(parent=self) as cur:
            cur.execute("SELECT nome, quantita, costo_unitario FROM magazzino ORDER BY nome")
            for nome, quantita, costo_unitario in cur.fetchall():
                self.tree_magazzino.insert('', 'end', values=(
                    nome,
                    f"{quantita:.2f}",
                    f"{costo_unitario:.2f}"
                ))

    # =========================================================================
    # AZIONI SUI COMPONENTI
    # =========================================================================

    def modifica_moltiplicatore(self, event):
        """Modifica il moltiplicatore di un componente."""
        item = self.tree_comp.identify_row(event.y)
        if not item:
            return

        current = self.tree_comp.item(item, "values")
        nome = current[0]

        nuovo_m = simpledialog.askfloat(
            "Moltiplicatore",
            f"Inserisci nuovo moltiplicatore per '{nome}':",
            minvalue=0.1, parent=self
        )
        if nuovo_m is None:
            return

        with db_cursor(commit=True, parent=self) as cur:
            cur.execute("""
                        UPDATE componenti_progetto
                        SET moltiplicatore = ?
                        WHERE progetto_id = ?
                          AND componente_id = (SELECT id FROM magazzino WHERE nome = ?)
                        """, (nuovo_m, self.progetto.id, nome))

        self.carica_componenti_progetto()

    def aggiungi_componente(self):
        """Aggiunge un componente dal magazzino al progetto."""
        selected = self.tree_magazzino.selection()
        if not selected:
            mostra_attenzione("Seleziona Componente", "Seleziona un componente disponibile in magazzino.", parent=self)
            return

        item = self.tree_magazzino.item(selected[0])
        nome = item['values'][0]

        with db_cursor(parent=self) as cur:
            cur.execute("SELECT id FROM magazzino WHERE nome = ?", (nome,))
            row = cur.fetchone()
            if not row:
                mostra_errore("Errore", f"Componente '{nome}' non trovato.", parent=self)
                return
            componente_id = row[0]

        quantita = simpledialog.askfloat("Quantità", f"Inserisci quantità per '{nome}':", minvalue=0.01, parent=self)
        if quantita is None:
            return

        moltiplicatore = simpledialog.askfloat(
            "Moltiplicatore",
            f"Inserisci moltiplicatore per '{nome}':",
            minvalue=0.1, parent=self
        )
        if moltiplicatore is None:
            moltiplicatore = 3.0

        try:
            self.progetto.aggiungi_componente_da_id(componente_id, quantita, moltiplicatore)
            self.carica_componenti_progetto()
            self.carica_componenti_magazzino()
        except Exception as e:
            mostra_errore("Errore aggiunta componente", str(e), parent=self)

    def rimuovi_componente(self):
        selected = self.tree_comp.selection()
        if not selected:
            messagebox.showwarning("Seleziona Componente", "Seleziona un componente da rimuovere.", parent=self)
            return
        item = self.tree_comp.item(selected[0])
        nome = item['values'][0]
        conferma = messagebox.askyesno("Rimuovi Componente", f"Rimuovere il componente '{nome}' dal progetto?", parent=self)
        if not conferma:
            return
        try:
            self.progetto.rimuovi_componente(nome)
            self.carica_componenti_progetto()
            self.carica_componenti_magazzino()
        except Exception as e:
            messagebox.showerror("Errore", str(e), parent=self)

    # =========================================================================
    # SALVATAGGIO
    # =========================================================================

    def salva_modifiche(self):
        """Salva tutte le modifiche al progetto."""
        nome = self.nome_var.get().strip()
        if not nome:
            mostra_attenzione("Nome vuoto", "Il nome del progetto non può essere vuoto.", parent=self)
            return

        moltiplicatore = self.moltiplicatore_var.get()
        if moltiplicatore <= 0:
            mostra_attenzione("Moltiplicatore non valido", "Il moltiplicatore deve essere maggiore di zero.",
                              parent=self)
            return

        # Aggiorna i dati del progetto
        self.progetto.nome = nome
        self.progetto.moltiplicatore = moltiplicatore
        self.progetto.immagine_percorso = self.percorso_immagine
        self.progetto.percorso = self.percorso_destinazione

        try:
            self.progetto.salva_su_db()
            if self.on_close_callback:
                self.on_close_callback()
            self.destroy()
        except Exception as e:
            mostra_errore("Errore salvataggio", f"Errore salvando progetto: {e}", parent=self)