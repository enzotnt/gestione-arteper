# gui/buoni_gui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import pyperclip  # per copiare il codice negli appunti (opzionale)

from logic.buoni import BuonoManager
from utils.helpers import (
    mostra_info, mostra_attenzione, mostra_errore, chiedi_conferma,
    db_cursor
)
from utils.gui_utils import (
    ordina_colonna_treeview,
    crea_menu_contestuale,
    crea_finestra_con_treeview
)


class TabBuoni(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(padx=10, pady=10, fill="both", expand=True)

        self.ordina_colonna = None
        self.ordina_asc = True
        self.stato_ordinamento = {'colonna': None, 'ascendente': True}

        self.mappa_colonne = {
            "ID": "id",
            "Codice": "codice",
            "Tipo": "tipo",
            "Valore": "valore_originale",
            "Residuo": "valore_residuo",
            "Stato": "stato",
            "Scadenza": "data_scadenza",
            "Cliente": "cliente_acquirente"
        }

        self.crea_interfaccia()
        self._crea_menu_contestuale()
        self.carica_dati()

    def crea_interfaccia(self):
        """Crea tutti gli elementi dell'interfaccia."""
        self._crea_pulsanti()
        self._crea_tabella()
        self._crea_filtri()

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

        pulsanti = [
            ("➕ Nuovo Buono", self.nuovo_buono, btn_opts),
            ("🔄 Aggiorna", self.carica_dati, btn_opts),
        ]

        for testo, comando, opts in pulsanti:
            btn = tk.Button(btn_frame, text=testo, command=comando, **opts)
            btn.pack(side="left", padx=6, pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#f0d9b5'))
            btn.bind("<Leave>", lambda e, b=btn, c=opts["bg"]: b.configure(bg=c))

    def _crea_filtri(self):
        """Crea i filtri per la tabella."""
        filter_frame = tk.Frame(self, bg="#f7f1e1")
        filter_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(filter_frame, text="Filtra per stato:", bg="#f7f1e1",
                 font=("Segoe UI", 9)).pack(side="left", padx=5)

        self.filtro_stato = ttk.Combobox(filter_frame,
                                         values=["TUTTI", "ATTIVO", "UTILIZZATO", "SCADUTO", "ANNULLATO"],
                                         width=15)
        self.filtro_stato.set("TUTTI")
        self.filtro_stato.pack(side="left", padx=5)
        self.filtro_stato.bind("<<ComboboxSelected>>", lambda e: self.carica_dati())

        tk.Label(filter_frame, text="Tipo:", bg="#f7f1e1",
                 font=("Segoe UI", 9)).pack(side="left", padx=(20, 5))

        self.filtro_tipo = ttk.Combobox(filter_frame,
                                        values=["TUTTI", "REGALO", "SCONTO"],
                                        width=10)
        self.filtro_tipo.set("TUTTI")
        self.filtro_tipo.pack(side="left", padx=5)
        self.filtro_tipo.bind("<<ComboboxSelected>>", lambda e: self.carica_dati())

    def _crea_tabella(self):
        """Crea la Treeview per visualizzare i buoni."""
        style = ttk.Style()
        style.configure("Treeview", rowheight=36, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 11))

        colonne = ("ID", "Codice", "Tipo", "Valore (€)", "Residuo (€)",
                   "Stato", "Scadenza", "Cliente acquirente")

        self.tree = ttk.Treeview(self, columns=colonne, show="headings")

        colonne_larghezze = {
            "ID": 50,
            "Codice": 120,
            "Tipo": 80,
            "Valore (€)": 80,
            "Residuo (€)": 80,
            "Stato": 100,
            "Scadenza": 100,
            "Cliente acquirente": 150,
        }

        for col in colonne:
            self.tree.heading(col, text=col, command=lambda c=col: self.ordina_per_colonna(c))
            self.tree.column(col, width=colonne_larghezze[col], anchor="center")

        # Configura tag per colori in base allo stato
        self.tree.tag_configure("ATTIVO", foreground="green")
        self.tree.tag_configure("UTILIZZATO", foreground="gray")
        self.tree.tag_configure("SCADUTO", foreground="orange")
        self.tree.tag_configure("ANNULLATO", foreground="red")

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _crea_menu_contestuale(self):
        """Crea il menu contestuale per la tabella."""
        voci = [
            ("📋 Copia codice", self.copia_codice),
            ("🔍 Dettagli buono", self.mostra_dettagli_buono),  # <-- NUOVA VOCE
            ("📜 Storico utilizzi", self.mostra_utilizzi),
            ("❌ Annulla buono", self.annulla_buono),
        ]
        crea_menu_contestuale(self.tree, voci)

    def mostra_dettagli_buono(self):
        """Mostra i dettagli del buono in una finestra con tabella."""
        selezione = self.get_selezione()
        if not selezione:
            return

        with db_cursor() as cur:
            cur.execute("SELECT * FROM buoni WHERE id = ?", (selezione['id'],))
            row = cur.fetchone()

            if not row:
                mostra_errore("Errore", "Buono non trovato.", parent=self)
                return

            columns = [desc[0] for desc in cur.description]
            buono = dict(zip(columns, row))

        # Prepara i dati per la visualizzazione a tabella
        dati = [
            ("Codice", buono['codice']),
            ("Tipo", buono['tipo']),
            ("Stato", buono['stato']),
            ("Valore originale", f"€ {buono['valore_originale']:.2f}"),
            ("Valore residuo", f"€ {buono['valore_residuo']:.2f}"),
            ("Incassato", f"€ {buono['incassato']:.2f}"),
            ("Metodo pagamento", buono['metodo_pagamento'] or "Non specificato"),
            ("Acquirente", buono['cliente_acquirente']),
            ("Beneficiario", buono['cliente_beneficiario'] or "Non specificato"),
            ("Data creazione", buono['data_creazione'][:16] if buono['data_creazione'] else "N/A"),
            ("Data incasso", buono['data_incasso'][:16] if buono['data_incasso'] else "Non incassato"),
            ("Data scadenza", buono['data_scadenza'] or "Nessuna"),
            ("Note", buono['note'] or "-"),
        ]

        colonne = [("campo", "Campo"), ("valore", "Valore")]
        crea_finestra_con_treeview(
            self,
            f"Dettagli Buono - {buono['codice']}",
            colonne,
            dati
        )

    def carica_dati(self):
        """Carica i buoni dal database."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Determina i filtri
        stato = self.filtro_stato.get()
        if stato == "TUTTI":
            stato = None

        tipo = self.filtro_tipo.get()
        if tipo == "TUTTI":
            tipo = None

        # Determina ordinamento
        campo_ordine = None
        if self.ordina_colonna and self.ordina_colonna in self.mappa_colonne:
            campo_ordine = self.mappa_colonne[self.ordina_colonna]

        buoni = BuonoManager.get_lista_buoni(
            stato=stato,
            tipo=tipo,
            ordina_per=campo_ordine or "data_creazione",
            ordine_asc=self.ordina_asc
        )

        for b in buoni:
            # Determina il tag in base allo stato
            tag = b['stato']

            # Formatta la data di scadenza
            scadenza = b['data_scadenza'] if b['data_scadenza'] else "-"

            self.tree.insert("", "end",
                             values=(
                                 b['id'],
                                 b['codice'],
                                 b['tipo'],
                                 f"{b['valore_originale']:.2f}",
                                 f"{b['valore_residuo']:.2f}",
                                 b['stato'],
                                 scadenza,
                                 b['cliente_acquirente']
                             ),
                             tags=(tag,)
                             )

    def ordina_per_colonna(self, colonna):
        """Ordina la tabella per la colonna selezionata."""
        self.stato_ordinamento = ordina_colonna_treeview(
            self.tree, colonna, self.stato_ordinamento
        )
        self.ordina_colonna = colonna
        self.ordina_asc = self.stato_ordinamento['ascendente']
        self.carica_dati()

    def get_selezione(self):
        """Restituisce i dati della riga selezionata."""
        sel = self.tree.selection()
        if not sel:
            mostra_attenzione("Selezione mancante", "Seleziona un buono.", parent=self)
            return None

        item = self.tree.item(sel[0])
        return {
            "id": int(item['values'][0]),
            "codice": item['values'][1],
            "tipo": item['values'][2],
            "valore": float(item['values'][3]),
            "residuo": float(item['values'][4]),
            "stato": item['values'][5],
            "cliente": item['values'][7]
        }

    def nuovo_buono(self):
        """Crea un nuovo buono."""
        # Dialog per inserimento dati
        dialog = NuovoBuonoDialog(self)
        self.wait_window(dialog)

        if dialog.risultato:
            dati = dialog.risultato
            successo, msg, buono = BuonoManager.crea_buono(
                tipo=dati['tipo'],
                valore=dati['valore'],
                cliente_acquirente=dati['cliente_acquirente'],
                cliente_beneficiario=dati['cliente_beneficiario'],
                giorni_scadenza=dati['giorni_scadenza'],
                note=dati['note']
            )

            if successo:
                # Chiedi se stampare/copiare il codice
                if messagebox.askyesno("Codice generato",
                                       f"Buono creato con successo!\n\n"
                                       f"Codice: {buono['codice']}\n\n"
                                       f"Vuoi copiarlo negli appunti?",
                                       parent=self):
                    try:
                        import pyperclip
                        pyperclip.copy(buono['codice'])
                        mostra_info("Copiato", "Codice copiato negli appunti!", parent=self)
                    except ImportError:
                        mostra_info("Codice", f"Codice: {buono['codice']}", parent=self)

                self.carica_dati()
            else:
                mostra_errore("Errore", msg, parent=self)

    def copia_codice(self):
        """Copia il codice del buono selezionato negli appunti."""
        selezione = self.get_selezione()
        if not selezione:
            return

        try:
            import pyperclip
            pyperclip.copy(selezione['codice'])
            mostra_info("Copiato", f"Codice {selezione['codice']} copiato negli appunti!", parent=self)
        except ImportError:
            mostra_info("Codice", f"Codice: {selezione['codice']}", parent=self)

    def mostra_utilizzi(self, buono_id=None, codice=None):
        """
        Mostra gli utilizzi di un buono.
        Se buono_id non è fornito, usa il buono selezionato.
        """
        # Se non è passato buono_id, prendi dalla selezione
        if buono_id is None:
            selezione = self.get_selezione()
            if not selezione:
                return
            buono_id = selezione['id']
            codice = selezione['codice']

        from logic.buoni import BuonoManager

        utilizzi = BuonoManager.get_utilizzi_buono(buono_id)

        if not utilizzi:
            mostra_info("Nessun utilizzo", f"Il buono {codice} non è stato ancora utilizzato.", parent=self)
            return

        colonne = [
            ("data_utilizzo", "Data utilizzo"),
            ("importo_utilizzato", "Importo (€)"),
            ("cliente", "Cliente"),
            ("note", "Note")
        ]

        dati = [(u['data_utilizzo'][:10], f"{u['importo_utilizzato']:.2f}",
                 u['cliente'] or "", u['note'] or "") for u in utilizzi]

        from utils.gui_utils import crea_finestra_con_treeview
        crea_finestra_con_treeview(
            self,
            f"Utilizzi buono {codice}",
            colonne,
            dati,
            {"data_utilizzo": "date", "importo_utilizzato": "numeric"}
        )

    def annulla_buono(self):
        """Annulla il buono selezionato."""
        selezione = self.get_selezione()
        if not selezione:
            return

        if selezione['stato'] != 'ATTIVO':
            mostra_attenzione("Attenzione", f"Non puoi annullare un buono con stato '{selezione['stato']}'.",
                              parent=self)
            return

        motivazione = simpledialog.askstring("Annulla buono",
                                             "Motivo dell'annullamento:",
                                             parent=self)
        if motivazione is None:
            return

        if chiedi_conferma("Conferma annullamento",
                           f"Sei sicuro di voler annullare il buono {selezione['codice']}?",
                           parent=self):
            if BuonoManager.annulla_buono(selezione['id'], motivazione):
                mostra_info("Annullato", "Buono annullato con successo.", parent=self)
                self.carica_dati()
            else:
                mostra_errore("Errore", "Impossibile annullare il buono.", parent=self)


class NuovoBuonoDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Nuovo Buono")
        self.geometry("550x500")
        self.configure(bg="#f7f1e1")
        self.transient(parent)
        self.grab_set()

        self.risultato = None
        self._crea_interfaccia()
        self._centra_finestra()

    def _crea_interfaccia(self):
        """Crea l'interfaccia del dialog."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Tipo buono
        ttk.Label(main_frame, text="Tipo buono:").grid(row=0, column=0, sticky="w", pady=5)
        self.tipo_var = tk.StringVar(value="REGALO")
        frame_tipo = ttk.Frame(main_frame)
        frame_tipo.grid(row=0, column=1, sticky="w", pady=5)
        ttk.Radiobutton(frame_tipo, text="Regalo", variable=self.tipo_var,
                        value="REGALO").pack(side="left", padx=5)
        ttk.Radiobutton(frame_tipo, text="Sconto %", variable=self.tipo_var,
                        value="SCONTO").pack(side="left", padx=5)

        # Valore
        ttk.Label(main_frame, text="Valore nominale:").grid(row=1, column=0, sticky="w", pady=5)
        frame_valore = ttk.Frame(main_frame)
        frame_valore.grid(row=1, column=1, sticky="w", pady=5)
        self.valore_var = tk.DoubleVar(value=10.0)
        ttk.Entry(frame_valore, textvariable=self.valore_var, width=10).pack(side="left")
        ttk.Label(frame_valore, text="€ (per REGALO) o % (per SCONTO)").pack(side="left", padx=5)

        # 🔥 NUOVO: Importo incassato
        ttk.Label(main_frame, text="Importo incassato:").grid(row=2, column=0, sticky="w", pady=5)
        frame_incasso = ttk.Frame(main_frame)
        frame_incasso.grid(row=2, column=1, sticky="w", pady=5)
        self.incassato_var = tk.DoubleVar(value=0.0)
        ttk.Entry(frame_incasso, textvariable=self.incassato_var, width=10).pack(side="left")
        ttk.Label(frame_incasso, text="€ (0 = non ancora pagato)").pack(side="left", padx=5)

        # 🔥 NUOVO: Metodo pagamento
        ttk.Label(main_frame, text="Metodo pagamento:").grid(row=3, column=0, sticky="w", pady=5)
        self.metodo_var = tk.StringVar()
        frame_metodo = ttk.Frame(main_frame)
        frame_metodo.grid(row=3, column=1, sticky="w", pady=5)
        ttk.Combobox(frame_metodo, textvariable=self.metodo_var,
                     values=["Contanti", "Carta", "Bonifico", "Altro"],
                     width=15).pack(side="left")

        # Cliente acquirente
        ttk.Label(main_frame, text="Cliente acquirente:").grid(row=4, column=0, sticky="w", pady=5)
        self.cliente_acquirente_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.cliente_acquirente_var, width=40).grid(row=4, column=1, pady=5)

        # Cliente beneficiario (opzionale)
        ttk.Label(main_frame, text="Intestato a (opzionale):").grid(row=5, column=0, sticky="w", pady=5)
        self.cliente_beneficiario_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.cliente_beneficiario_var, width=40).grid(row=5, column=1, pady=5)

        # Scadenza
        ttk.Label(main_frame, text="Scadenza:").grid(row=6, column=0, sticky="w", pady=5)
        frame_scadenza = ttk.Frame(main_frame)
        frame_scadenza.grid(row=6, column=1, sticky="w", pady=5)
        self.scadenza_var = tk.StringVar(value="nessuna")
        ttk.Radiobutton(frame_scadenza, text="Nessuna", variable=self.scadenza_var,
                        value="nessuna").pack(side="left", padx=5)
        ttk.Radiobutton(frame_scadenza, text="30 giorni", variable=self.scadenza_var,
                        value="30").pack(side="left", padx=5)
        ttk.Radiobutton(frame_scadenza, text="60 giorni", variable=self.scadenza_var,
                        value="60").pack(side="left", padx=5)
        ttk.Radiobutton(frame_scadenza, text="90 giorni", variable=self.scadenza_var,
                        value="90").pack(side="left", padx=5)

        # Note
        ttk.Label(main_frame, text="Note:").grid(row=7, column=0, sticky="w", pady=5)
        self.note_text = tk.Text(main_frame, width=40, height=3, font=("Segoe UI", 9))
        self.note_text.grid(row=7, column=1, pady=5)

        # Pulsanti
        frame_btn = ttk.Frame(main_frame)
        frame_btn.grid(row=8, column=0, columnspan=2, pady=20)

        ttk.Button(frame_btn, text="Crea", command=self._conferma).pack(side="left", padx=5)
        ttk.Button(frame_btn, text="Annulla", command=self._annulla).pack(side="left", padx=5)

    def _conferma(self):
        """Conferma la creazione del buono."""
        try:
            valore = self.valore_var.get()
            if valore <= 0:
                messagebox.showerror("Errore", "Il valore deve essere positivo", parent=self)
                return

            incassato = self.incassato_var.get()
            if incassato < 0:
                messagebox.showerror("Errore", "L'importo incassato non può essere negativo", parent=self)
                return

            if incassato > valore and self.tipo_var.get() == "REGALO":
                if not messagebox.askyesno("Attenzione",
                                           "L'importo incassato è maggiore del valore nominale. Continuare?",
                                           parent=self):
                    return

            cliente_acquirente = self.cliente_acquirente_var.get().strip()
            if not cliente_acquirente:
                messagebox.showerror("Errore", "Inserisci il cliente acquirente", parent=self)
                return

            giorni_scadenza = None
            if self.scadenza_var.get() != "nessuna":
                giorni_scadenza = int(self.scadenza_var.get())

            self.risultato = {
                'tipo': self.tipo_var.get(),
                'valore': valore,
                'incassato': incassato,
                'metodo_pagamento': self.metodo_var.get(),
                'cliente_acquirente': cliente_acquirente,
                'cliente_beneficiario': self.cliente_beneficiario_var.get().strip(),
                'giorni_scadenza': giorni_scadenza,
                'note': self.note_text.get("1.0", "end").strip()
            }
            self.destroy()

        except Exception as e:
            messagebox.showerror("Errore", f"Dati non validi: {e}", parent=self)

    def _annulla(self):
        """Annulla l'operazione."""
        self.risultato = None
        self.destroy()

    def _centra_finestra(self):
        """Centra la finestra rispetto al parent."""
        self.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")