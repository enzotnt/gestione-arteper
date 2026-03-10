# gui/magazzino_gui.py
# Interfaccia per la gestione del magazzino - VERSIONE OTTIMIZZATA

import tkinter as tk

import os
from tkinter import ttk, messagebox
from logic import magazzino
from utils.helpers import (
    mostra_info, mostra_attenzione, mostra_errore,
    chiedi_conferma, salva_csv, carica_immagine_percorso, db_cursor
)
from utils.componenti_mancanti_util import apri_componenti_mancanti
from utils.gui_utils import crea_finestra_con_treeview, ordina_colonna_treeview, mostra_immagine_zoom, DialogComponente, \
    crea_menu_contestuale
from utils.magazzino_util import on_doppio_click


class TabMagazzino(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.stato_ordinamento = {'colonna': None, 'ascendente': True}
        self.mappa_colonne = {
            "ID": "id",
            "Nome": "nome",
            "Unità": "unita",
            "Quantità": "quantita",
            "Costo unitario (€)": "costo_unitario",
            "Ultimo acquisto": "ultimo_acquisto",
            "Fornitore": "fornitore",
            "Note": "note"
        }
        self.percorsi_immagini = {}  # Mappa item_id -> percorso immagine
        self.immagini = []  # Riferimenti per evitare garbage collection

        self.crea_interfaccia()
        self._crea_menu_contestuale()

    def _crea_menu_contestuale(self):
        """Crea il menu contestuale specifico per il magazzino."""
        voci = [
            ("✏️ Modifica componente", self.modifica_componente),
            ("📝 Modifica note", self.modifica_note),
            ("📦 Aggiungi scorte", self.aggiungi_scorte_da_menu),
            ("� Forza Quantità", self.forza_quantita_da_menu),
            ("�📜 Mostra storico", self.mostra_storico),
            ("💾 Esporta storico", self.esporta_storico_singolo_csv),
            ("🗑️ Elimina", self.elimina_componente),
        ]
        crea_menu_contestuale(self.tree, voci)

    # =========================================================================
    # CREAZIONE INTERFACCIA
    # =========================================================================

    def crea_interfaccia(self):
        """Crea tutti gli elementi dell'interfaccia."""
        self._crea_pulsanti_principali()
        self._crea_pulsanti_secondari()
        self._crea_tabella()
        self.visualizza_magazzino()

    def _crea_pulsanti_principali(self):
        """Crea la prima riga di pulsanti (azioni principali)."""
        frame = tk.Frame(self, bg="#f7f1e1")
        frame.pack(pady=(10, 5), anchor="w", fill="x")

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
            ("🧩 Componenti Mancanti", lambda: apri_componenti_mancanti(self)),
            ("➕ Nuovo componente", self.nuovo_componente),
            ("🔄 Aggiorna elenco", self.visualizza_magazzino),
            ("🎪 Aggiungi a Mercatino", self.aggiungi_a_mercatino)
        ]

        for testo, comando in pulsanti:
            btn = tk.Button(frame, text=testo, command=comando, **btn_opts)
            btn.pack(side="left", padx=6, pady=5)

            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#f0d9b5'))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=btn_opts["bg"]))

        # 🔥 AGGIUNGI L'ETICHETTA INFORMATIVA (stessa di negozio e progetti)
        info_label = tk.Label(frame,
                              text="💡 Seleziona più componenti con Ctrl+click, poi clicca 'Aggiungi a Mercatino' -- 🔥 NON SELEZIONARE I COMPONENTI A ZERO! 🔥--",
                              bg="#f7f1e1", fg="#5a3e1b", font=("Segoe UI", 9, "italic"))
        info_label.pack(side="left", padx=20)

    def _crea_pulsanti_secondari(self):
        """Crea la seconda riga di pulsanti (storico ed esportazione)."""
        frame = tk.Frame(self, bg="#f7f1e1")
        frame.pack(pady=(2, 10), anchor="w", fill="x")

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
            "pady": 3,
        }

        pulsanti = [
            ("📦 Storico Magazzino", self.visualizza_storico_magazzino),
            ("💾 Esporta storico completo", self.esporta_storico_completo_csv),
            ("🔧 Forza Quantità", self.forza_quantita_componente),
        ]

        for testo, comando in pulsanti:
            btn = tk.Button(frame, text=testo, command=comando, **btn_opts)
            btn.pack(side="left", padx=6, pady=3)

    def _crea_tabella(self):
        """Crea la Treeview per visualizzare i componenti."""
        style = ttk.Style()
        style.configure("Treeview", rowheight=36, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 11))

        colonne = ("ID", "Nome", "Unità", "Quantità", "Costo unitario (€)",
                   "Ultimo acquisto", "Fornitore", "Note")

        self.tree = ttk.Treeview(self, columns=colonne, show="tree headings")
        self.tree.heading("#0", text="🖼️")
        self.tree.column("#0", width=80, anchor="center", stretch=False)

        larghezze = {
            "ID": 50, "Nome": 200, "Unità": 60, "Quantità": 80,
            "Costo unitario (€)": 120, "Ultimo acquisto": 120,
            "Fornitore": 150, "Note": 250,
        }

        for col in colonne:
            self.tree.heading(col, text=col, command=lambda c=col: self.ordina_per_colonna(c))
            self.tree.column(col, width=larghezze[col], anchor="center", stretch=False)

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.azione_doppio_click)

    # =========================================================================
    # FUNZIONI DI VISUALIZZAZIONE E ORDINAMENTO
    # =========================================================================

    def aggiungi_a_mercatino(self):
        """Aggiunge i componenti selezionati al tab Mercatini."""
        selected = self.tree.selection()
        if not selected:
            from utils.helpers import mostra_attenzione
            mostra_attenzione("Seleziona Componenti", "Seleziona uno o più componenti dalla lista.", parent=self)
            return

        # Raccogli gli ID dei componenti selezionati
        componenti_selezionati = []
        for item_id in selected:
            item = self.tree.item(item_id)
            valori = item["values"]
            componente_id = valori[0]
            nome = valori[1]
            quantita_attuale = float(valori[3])

            componenti_selezionati.append({
                "componente_id": componente_id,
                "nome": nome,
                "quantita_attuale": quantita_attuale
            })

        self._mostra_dialog_aggiunta_mercatino(componenti_selezionati)

    def _mostra_dialog_aggiunta_mercatino(self, componenti_selezionati):
        """Dialog per confermare e modificare i componenti prima di aggiungerli al mercatino."""
        from logic.mercatini import prepara_componente_per_mercatino

        # Prepara i dati iniziali
        componenti_da_mostrare = []
        for comp in componenti_selezionati:

            componente = magazzino.get_componente_by_id(comp["componente_id"])

            componenti_da_mostrare.append({
                "componente_id": comp["componente_id"],
                "nome": f"[MAT] {comp['nome']}",
                "prezzo": round(componente["costo_unitario"], 1),
                "quantita": 1,
                "note": componente.get("note", ""),
                "max_quantita": int(comp["quantita_attuale"])
            })

        class AggiuntaMercatinoDialog(tk.Toplevel):
            def __init__(self, parent, componenti):
                super().__init__(parent)
                self.parent = parent
                self.componenti = componenti
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
                tk.Label(self, text="Conferma e modifica i componenti da aggiungere al mercatino:",
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

                # Righe componenti
                self.row_widgets = []
                for comp in self.componenti:
                    self._crea_riga_componente(scroll_frame, comp)

                # Pulsanti
                self._crea_pulsanti()

            def _crea_intestazioni(self, parent):
                """Crea le intestazioni."""
                header = tk.Frame(parent, bg="#f7f1e1")
                header.pack(fill="x", pady=(0, 5))

                headings = [
                    ("Nome Componente", 40),
                    ("Prezzo (€)", 15),
                    ("Quantità", 10),
                    ("Note", 30)
                ]

                for txt, w in headings:
                    tk.Label(header, text=txt, font=("Segoe UI", 10, "bold"),
                             bg="#f7f1e1", width=w).pack(side="left", padx=5)

            def _crea_riga_componente(self, parent, componente):
                """Crea una riga modificabile per il componente."""
                row = tk.Frame(parent, bg="#fffafa", bd=1, relief="solid")
                row.pack(fill="x", pady=2, padx=5)

                # Nome componente
                lbl_nome = tk.Label(row, text=componente["nome"][:40],
                                    anchor="w", bg="#fffafa", width=40)
                lbl_nome.pack(side="left", padx=5, fill="x", expand=True)

                # Prezzo (modificabile)
                prezzo_var = tk.DoubleVar(value=componente["prezzo"])
                ent_prezzo = tk.Entry(row, textvariable=prezzo_var, width=12, justify="center")
                ent_prezzo.pack(side="left", padx=5)

                # Quantità (modificabile con limite)
                qta_var = tk.IntVar(value=componente["quantita"])
                sb_qta = tk.Spinbox(row, from_=1, to=componente["max_quantita"],
                                    textvariable=qta_var, width=8)
                sb_qta.pack(side="left", padx=5)

                # Note (modificabili)
                note_var = tk.StringVar(value=componente["note"])
                ent_note = tk.Entry(row, textvariable=note_var, width=28)
                ent_note.pack(side="left", padx=5)

                self.row_widgets.append({
                    "componente_id": componente["componente_id"],
                    "nome": componente["nome"],
                    "prezzo_var": prezzo_var,
                    "qta_var": qta_var,
                    "note_var": note_var,
                    "max_quantita": componente["max_quantita"]
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
                    # Verifica quantità
                    if rw["qta_var"].get() > rw["max_quantita"]:

                        messagebox.showwarning("Quantità non valida",
                                               f"La quantità per {rw['nome']} supera la disponibilità.",
                                               parent=self)
                        return

                    self.result.append({
                        "componente_id": rw["componente_id"],
                        "nome": rw["nome"],
                        "prezzo": round(rw["prezzo_var"].get(), 1),
                        "quantita": rw["qta_var"].get(),
                        "note": rw["note_var"].get(),
                        "tipo": "componente"
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
        dlg = AggiuntaMercatinoDialog(self, componenti_da_mostrare)
        self.wait_window(dlg)

        if dlg.result:
            self._invia_a_mercatino(dlg.result)

    def _invia_a_mercatino(self, items):
        """Invia gli items al tab Mercatini (IDENTICO a negozio_gui.py e progetti_gui.py)."""
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

    def modifica_componente(self):
        """Modifica i dati del componente selezionato."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente da modificare.")
            return

        item = self.tree.item(selected[0])
        valori = item["values"]
        componente_id = valori[0]
        nome = valori[1]
        unita = valori[2]
        fornitore = valori[6] if len(valori) > 6 else ""
        note = valori[7] if len(valori) > 7 else ""

        immagine = magazzino.get_percorso_immagine(componente_id)

        from utils.gui_utils import DialogComponente
        dialog = DialogComponente(
            parent=self,
            titolo=f"Modifica componente - {nome}",
            modalita=DialogComponente.MODALITA_MODIFICA,
            nome_componente=nome,
            unita_componente=unita,
            fornitore_default=fornitore,
            note_default=note,
            immagine_corrente=immagine,
            quantita_default=0,
            costo_default=0
        )

        self.wait_window(dialog)

        if dialog.risultato:
            dati = dialog.risultato
            try:
                magazzino.aggiorna_componente(
                    componente_id=componente_id,
                    nome=dati['nome'],
                    unita=dati['unita'],
                    fornitore=dati['fornitore'],
                    note=dati['note'],
                    immagine_percorso=dati['immagine_percorso']
                )
                mostra_info("Successo", f"Componente '{dati['nome']}' modificato.")
                self.visualizza_magazzino()
            except Exception as e:
                mostra_errore("Errore", str(e))

    def aggiungi_scorte_da_menu(self):
        """Aggiunge scorte al componente selezionato dal menu contestuale."""
        on_doppio_click(self, self.tree, self.visualizza_magazzino)

    def forza_quantita_da_menu(self):
        """Forza la quantità del componente selezionato dal menu contestuale."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Selezionare un componente.")
            return

        item = self.tree.item(selected[0])
        valori = item["values"]
        componente_id = valori[0]
        nome_componente = valori[1]

        # Chiedi conferma e nuova quantità
        from tkinter import simpledialog
        nuova_qta_str = simpledialog.askstring(
            "🔧 Forza Quantità",
            f"Componente: {nome_componente}\n\n"
            f"⚠️ Questa operazione modifica direttamente la quantità\n"
            f"SENZA aggiornare componenti mancanti o ordini.\n\n"
            f"Inserisci la nuova quantità:",
            parent=self
        )

        if nuova_qta_str is None:
            return

        try:
            nuova_quantita = float(nuova_qta_str)
        except ValueError:
            mostra_errore("Errore", "Quantità non valida.")
            return

        # Conferma
        if not chiedi_conferma("⚠️ Conferma Forzatura Quantità",
                             f"Componente: {nome_componente}\n"
                             f"Nuova quantità: {nuova_quantita}\n\n"
                             f"Questa modifica BYPASSA la logica di gestione ordini.\n"
                             f"Continuare?", parent=self):
            return

        # Applica forzatura
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE magazzino SET quantita = ? WHERE id = ?",
                       (nuova_quantita, componente_id))

        mostra_info("✅ Forzatura Applicata",
                   f"Quantità di '{nome_componente}' impostata a {nuova_quantita}.\n\n"
                   f"⚠️ Modifica applicata SENZA sincronizzazioni.",
                   parent=self)

        self.visualizza_magazzino()

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

    def _aggiungi_riga_tabella(self, componente):
        """Aggiunge una riga alla tabella con i dati del componente."""
        id_, nome, unita, quantita, costo_unitario, ultimo_acquisto, fornitore, immagine_path, note = componente

        foto = carica_immagine_percorso(immagine_path, (32, 32))
        if foto:
            self.immagini.append(foto)

        valori = (
            id_,
            nome or "",
            unita or "",
            f"{quantita:.2f}" if quantita is not None else "0.00",
            f"{costo_unitario:.2f}" if costo_unitario is not None else "0.00",
            ultimo_acquisto or "",
            fornitore or "",
            note or ""
        )

        kwargs = {'values': valori}
        if foto:
            kwargs['image'] = foto

        item_id = self.tree.insert("", "end", **kwargs)
        self.percorsi_immagini[item_id] = immagine_path

    def ordina_per_colonna(self, colonna):
        """Ordina la tabella per la colonna selezionata."""
        self.stato_ordinamento = ordina_colonna_treeview(
            self.tree, colonna, self.stato_ordinamento
        )

    # =========================================================================
    # AZIONI SUI COMPONENTI
    # =========================================================================

    def nuovo_componente(self):
        """Aggiunge un nuovo componente al magazzino."""
        from utils.gui_utils import DialogComponente
        dialog = DialogComponente(
            parent=self,
            titolo="Nuovo componente",
            modalita=DialogComponente.MODALITA_NUOVO
        )

        self.wait_window(dialog)

        if dialog.risultato:
            dati = dialog.risultato
            try:
                magazzino.aggiungi_componente(
                    nome=dati['nome'],
                    unita=dati['unita'],
                    quantita=dati['quantita'],
                    costo_totale=dati['costo_totale'],
                    note=dati['note'] or None,
                    fornitore=dati['fornitore'] or None,
                    immagine_percorso=dati['immagine_percorso']
                )
                mostra_info("Successo", f"Componente '{dati['nome']}' aggiunto.")
                self.visualizza_magazzino()
            except Exception as e:
                mostra_errore("Errore", str(e))

    def elimina_componente(self):
        """Elimina il componente selezionato."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente da eliminare.")
            return

        item = self.tree.item(selected[0])
        componente_id = item["values"][0]
        nome = item["values"][1]

        if not chiedi_conferma("Conferma eliminazione", f"Vuoi davvero eliminare il componente '{nome}'?"):
            return

        try:
            magazzino.elimina_componente(componente_id)
            mostra_info("Eliminato", f"Componente '{nome}' eliminato con successo.")
            self.visualizza_magazzino()
        except Exception as e:
            mostra_errore("Errore", f"Errore durante l'eliminazione: {e}")

    def modifica_note(self):
        """Modifica le note del componente selezionato."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente per modificarne le note.")
            return

        item = self.tree.item(selected[0])
        componente_id = item["values"][0]
        nota_corrente = item["values"][-1]

        finestra_note = tk.Toplevel(self)
        finestra_note.title("Modifica Note")
        finestra_note.geometry("600x400")
        finestra_note.transient(self)
        finestra_note.grab_set()

        top_frame = tk.Frame(finestra_note)
        top_frame.pack(fill="x", pady=(10, 0), padx=10)

        tk.Label(top_frame, text="Modifica le note:", font=("Segoe UI", 11, "bold")).pack(side="left")

        def salva_note():
            nuova_nota = text_note.get("1.0", "end").strip()
            if nuova_nota != nota_corrente:
                try:
                    magazzino.aggiorna_note(componente_id, nuova_nota)
                    self.visualizza_magazzino()
                except Exception as e:
                    mostra_errore("Errore", f"Impossibile salvare le note: {e}")
            finestra_note.destroy()

        btn_salva = tk.Button(
            top_frame, text="💾 Salva", command=salva_note,
            font=("Segoe UI", 10, "bold"), bg="#90ee90", fg="black", padx=10, pady=5
        )
        btn_salva.pack(side="right")

        text_note = tk.Text(finestra_note, wrap="word", font=("Segoe UI", 10))
        text_note.pack(expand=True, fill="both", padx=10, pady=10)
        text_note.insert("1.0", nota_corrente)

    # =========================================================================
    # GESTIONE IMMAGINI
    # =========================================================================

    def mostra_immagine(self):
        """Mostra l'immagine del componente selezionato."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente.")
            return

        item_id = selected[0]
        immagine_percorso = self.percorsi_immagini.get(item_id)

        if not immagine_percorso or not os.path.isfile(immagine_percorso):
            mostra_info("Nessuna immagine", "Nessuna immagine trovata per questo componente.")
            return

        mostra_immagine_zoom(self, immagine_percorso, "Immagine componente")

    # =========================================================================
    # STORICO ED ESPORTAZIONE
    # =========================================================================

    def mostra_storico(self):
        """Mostra lo storico acquisti del componente selezionato."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente.")
            return

        item = self.tree.item(selected[0])
        componente_id = item["values"][0]
        nome_componente = item["values"][1]

        try:
            storico = magazzino.get_storico_acquisti(componente_id)
            if not storico:
                mostra_info("Storico vuoto", f"Nessun movimento per '{nome_componente}'.")
                return

            colonne = [
                ("data", "Data"),
                ("quantita", "Quantità"),
                ("costo_totale", "Costo Totale (€)"),
                ("fornitore", "Fornitore"),
                ("note", "Note")
            ]

            dati_formattati = [
                (data, f"{q:.2f}", f"{c:.2f}", f or "", n or "")
                for data, q, c, f, n in storico
            ]

            column_types = {"data": "date", "quantita": "numeric", "costo_totale": "numeric"}
            crea_finestra_con_treeview(
                self, f"Storico: {nome_componente}", colonne, dati_formattati, column_types
            )
        except Exception as e:
            mostra_errore("Errore", f"Impossibile caricare lo storico: {e}")

    def visualizza_storico_magazzino(self):
        """Mostra lo storico completo del magazzino."""
        try:
            with db_cursor(parent=self) as cur:
                cur.execute("""
                            SELECT data, nome, quantita, costo_totale, fornitore, note
                            FROM movimenti_magazzino
                            ORDER BY data DESC
                            """)
                dati = cur.fetchall()

            if not dati:
                mostra_info("Storico vuoto", "Nessun movimento nel magazzino.")
                return

            colonne = [
                ("data", "Data"),
                ("nome", "Nome"),
                ("quantita", "Quantità"),
                ("costo_totale", "Costo Totale (€)"),
                ("fornitore", "Fornitore"),
                ("note", "Note")
            ]
            column_types = {"data": "date", "quantita": "numeric", "costo_totale": "numeric"}
            crea_finestra_con_treeview(self, "Storico Magazzino", colonne, dati, column_types)

        except Exception as e:
            mostra_errore("Errore", f"Errore nel recupero dello storico: {e}")

    def esporta_storico_singolo_csv(self):
        """Esporta in CSV lo storico del componente selezionato."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente.")
            return

        item = self.tree.item(selected[0])
        componente_id = item["values"][0]
        nome_componente = item["values"][1]

        try:
            storico = magazzino.get_storico_acquisti(componente_id)
            if not storico:
                mostra_info("Storico vuoto", f"Nessun movimento per '{nome_componente}'.")
                return

            intestazioni = ["Data", "Quantità", "Costo Totale (€)", "Fornitore", "Note"]
            salva_csv(storico, intestazioni, titolo_finestra=f"Esporta storico di '{nome_componente}'")
        except Exception as e:
            mostra_errore("Errore", f"Errore durante l'esportazione: {e}")

    def esporta_storico_completo_csv(self):
        """Esporta in CSV l'intero storico del magazzino."""
        try:
            with db_cursor(parent=self) as cur:
                cur.execute("""
                            SELECT data, nome, quantita, costo_totale, fornitore, note
                            FROM movimenti_magazzino
                            ORDER BY data DESC
                            """)
                dati = cur.fetchall()

            if not dati:
                mostra_info("Storico vuoto", "Nessun movimento nel magazzino.")
                return

            intestazioni = ["Data", "Nome", "Quantità", "Costo Totale (€)", "Fornitore", "Note"]
            salva_csv(dati, intestazioni, titolo_finestra="Esporta storico magazzino completo")
        except Exception as e:
            mostra_errore("Errore", f"Errore durante l'esportazione: {e}")

    def forza_quantita_componente(self):
        """Permette di forzare la quantità di un componente senza incidere sulla catena di gestione."""
        try:
            # Crea finestra di dialogo più grande
            dialog = tk.Toplevel(self)
            dialog.title("🔧 Forza Quantità Componente")
            dialog.geometry("1000x700")
            dialog.configure(bg="#f7f1e1")
            dialog.transient(self)
            dialog.grab_set()

            # Centra la finestra
            dialog.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
            y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")

            # Titolo
            tk.Label(dialog, text="⚠️ FORZATURA QUANTITÀ COMPONENTE",
                    font=("Segoe Print", 14, "bold"), bg="#f7f1e1", fg="#8B0000").pack(pady=10)

            tk.Label(dialog, text="Questa operazione modifica direttamente la quantità nel database\n"
                                 "SENZA aggiornare componenti mancanti o sincronizzare ordini.\n"
                                 "Usare solo per correzioni manuali (smarrimenti, guasti, ecc.)",
                    font=("Segoe UI", 9), bg="#f7f1e1", fg="#5a3e1b", justify="center").pack(pady=5)

            # Frame principale con scrollbar per la tabella
            main_frame = tk.Frame(dialog, bg="#f7f1e1")
            main_frame.pack(fill="both", expand=True, padx=10, pady=5)

            # Treeview per i componenti
            colonne = ("ID", "Nome", "Unità", "Quantità Attuale", "Costo unitario (€)",
                      "Ultimo acquisto", "Fornitore", "Note")

            tree_frame = tk.Frame(main_frame, bg="#f7f1e1")
            tree_frame.pack(fill="both", expand=True)

            tree = ttk.Treeview(tree_frame, columns=colonne, show="headings", height=15)
            tree.pack(fill="both", expand=True, side="left")

            # Scrollbar
            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            scrollbar.pack(side="right", fill="y")
            tree.configure(yscrollcommand=scrollbar.set)

            # Configura colonne
            larghezze = {
                "ID": 50, "Nome": 200, "Unità": 60, "Quantità Attuale": 120,
                "Costo unitario (€)": 120, "Ultimo acquisto": 120,
                "Fornitore": 150, "Note": 200,
            }

            # Stato ordinamento
            sort_state = {"colonna": None, "ascendente": True}

            def ordina_colonna(col):
                """Ordina la colonna selezionata."""
                if sort_state["colonna"] == col:
                    sort_state["ascendente"] = not sort_state["ascendente"]
                else:
                    sort_state["colonna"] = col
                    sort_state["ascendente"] = True

                # Rimuovi indicatore precedente
                for c in colonne:
                    tree.heading(c, text=c)

                # Aggiungi indicatore alla colonna corrente
                indicator = " ▲" if sort_state["ascendente"] else " ▼"
                tree.heading(col, text=col + indicator)

                # Ordina i dati
                items = [(tree.item(item)["values"], item) for item in tree.get_children()]
                if col == "ID":
                    items.sort(key=lambda x: int(x[0][0]) if x[0][0] else 0,
                              reverse=not sort_state["ascendente"])
                elif col in ["Quantità Attuale", "Costo unitario (€)"]:
                    items.sort(key=lambda x: float(x[0][colonne.index(col)]) if x[0][colonne.index(col)] else 0,
                              reverse=not sort_state["ascendente"])
                else:
                    items.sort(key=lambda x: str(x[0][colonne.index(col)]).lower(),
                              reverse=not sort_state["ascendente"])

                # Ricostruisci la treeview
                for item in tree.get_children():
                    tree.delete(item)
                for values, item_id in items:
                    tree.insert("", "end", values=values, tags=(item_id,))

            for col in colonne:
                tree.heading(col, text=col, command=lambda c=col: ordina_colonna(c))
                tree.column(col, width=larghezze[col], anchor="center")

            # Carica i componenti
            componenti = magazzino.get_lista_componenti()
            for comp in componenti:
                id_, nome, unita, quantita, costo_unitario, ultimo_acquisto, fornitore, immagine_path, note = comp
                valori = (
                    id_,
                    nome or "",
                    unita or "",
                    f"{quantita:.2f}" if quantita is not None else "0.00",
                    f"{costo_unitario:.2f}" if costo_unitario is not None else "0.00",
                    ultimo_acquisto or "",
                    fornitore or "",
                    note or ""
                )
                tree.insert("", "end", values=valori)

            # Frame per i controlli di forzatura
            control_frame = tk.Frame(dialog, bg="#f7f1e1", relief="ridge", bd=2)
            control_frame.pack(fill="x", padx=10, pady=10)

            tk.Label(control_frame, text="💡 Seleziona un componente dalla tabella sopra e inserisci la nuova quantità:",
                    font=("Segoe UI", 10, "bold"), bg="#f7f1e1", fg="#5a3e1b").pack(pady=5)

            # Frame per input
            input_frame = tk.Frame(control_frame, bg="#f7f1e1")
            input_frame.pack(pady=5)

            tk.Label(input_frame, text="Componente selezionato:",
                    font=("Segoe UI", 10), bg="#f7f1e1").grid(row=0, column=0, sticky="w", padx=5, pady=2)

            self.lbl_componente_selezionato = tk.Label(input_frame, text="Nessuno",
                                                     font=("Segoe UI", 10, "bold"), bg="#f7f1e1", fg="#8B0000")
            self.lbl_componente_selezionato.grid(row=0, column=1, sticky="w", padx=5, pady=2)

            tk.Label(input_frame, text="Quantità attuale:",
                    font=("Segoe UI", 10), bg="#f7f1e1").grid(row=1, column=0, sticky="w", padx=5, pady=2)

            self.lbl_quantita_attuale = tk.Label(input_frame, text="0.00",
                                                font=("Segoe UI", 10, "bold"), bg="#f7f1e1", fg="#006400")
            self.lbl_quantita_attuale.grid(row=1, column=1, sticky="w", padx=5, pady=2)

            tk.Label(input_frame, text="Nuova quantità:",
                    font=("Segoe UI", 10, "bold"), bg="#f7f1e1").grid(row=2, column=0, sticky="w", padx=5, pady=2)

            self.entry_nuova_quantita = tk.Entry(input_frame, width=15, font=("Segoe UI", 10))
            self.entry_nuova_quantita.grid(row=2, column=1, sticky="w", padx=5, pady=2)

            # Bind selezione treeview
            def on_select(event):
                selected = tree.selection()
                if selected:
                    valori = tree.item(selected[0])["values"]
                    componente_id = valori[0]
                    nome = valori[1]
                    quantita_attuale = valori[3]

                    self.lbl_componente_selezionato.config(text=f"{nome} (ID: {componente_id})")
                    self.lbl_quantita_attuale.config(text=quantita_attuale)
                    self.entry_nuova_quantita.focus()
                    # Salva il componente selezionato per l'applicazione
                    dialog.selected_componente = (componente_id, nome)
                else:
                    self.lbl_componente_selezionato.config(text="Nessuno")
                    self.lbl_quantita_attuale.config(text="0.00")
                    dialog.selected_componente = None

            tree.bind("<<TreeviewSelect>>", on_select)

            # Pulsanti
            btn_frame = tk.Frame(control_frame, bg="#f7f1e1")
            btn_frame.pack(pady=10)

            tk.Button(btn_frame, text="Annulla", command=dialog.destroy,
                     bg="#deb887", font=("Segoe UI", 10)).pack(side="left", padx=10)

            tk.Button(btn_frame, text="✅ Applica Forzatura",
                     command=lambda: self._applica_forzatura_da_tabella(dialog),
                     bg="#FF6B6B", fg="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)

        except Exception as e:
            mostra_errore("Errore", f"Errore nell'apertura della finestra: {e}")

    def _applica_forzatura_da_tabella(self, dialog):
        """Applica la forzatura della quantità dalla tabella."""
        try:
            if not hasattr(dialog, 'selected_componente') or not dialog.selected_componente:
                mostra_attenzione("Attenzione", "Selezionare un componente dalla tabella.", parent=dialog)
                return

            componente_id, nome_componente = dialog.selected_componente

            # Ottieni nuova quantità
            quantita_str = self.entry_nuova_quantita.get().strip()
            if not quantita_str:
                mostra_attenzione("Attenzione", "Inserire una quantità.", parent=dialog)
                return

            try:
                nuova_quantita = float(quantita_str)
            except ValueError:
                mostra_errore("Errore", "Quantità non valida.", parent=dialog)
                return

            # Conferma operazione
            if not chiedi_conferma("⚠️ Conferma Forzatura Quantità",
                                 f"Componente: {nome_componente}\n"
                                 f"Nuova quantità: {nuova_quantita}\n\n"
                                 f"Questa operazione BYPASSA completamente la logica di gestione\n"
                                 f"ordini e componenti mancanti. Continuare?",
                                 parent=dialog):
                return

            # Applica forzatura - UPDATE DIRETTO senza sincronizzazioni
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE magazzino SET quantita = ? WHERE id = ?",
                           (nuova_quantita, componente_id))

            mostra_info("✅ Forzatura Applicata",
                       f"Quantità di '{nome_componente}' impostata a {nuova_quantita}.\n\n"
                       f"⚠️ Questa modifica NON ha aggiornato componenti mancanti né sincronizzato ordini.",
                       parent=dialog)

            dialog.destroy()
            self.visualizza_magazzino()  # Aggiorna la vista

        except Exception as e:
            mostra_errore("Errore", f"Errore nell'applicazione della forzatura: {e}", parent=dialog)

    def azione_doppio_click(self, event):
        """Mostra l'immagine del componente al doppio click."""
        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        immagine_percorso = self.percorsi_immagini.get(item_id)

        if not immagine_percorso or not os.path.isfile(immagine_percorso):
            messagebox.showinfo("Nessuna immagine", "Nessuna immagine trovata per questo componente.")
            return

        # Usa la funzione centralizzata da gui_utils
        from utils.gui_utils import mostra_immagine_zoom
        mostra_immagine_zoom(self, immagine_percorso, "Immagine componente")
