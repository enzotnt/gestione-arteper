# gui/ordini_gui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
from datetime import datetime, timedelta
from pathlib import Path

from tkcalendar import DateEntry

from logic.ordini import OrdineManager, ComponentiMancantiManager
from logic.magazzino import aggiungi_scorte
from utils.helpers import (
    mostra_info, mostra_attenzione, mostra_errore, chiedi_conferma,
    treeview_sort_column, db_cursor
)
from utils.componenti_mancanti_util import apri_componenti_mancanti
from utils.magazzino_util import on_doppio_click


class TabOrdini(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f7f1e1")
        self.pack(padx=10, pady=10, fill="both", expand=True)

        self.ordina_colonna = None
        self.ordina_asc = True
        self.progetti = []
        self.percorso_salvataggio = Path.home() / "LAVORI"

        self.crea_widgets()

    # =========================================================================
    # CREAZIONE INTERFACCIA
    # =========================================================================

    def crea_widgets(self):
        """Crea tutti i widget dell'interfaccia."""
        self._crea_sezione_nuovo_ordine()
        self._crea_sezione_ordini_esistenti()
        self.carica_progetti()
        self.carica_ordini()

    def _crea_sezione_nuovo_ordine(self):
        """Crea la sezione per l'inserimento di nuovi ordini."""
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

        # Frame principale
        frame_nuovo = tk.LabelFrame(
            self, text="Nuovo Ordine", bg="#f7f1e1",
            font=("Segoe UI", 10, "bold"), padx=10, pady=10
        )
        frame_nuovo.pack(fill="x", padx=10, pady=10)

        # Frame sinistro - Lista progetti
        frame_progetti = tk.Frame(frame_nuovo, bg="#f7f1e1")
        frame_progetti.grid(row=0, column=0, sticky="nw", padx=(0, 15))

        tk.Label(
            frame_progetti, text="Seleziona Progetti:",
            bg="#f7f1e1", font=("Segoe UI", 10)
        ).grid(row=0, column=0, sticky="nw")

        self.lista_progetti = tk.Listbox(
            frame_progetti, selectmode="multiple",
            height=9, width=40
        )
        self.lista_progetti.grid(row=1, column=0, padx=5, pady=5)

        # Frame centrale - Campi inserimento
        frame_campi = tk.Frame(frame_nuovo, bg="#f7f1e1")
        frame_campi.grid(row=0, column=1, sticky="nw")

        # Cliente
        tk.Label(frame_campi, text="Cliente:", bg="#f7f1e1").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.entry_cliente = ttk.Entry(frame_campi, width=30)
        self.entry_cliente.grid(row=0, column=1, padx=5, pady=2)

        # Data consegna
        tk.Label(frame_campi, text="Data consegna:", bg="#f7f1e1").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.entry_data_consegna = ttk.Entry(frame_campi, width=20)
        self.entry_data_consegna.grid(row=1, column=1, padx=5, pady=2)
        self.entry_data_consegna.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Note
        tk.Label(frame_campi, text="Note:", bg="#f7f1e1").grid(
            row=2, column=0, sticky="nw", pady=2
        )
        self.text_note = ScrolledText(frame_campi, width=50, height=9)
        self.text_note.grid(row=2, column=1, padx=5, pady=5)

        # Frame destro - Pulsanti
        frame_pulsanti = tk.Frame(frame_nuovo, bg="#f7f1e1")
        frame_pulsanti.grid(row=0, column=2, sticky="ne", padx=(15, 0))

        pulsanti = [
            ("📝 Crea Ordine", self.crea_ordine, btn_opts),
            ("🧩 Componenti Mancanti", lambda: apri_componenti_mancanti(self), btn_opts),
            ("✅ Stato Consegna", self.marca_come_consegnato, btn_opts),
            ("🔄 Aggiorna Progetti", self.carica_progetti, btn_opts),
            ("🔄 Aggiorna Tabella", self.aggiorna_tabella, btn_opts),
        ]

        for testo, comando, opts in pulsanti:
            btn = tk.Button(frame_pulsanti, text=testo, command=comando, **opts)
            btn.pack(fill="x", pady=(0, 5))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#f0d9b5'))
            btn.bind("<Leave>", lambda e, b=btn, c=opts["bg"]: b.configure(bg=c))

        # Pulsante elimina (con colori diversi)
        elimina_opts = btn_opts.copy()
        elimina_opts.update({
            "bg": "#d9534f",
            "activebackground": "#c9302c",
            "fg": "white",
            "activeforeground": "white"
        })
        self.btn_elimina = tk.Button(
            frame_pulsanti, text="🗑️ Elimina Ordine/i",
            command=self.elimina_ordine, **elimina_opts
        )
        self.btn_elimina.pack(fill="x", pady=(0, 5))
        self.btn_elimina.bind("<Enter>", lambda e: self.btn_elimina.configure(bg='#c9302c'))
        self.btn_elimina.bind("<Leave>", lambda e: self.btn_elimina.configure(bg='#d9534f'))

    def _crea_sezione_ordini_esistenti(self):
        """Crea la sezione con la tabella degli ordini esistenti."""
        frame_ordini = tk.LabelFrame(
            self, text="Ordini Esistenti", bg="#f7f1e1",
            font=("Segoe UI", 10, "bold"), padx=10, pady=10
        )
        frame_ordini.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Scrollbar
        scrollbar_y = ttk.Scrollbar(frame_ordini, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        # 🔥 DEFINISCI UNA SOLA VOLTA LE COLONNE (con pagamento)
        colonne = ("id", "cliente", "data_inserimento", "data_consegna", "countdown", "stato", "pagamento")
        self.tree = ttk.Treeview(
            frame_ordini, columns=colonne, show="headings",
            yscrollcommand=scrollbar_y.set
        )
        scrollbar_y.config(command=self.tree.yview)

        # Intestazioni
        intestazioni = {
            "id": "ID",
            "cliente": "Cliente",
            "data_inserimento": "Data Inserimento",
            "data_consegna": "Data Consegna",
            "countdown": "Giorni Mancanti",
            "stato": "Consegnato",
            "pagamento": "Stato Pagamento"
        }

        larghezze = {
            "id": 0,  # Nascosto
            "cliente": 150,
            "data_inserimento": 110,
            "data_consegna": 110,
            "countdown": 100,
            "stato": 80,
            "pagamento": 200  # 🔥 Aumentato per testo più lungo
        }

        for col, testo in intestazioni.items():
            self.tree.heading(
                col, text=testo,
                command=lambda c=col: self.ordina_colonna(c)
            )
            self.tree.column(col, width=larghezze[col], anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Stile Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#fff8f0",
            foreground="black",
            rowheight=25,
            fieldbackground="#fff8f0",
            borderwidth=1,
            relief="solid"
        )
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))
        style.map("Treeview", background=[("selected", "#f7c873")])

        # Tag per righe alternate
        self.tree.tag_configure("evenrow", background="#fff3e0")
        self.tree.tag_configure("oddrow", background="#ffe9cc")

        # Bind doppio click per dettaglio
        self.tree.bind("<Double-1>", self.apri_dettaglio_ordine)

    # =========================================================================
    # CARICAMENTO DATI
    # =========================================================================

    def aggiorna_tabella(self):
        """Aggiorna sia i progetti che gli ordini."""
        print("🔄 Aggiornamento tabella ordini...")
        self.carica_progetti()  # Aggiorna la lista progetti
        self.carica_ordini()  # Aggiorna la tabella ordini
        #mostra_info("Aggiornamento", "Tabella aggiornata con successo!", parent=self)

    def carica_progetti(self):
        """Carica la lista dei progetti (solo quelli in vendita) nella Listbox."""
        self.lista_progetti.delete(0, tk.END)

        self.progetti = OrdineManager.get_progetti_lista()

        if not self.progetti:
            # Nessun progetto in vendita
            self.lista_progetti.insert(tk.END, "⚠️ Nessun progetto in vendita")
            self.lista_progetti.config(state="disabled")
        else:
            self.lista_progetti.config(state="normal")
            for p in self.progetti:
                self.lista_progetti.insert(tk.END, p["nome"])

    def carica_ordini(self):
        """Carica gli ordini nella Treeview."""
        self.tree.delete(*self.tree.get_children())

        ordini = OrdineManager.get_ordini()
        oggi = datetime.today().date()

        for i, ordine in enumerate(ordini):
            # Formatta date
            data_ins = self._formatta_data(ordine["data_inserimento"])
            data_cons, giorni_mancanti = self._calcola_countdown(
                ordine["data_consegna"], oggi
            )

            # Stato consegna
            stato = "✔️" if ordine["consegnato"] else "❌"

            # 🔥 STATO PAGAMENTO
            stato_pagamento = ordine.get("stato_pagamento", "DA PAGARE")

            # Se l'ordine è consegnato ma non c'è stato pagamento, mostra "DA PAGARE"
            if ordine["consegnato"] and stato_pagamento == "DA PAGARE":
                stato_pagamento = "DA PAGARE (consegnato)"

            # Determina tag per righe alternate
            tag = "evenrow" if i % 2 == 0 else "oddrow"

            self.tree.insert(
                "", tk.END, iid=str(ordine["id"]),
                values=(
                    ordine["id"],
                    ordine["cliente"],
                    data_ins,
                    data_cons,
                    giorni_mancanti,
                    stato,
                    stato_pagamento  # 🔥 NUOVA COLONNA
                ),
                tags=(tag,)
            )

    def _formatta_data(self, data_str):
        """Formatta una data da YYYY-MM-DD a DD/MM/YYYY."""
        if not data_str:
            return "N/D"
        try:
            return datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return data_str

    def _calcola_countdown(self, data_consegna_str, oggi):
        """Calcola i giorni mancanti alla consegna."""
        if not data_consegna_str:
            return "N/D", "N/D"

        try:
            # Prova formato YYYY-MM-DD
            data_consegna = datetime.strptime(data_consegna_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                # Prova formato DD/MM/YYYY
                data_consegna = datetime.strptime(data_consegna_str, "%d/%m/%Y").date()
                data_consegna_str = data_consegna.strftime("%d/%m/%Y")
            except ValueError:
                return data_consegna_str, "N/D"

        giorni = (data_consegna - oggi).days
        if giorni >= 0:
            countdown = f"{giorni} gg"
        else:
            countdown = "Scaduto"

        return data_consegna_str, countdown

    # =========================================================================
    # ORDINAMENTO
    # =========================================================================

    def ordina_colonna(self, col):
        """Ordina la tabella per colonna."""
        if not hasattr(self, 'tree') or not self.tree:
            return

        dati = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

        # Tentativo di conversione per date
        if col in ("data_inserimento", "data_consegna"):
            try:
                dati = [(datetime.strptime(v, "%d/%m/%Y"), k) for v, k in dati if v != "N/D"]
            except Exception:
                pass
        elif col == "countdown":
            try:
                dati = [(int(v.split()[0]) if v != "N/D" and v != "Scaduto" else 9999, k)
                        for v, k in dati]
            except Exception:
                pass

        dati.sort(reverse=not self.ordina_asc)

        for index, (val, k) in enumerate(dati):
            self.tree.move(k, "", index)

        self.ordina_asc = not self.ordina_asc
        self.ordina_colonna = col

    # =========================================================================
    # AZIONI SUGLI ORDINI
    # =========================================================================

    def crea_ordine(self):
        """Crea un nuovo ordine usando il dialog unificato."""
        # Verifica che ci siano progetti disponibili
        if not self.progetti:
            mostra_attenzione("Attenzione", "Non ci sono progetti in vendita disponibili.")
            return

        selezionati = self.lista_progetti.curselection()
        if not selezionati:
            mostra_attenzione("Attenzione", "Seleziona almeno un progetto.")
            return

        # Raccogli i progetti selezionati con controllo indici
        progetti_selezionati = []
        for idx in selezionati:
            if idx < len(self.progetti):
                progetti_selezionati.append(self.progetti[idx])
            else:
                mostra_errore("Errore", "Selezione non valida.")
                return

        # Apri il dialog per la creazione dell'ordine
        dialog = DialogCreaOrdine(self, progetti_selezionati)
        self.wait_window(dialog)

        if not dialog or not dialog.result:
            return

        dati = dialog.result

        # 🔥 DEBUG: verifica i dati ricevuti
        print("\n" + "=" * 60)
        print("📦 DATI RICEVUTI DAL DIALOG:")
        print(f"Cliente: {dati['cliente']}")
        print(f"Data consegna: {dati['data_consegna']}")
        print(f"Acconto: {dati['acconto']} €")
        print(f"Totale ordine: {dati['totale_ordine']} €")
        print("\nProgetti con prezzi MODIFICATI:")
        for prog_id, prog_data in dati["progetti"].items():
            print(f"  - {prog_data['nome']}:")
            print(f"      Quantità: {prog_data['quantita']}")
            print(f"      Prezzo unitario: {prog_data['prezzo_unitario']:.2f} €")
            print(f"      Prezzo totale: {prog_data['prezzo_totale']:.2f} €")
        print("=" * 60 + "\n")

        # Verifica omonimia cliente (opzionale)
        # from logic.ordini import OrdineManager
        # if OrdineManager.cliente_esiste(dati["cliente"]):
        #     # Gestisci omonimia...

        # Crea ordine con prezzi e acconto - PASSA DIRETTAMENTE I DATI
        try:
            successo, msg, ordine_id = OrdineManager.crea_ordine_con_prezzi(
                cliente=dati["cliente"],
                data_consegna=dati["data_consegna"],
                note=dati["note"],
                progetti_con_prezzi=dati["progetti"],  # Passa l'intero dizionario con i prezzi
                acconto=dati["acconto"]
            )

            if successo and ordine_id:
                # Se c'è un acconto, registralo (se serve una tabella separata)
                if dati["acconto"] > 0:
                    # TODO: registra acconto
                    pass

                mostra_info("✅ Successo", f"Ordine creato con successo! ID: {ordine_id}")

                # Chiedi se salvare su disco
                if messagebox.askyesno("Salva su disco",
                                       "Vuoi salvare i dettagli dell'ordine su disco?"):
                    # Prepara i dati per il salvataggio
                    progetti_per_salvataggio = {}
                    for prog_id, prog_data in dati["progetti"].items():
                        progetti_per_salvataggio[prog_id] = (prog_data["nome"], prog_data["quantita"])

                    self._esegui_salvataggio(
                        dati["cliente"],
                        dati["data_consegna"],
                        progetti_per_salvataggio,
                        dati["note"]
                    )

                self.carica_ordini()
                self._pulisci_campi()
            else:
                mostra_errore("❌ Errore", msg or "Errore sconosciuto nella creazione dell'ordine")

        except Exception as e:
            mostra_errore("❌ Errore", f"Eccezione durante la creazione: {str(e)}")
            import traceback
            traceback.print_exc()
    def _chiedi_salvataggio_su_disco(self, cliente, data_consegna, progetti_quantita, note):
        """Chiede all'utente se vuole salvare l'ordine su disco."""
        win = tk.Toplevel(self)
        win.title("Salva su disco")
        win.geometry("450x180")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)

        tk.Label(
            win, text="Vuoi salvare i dati dell'ordine anche su disco?"
        ).pack(pady=(10, 5))

        path_var = tk.StringVar(value=str(self.percorso_salvataggio))
        tk.Label(win, textvariable=path_var, fg="blue").pack()

        def cambia_cartella():
            nuovo_path = filedialog.askdirectory(
                initialdir=self.percorso_salvataggio, parent=win
            )
            if nuovo_path:
                self.percorso_salvataggio = Path(nuovo_path)
                path_var.set(str(nuovo_path))

        tk.Button(win, text="📂 Cambia cartella", command=cambia_cartella).pack(pady=5)

        def conferma():
            win.destroy()
            messaggi = self._esegui_salvataggio(
                cliente, data_consegna, progetti_quantita, note
            )
            mostra_info("Salvataggio completato", "\n\n".join(messaggi))

        def annulla():
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Conferma salvataggio", command=conferma).pack(
            side="left", padx=10
        )
        tk.Button(btn_frame, text="Annulla", command=annulla).pack(
            side="left", padx=10
        )

    def _esegui_salvataggio(self, cliente, data_consegna, progetti_quantita, note):
        """Salva l'ordine su disco."""
        from config.config import config
        import os
        from pathlib import Path
        import shutil
        from datetime import datetime

        messaggi = []

        # 🔴 RECUPERA CONFIGURAZIONI
        cartella_sorgente = config.get("ordini", "cartella_sorgente", default="FILE_ORDINI")
        cartella_destinazione_base = config.get("ordini", "cartella_destinazione", default="")
        copia_file = config.get("ordini", "copia_file_ordini", default=True)
        apri_cartella = config.get("ordini", "apri_cartella_dopo_salvataggio", default=False)

        # 🔴 GESTIONE CARTELLA DESTINAZIONE
        if not cartella_destinazione_base:
            # Default: cartella "Ordini" nella home dell'utente
            cartella_destinazione_base = os.path.expanduser("~/Documents/Ordini")
            messaggi.append(f"📁 Usata cartella di default: {cartella_destinazione_base}")

        # Crea la cartella base se non esiste
        Path(cartella_destinazione_base).mkdir(parents=True, exist_ok=True)

        # Crea la cartella per il cliente (rimuovi caratteri problematici)
        nome_cartella_cliente = "".join(c for c in cliente if c.isalnum() or c in " -_").strip()
        if not nome_cartella_cliente:
            nome_cartella_cliente = "cliente_senza_nome"

        base_path = Path(cartella_destinazione_base) / nome_cartella_cliente
        base_path.mkdir(parents=True, exist_ok=True)

        # 🔴 GESTIONE CARTELLA SORGENTE
        if copia_file:
            sorgente_path = Path(cartella_sorgente)
            if sorgente_path.exists() and sorgente_path.is_dir():
                # Conta quanti elementi copiati
                elementi_copiati = 0
                for item in sorgente_path.iterdir():
                    destinazione = base_path / item.name
                    try:
                        if item.is_dir():
                            shutil.copytree(item, destinazione, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, destinazione)
                        elementi_copiati += 1
                        messaggi.append(f"✅ Copiato: {item.name}")
                    except Exception as e:
                        messaggi.append(f"⚠️ Errore copia {item.name}: {e}")

                if elementi_copiati > 0:
                    messaggi.append(f"✅ Copiati {elementi_copiati} elementi da: {cartella_sorgente}")
                else:
                    messaggi.append(f"⚠️ La cartella sorgente è vuota: {cartella_sorgente}")
            else:
                messaggi.append(f"⚠️ Cartella sorgente non trovata: {cartella_sorgente}")
        else:
            messaggi.append("⏭️ Copia file saltata (disabilitata in configurazione).")

        # Salva ordine.txt
        file_path = base_path / "ordine.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Cliente: {cliente}\n")
            f.write(f"Data ordine: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"Data consegna: {data_consegna}\n")
            f.write("\nProgetti ordinati:\n")
            for _, (nome, quantita) in progetti_quantita.items():
                f.write(f" - {nome} (x{quantita})\n")
            f.write("\nNote:\n")
            f.write(note if note else "Nessuna")

        messaggi.append(f"✅ Ordine salvato in:\n{file_path}")

        # 🔴 APRI CARTELLA SE CONFIGURATO
        if apri_cartella:
            try:
                import subprocess
                import platform
                if platform.system() == "Windows":
                    os.startfile(base_path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', base_path])
                else:  # linux
                    subprocess.run(['xdg-open', base_path])
            except Exception as e:
                messaggi.append(f"⚠️ Errore nell'aprire la cartella: {e}")

        return messaggi

    def _pulisci_campi(self):
        """Pulisce i campi di inserimento dopo un ordine."""
        self.entry_cliente.delete(0, tk.END)
        self.text_note.delete("1.0", tk.END)
        self.lista_progetti.selection_clear(0, tk.END)

    def marca_come_consegnato(self):
        """Cambia lo stato di consegna dell'ordine selezionato."""
        item = self.tree.selection()
        if not item:
            mostra_attenzione("Attenzione", "Seleziona un ordine.")
            return

        ordine_id = int(item[0])
        successo, nuovo_stato, msg = OrdineManager.toggle_consegnato(ordine_id)

        if successo:
            testo = "consegnato" if nuovo_stato == 1 else "non consegnato"
            mostra_info("Stato aggiornato", f"Ordine marcato come {testo}.")
            self.carica_ordini()
        else:
            mostra_errore("Errore", msg)

    def elimina_ordine(self):
        """Elimina gli ordini selezionati."""
        selected = self.tree.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona almeno un ordine da eliminare.")
            return

        conferma = chiedi_conferma(
            "Conferma",
            f"Sei sicuro di voler eliminare {len(selected)} ordine/i selezionato/i?"
        )
        if not conferma:
            return

        ordine_ids = [int(item) for item in selected]
        successo, msg = OrdineManager.elimina_ordini(ordine_ids)

        if successo:
            mostra_info("Eliminazione completata", msg)
            self.carica_ordini()
        else:
            mostra_errore("Errore", f"Errore durante l'eliminazione: {msg}")

    def apri_dettaglio_ordine(self, event):
        """Apre la finestra di dettaglio dell'ordine."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        ordine_id = int(item)
        self.mostra_finestra_dettaglio(ordine_id)

    def mostra_finestra_dettaglio(self, ordine_id):
        """Mostra una finestra con i dettagli dell'ordine."""
        ordine = OrdineManager.get_ordine_dettaglio(ordine_id)
        if not ordine:
            mostra_errore("Errore", "Ordine non trovato.")
            return

        progetti = OrdineManager.get_progetti_ordinati(ordine_id)

        print(f"\n🔍 DETTAGLIO ORDINE #{ordine_id}")
        print(f"   Totale ordine dal DB: {ordine.get('prezzo_totale')}")
        print(f"   Progetti trovati: {len(progetti)}")
        for p in progetti:
            print(f"   - {p['nome']}: qta {p['quantita']}, "
                  f"prezzo_unitario {p.get('prezzo_unitario')}, "
                  f"prezzo_totale {p.get('prezzo_totale')}")

        # Crea popup
        popup = tk.Toplevel(self)
        popup.title(f"Dettaglio Ordine - Cliente: {ordine['cliente']}")
        popup.geometry("650x700")
        popup.configure(bg="#f7f1e1")
        popup.transient(self)
        popup.update_idletasks()
        popup.grab_set()

        # Frame principale con scroll
        main_frame = tk.Frame(popup, bg="#f7f1e1")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Canvas per lo scroll
        canvas = tk.Canvas(main_frame, bg="#f7f1e1", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#f7f1e1")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0

        # Intestazione
        tk.Label(scroll_frame, text=f"DETTAGLIO ORDINE ID:{ordine_id} - {ordine['cliente']}",
                 font=("Segoe UI", 14, "bold"), bg="#f7f1e1", fg="#5a3e1b").grid(
            row=row, column=0, columnspan=2, pady=(0, 15))
        row += 1

        # Cliente
        tk.Label(scroll_frame, text="Cliente:", font=("Segoe UI", 10, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        entry_cliente = ttk.Entry(scroll_frame, width=40, font=("Segoe UI", 10))
        entry_cliente.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        entry_cliente.insert(0, ordine["cliente"])
        row += 1

        # Data inserimento (sola lettura)
        tk.Label(scroll_frame, text="Data Inserimento:", font=("Segoe UI", 10, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        tk.Label(scroll_frame, text=ordine["data_inserimento"], bg="#f7f1e1",
                 font=("Segoe UI", 10)).grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        # Data consegna
        tk.Label(scroll_frame, text="Data Consegna:", font=("Segoe UI", 10, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        entry_data = ttk.Entry(scroll_frame, width=20, font=("Segoe UI", 10))
        entry_data.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        entry_data.insert(0, ordine["data_consegna"] or "")
        row += 1

        # Stato consegna
        tk.Label(scroll_frame, text="Consegnato:", font=("Segoe UI", 10, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        stato_text = "✅ Sì" if ordine["consegnato"] else "❌ No"
        tk.Label(scroll_frame, text=stato_text, bg="#f7f1e1",
                 font=("Segoe UI", 10)).grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        # Prezzi e acconto (se presenti)
        if "prezzo_totale" in ordine and ordine["prezzo_totale"]:
            tk.Label(scroll_frame, text="Totale Ordine:", font=("Segoe UI", 10, "bold"),
                     bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)
            tk.Label(scroll_frame, text=f"€ {ordine['prezzo_totale']:.2f}",
                     bg="#f7f1e1", font=("Segoe UI", 10, "bold"), fg="#3366cc").grid(
                row=row, column=1, sticky="w", padx=5)
            row += 1

        if "acconto" in ordine and ordine["acconto"]:
            tk.Label(scroll_frame, text="Acconto Versato:", font=("Segoe UI", 10, "bold"),
                     bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)
            tk.Label(scroll_frame, text=f"€ {ordine['acconto']:.2f}",
                     bg="#f7f1e1", font=("Segoe UI", 10), fg="green").grid(
                row=row, column=1, sticky="w", padx=5)
            row += 1

        if "stato_pagamento" in ordine:
            tk.Label(scroll_frame, text="Stato Pagamento:", font=("Segoe UI", 10, "bold"),
                     bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=5, padx=5)

            stato_colori = {
                "DA PAGARE": "red",
                "PARZIALE": "orange",
                "PAGATO": "green"
            }
            colore = stato_colori.get(ordine["stato_pagamento"], "black")

            tk.Label(scroll_frame, text=ordine["stato_pagamento"],
                     bg="#f7f1e1", font=("Segoe UI", 10, "bold"), fg=colore).grid(
                row=row, column=1, sticky="w", padx=5)
            row += 1

        # Note
        tk.Label(scroll_frame, text="Note:", font=("Segoe UI", 10, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="nw", pady=5, padx=5)
        text_note = tk.Text(scroll_frame, width=50, height=4, font=("Segoe UI", 9))
        text_note.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        text_note.insert("1.0", ordine["note"] or "")
        row += 1

        # Progetti ordinati
        tk.Label(scroll_frame, text="Progetti Ordinati:", font=("Segoe UI", 10, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5))
        row += 1

        # Treeview per i progetti
        tree_frame = tk.Frame(scroll_frame)
        tree_frame.grid(row=row, column=0, columnspan=2, pady=5, sticky="nsew")

        colonne = ("progetto", "quantita", "prezzo_unitario", "prezzo_totale")
        tree_progetti = ttk.Treeview(tree_frame, columns=colonne, show="headings", height=6)

        tree_progetti.heading("progetto", text="Progetto")
        tree_progetti.heading("quantita", text="Qtà")
        tree_progetti.heading("prezzo_unitario", text="Prezzo Unit.")
        tree_progetti.heading("prezzo_totale", text="Prezzo Tot.")

        tree_progetti.column("progetto", width=250)
        tree_progetti.column("quantita", width=60, anchor="center")
        tree_progetti.column("prezzo_unitario", width=100, anchor="center")
        tree_progetti.column("prezzo_totale", width=100, anchor="center")

        scrollbar_tree = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_progetti.yview)
        tree_progetti.configure(yscrollcommand=scrollbar_tree.set)

        tree_progetti.pack(side="left", fill="both", expand=True)
        scrollbar_tree.pack(side="right", fill="y")

        # 🔥 INSERIMENTO PROGETTI (UNA SOLA VOLTA)
        for p in progetti:
            prezzo_u = f"€ {p['prezzo_unitario']:.2f}" if p.get('prezzo_unitario') else "N/D"
            prezzo_t = f"€ {p['prezzo_totale']:.2f}" if p.get('prezzo_totale') else "N/D"

            tree_progetti.insert("", tk.END, values=(
                p["nome"],
                p["quantita"],
                prezzo_u,
                prezzo_t
            ))

            print(f"   Inserito in treeview: {p['nome']} - {prezzo_u} - {prezzo_t}")

        row += 1

        # Pulsanti
        frame_btn = tk.Frame(scroll_frame, bg="#f7f1e1")
        frame_btn.grid(row=row, column=0, columnspan=2, pady=20)

        def salva_modifiche():
            nuovo_cliente = entry_cliente.get().strip()
            nuova_data = entry_data.get().strip()
            nuove_note = text_note.get("1.0", "end").strip()

            if not nuovo_cliente:
                mostra_attenzione("Attenzione", "Il cliente non può essere vuoto.", parent=popup)
                return

            successo, msg = OrdineManager.aggiorna_ordine(
                ordine_id, nuovo_cliente, nuova_data, nuove_note
            )

            if successo:
                mostra_info("Successo", "Ordine aggiornato.", parent=popup)
                self.carica_ordini()
                popup.destroy()
            else:
                mostra_errore("Errore", msg, parent=popup)

        tk.Button(frame_btn, text="Salva Modifiche", command=salva_modifiche,
                  bg="#90EE90", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(frame_btn, text="Annulla", command=popup.destroy,
                  bg="#f0f0f0").pack(side="left", padx=5)

        # Centra la finestra
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - popup.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")


class DialogCreaOrdine(tk.Toplevel):
    def __init__(self, parent, progetti_selezionati):
        super().__init__(parent)
        self.parent = parent
        self.progetti = [dict(p) for p in progetti_selezionati if p]  # Filtra eventuali None
        self.result = None
        self.title("Nuovo Ordine")
        self.configure(bg="#f7f1e1")
        self.geometry("1600x800")  # Ridimensionato per essere più compatto
        self.transient(parent)

        # Dizionario per tracciare i componenti mancanti per progetto
        self.componenti_mancanti_per_progetto = {}

        if not self.progetti:
            messagebox.showerror("Errore", "Nessun progetto valido selezionato", parent=parent)
            self.destroy()
            return

        self._crea_interfaccia()
        self._centra_finestra()
        self.after(100, self.grab_set)

    def _crea_interfaccia(self):
        """Crea l'interfaccia del dialog."""
        # Intestazione cliente e data su stessa riga
        frame_top = tk.Frame(self, bg="#f7f1e1")
        frame_top.pack(fill="x", padx=10, pady=8)

        # Cliente
        tk.Label(frame_top, text="CLIENTE:", bg="#f7f1e1",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 2))
        self.entry_cliente = ttk.Entry(frame_top, width=25, font=("Segoe UI", 9))
        self.entry_cliente.pack(side="left", padx=5)

        # Separatore
        tk.Frame(frame_top, width=20, bg="#f7f1e1").pack(side="left")

        # Data consegna
        # Data consegna
        tk.Label(frame_top, text="CONSEGNA:", bg="#f7f1e1",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 2))


        self.data_consegna = DateEntry(
            frame_top,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',  # Formato YYYY-MM-DD per il database
            font=("Segoe UI", 9)
        )
        self.data_consegna.pack(side="left", padx=5)

        # Imposta data predefinita (tra 7 giorni)
        self.data_consegna.set_date(datetime.now() + timedelta(days=7))

        # Frame principale con due colonne
        frame_principale = tk.Frame(self, bg="#f7f1e1")
        frame_principale.pack(fill="both", expand=True, padx=10, pady=5)

        # COLONNA SINISTRA: Progetti (70%)
        frame_progetti = tk.Frame(frame_principale, bg="#f7f1e1")
        frame_progetti.pack(side="left", fill="both", expand=True, padx=(0, 5))

        tk.Label(frame_progetti, text="PROGETTI:", bg="#f7f1e1",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

        # Canvas con scrollbar per i progetti
        container = tk.Frame(frame_progetti, bg="#f7f1e1")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="#f7f1e1", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#f7f1e1")
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Intestazioni compatte
        self._crea_intestazioni(scroll_frame)

        # Righe progetti
        self.row_widgets = []
        from logic.progetti import Progetto

        for progetto in self.progetti:
            p = Progetto(carica_da_id=progetto["id"])
            prezzo_unitario = p.calcola_prezzo()
            progetto["prezzo_unitario"] = prezzo_unitario
            self._crea_riga_prodotto(scroll_frame, progetto)

        # COLONNA DESTRA: Componenti Mancanti (30%)
        frame_mancanti = tk.LabelFrame(frame_principale, text="⚠️ COMPONENTI MANCANTI",
                                       bg="#fff3e0", font=("Segoe UI", 11, "bold"),
                                       padx=10, pady=10)
        frame_mancanti.pack(side="right", fill="both", expand=True, padx=(10, 0))  # expand=True già presente

        # Text area per i componenti mancanti
        self.text_mancanti = tk.Text(frame_mancanti, height=15, width=20,
                                     font=("Segoe UI", 15),
                                     spacing3=10,  # AGGIUNGI QUESTO - spazio extra tra le righe
                                     bg="white",
                                     fg="#d32f2f")
        self.text_mancanti.pack(fill="both", expand=True)

        # Testo iniziale
        self.text_mancanti.insert("1.0", "Nessun componente mancante.\nModifica le quantità per\nvedere i dettagli.")
        self.text_mancanti.config(state="disabled")

        # Frame acconto e totale
        frame_bottom = tk.Frame(self, bg="#f7f1e1")
        frame_bottom.pack(fill="x", padx=10, pady=8)

        # Acconto
        tk.Label(frame_bottom, text="ACCONTO (€):", bg="#f7f1e1",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
        self.acconto_var = tk.DoubleVar(value=0.0)
        self.entry_acconto = ttk.Entry(frame_bottom, textvariable=self.acconto_var, width=10)
        self.entry_acconto.pack(side="left", padx=5)

        # Spazio
        tk.Frame(frame_bottom, width=20, bg="#f7f1e1").pack(side="left")

        # Totale ordine
        tk.Label(frame_bottom, text="TOTALE (€):", bg="#f7f1e1",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
        self.totale_ordine_var = tk.DoubleVar(value=self._calcola_totale())
        self.entry_totale_ordine = ttk.Entry(frame_bottom, textvariable=self.totale_ordine_var,
                                             width=12, font=("Segoe UI", 9, "bold"))
        self.entry_totale_ordine.pack(side="left", padx=5)

        # Note
        tk.Label(self, text="NOTE:", bg="#f7f1e1",
                 font=("Segoe UI", 9, "bold")).pack(pady=(2, 2))

        self.text_note = tk.Text(self, height=2, width=60, font=("Segoe UI", 9))
        self.text_note.pack(padx=10, pady=2, fill="x")

        # Pulsanti
        self._crea_pulsanti()

        # Flag per tracciare se l'utente ha modificato il totale
        self.totale_modificato = False

        def on_totale_edit(e):
            self.totale_modificato = True

        self.entry_totale_ordine.bind("<KeyRelease>", on_totale_edit)

        # Aggiorna totale quando cambiano i prezzi
        for rw in self.row_widgets:
            rw["p_tot_var"].trace_add("write", lambda *a: self._aggiorna_totale_se_non_modificato())
            rw["q_var"].trace_add("write", lambda *a: self._aggiorna_totale_se_non_modificato())

        self.bind("<Return>", lambda e: self.on_confirm())
        self.bind("<Escape>", lambda e: self.on_cancel())

    def _crea_intestazioni(self, parent):
        """Crea le intestazioni delle colonne."""
        header = tk.Frame(parent, bg="#f7f1e1")
        header.pack(fill="x", pady=(0, 5))

        headings = [
            ("Progetto", 30),  # Corrisponde a width=30 del nome
            ("Neg.", 7),  # Corrisponde a width=7 del negozio
            ("Ass.", 8),  # Corrisponde a width=8 assemblabili
            ("Tot.", 8),  # Corrisponde a width=8 totale
            ("Qtà", 5),  # Corrisponde a width=5 quantità
            ("€/pz", 9),  # Corrisponde a width=9 prezzo unitario
            ("€ tot", 10)  # Corrisponde a width=10 prezzo totale
        ]

        for i, (txt, w) in enumerate(headings):
            lbl = tk.Label(header, text=txt, font=("Segoe UI", 11, "bold"),  # Stesso font delle righe
                           bg="#f7f1e1", width=w, anchor="w" if i == 0 else "center")
            if i == 0:
                lbl.pack(side="left", padx=3, fill="x", expand=True)
            else:
                lbl.pack(side="left", padx=2)

    def _crea_riga_prodotto(self, parent, progetto):
        """Crea una riga per un progetto in versione compatta."""
        from logic.ordini import OrdineManager

        row = tk.Frame(parent, bg="#fffafa", bd=1, relief="solid")
        row.pack(fill="x", pady=4, padx=3)  # Aumentato pady e padx

        # Nome progetto (troncato se troppo lungo)
        nome = progetto["nome"][:30] + "..." if len(progetto["nome"]) > 30 else progetto["nome"]
        lbl_nome = tk.Label(row, text=nome, anchor="w",
                            bg="#fffafa", width=30,  # Aumentato da 25
                            font=("Segoe UI", 11))  # Aumentato da 9
        lbl_nome.pack(side="left", padx=(3, 2), fill="x", expand=True)

        # Disponibilità in negozio
        with db_cursor() as cur:
            cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?",
                        (progetto["id"],))
            row_negozio = cur.fetchone()
            disponibili_negozio = row_negozio[0] if row_negozio else 0

        # Calcola quanti si possono assemblare
        info_assembly = OrdineManager.calcola_progetti_assemblabili(progetto["id"])
        assemblabili = info_assembly["assemblabili"]

        # Totale disponibile
        totale_disp = disponibili_negozio + assemblabili

        lbl_negozio = tk.Label(row, text=str(disponibili_negozio), width=7,  # Aumentato da 5
                               bg="#fffafa", anchor="center",
                               font=("Segoe UI", 11))  # Aumentato da 9
        lbl_negozio.pack(side="left", padx=2)  # Aumentato padx

        lbl_assemblabili = tk.Label(row, text=str(assemblabili), width=8,  # Aumentato da 6
                                    bg="#e8f5e9", anchor="center", fg="#2e7d32",
                                    font=("Segoe UI", 11, "bold"))  # Aumentato da 9
        lbl_assemblabili.pack(side="left", padx=2)

        lbl_totale_disp = tk.Label(row, text=str(totale_disp), width=8,  # Aumentato da 6
                                   bg="#fff3e0", anchor="center", fg="#e65100",
                                   font=("Segoe UI", 11, "bold"))  # Aumentato da 9
        lbl_totale_disp.pack(side="left", padx=2)

        # Quantità
        q_var = tk.IntVar(value=1)
        sb = tk.Spinbox(row, from_=0, to=100, textvariable=q_var, width=5,  # Aumentato da 4
                        font=("Segoe UI", 11))  # Aumentato da 9
        sb.pack(side="left", padx=2)

        # Prezzo unitario
        p_unit_var = tk.DoubleVar(value=progetto['prezzo_unitario'])
        entry_prezzo_u = tk.Entry(row, textvariable=p_unit_var, width=9,  # Aumentato da 7
                                  justify="center", font=("Segoe UI", 11))  # Aumentato da 9
        entry_prezzo_u.pack(side="left", padx=2)

        # Prezzo totale
        p_tot_var = tk.DoubleVar(value=progetto['prezzo_unitario'])
        entry_prezzo_tot = tk.Entry(row, textvariable=p_tot_var, width=10,  # Aumentato da 8
                                    justify="center", font=("Segoe UI", 11))  # Aumentato da 9
        entry_prezzo_tot.pack(side="left", padx=2)

        # Callback per aggiornamento
        def on_qty_change(*a):
            try:
                q = q_var.get()
                p_unit = p_unit_var.get()
                nuovo_tot = p_unit * q
                p_tot_var.set(round(nuovo_tot, 2))

                self._aggiorna_label_assemblabili()
                self._aggiorna_componenti_mancanti_display()
                self._aggiorna_totali()
            except Exception:
                pass

        def on_unit_change(*a):
            try:
                q = q_var.get()
                p_unit = p_unit_var.get()
                nuovo_tot = p_unit * q
                p_tot_var.set(round(nuovo_tot, 2))
                self._aggiorna_totali()
            except Exception:
                pass

        def on_total_change(*a):
            try:
                self._aggiorna_totali()
            except Exception:
                pass

        q_var.trace_add("write", lambda *a: on_qty_change())
        p_unit_var.trace_add("write", lambda *a: on_unit_change())
        p_tot_var.trace_add("write", lambda *a: on_total_change())

        self.row_widgets.append({
            "progetto_id": progetto["id"],
            "nome": progetto["nome"],
            "q_var": q_var,
            "p_unit_var": p_unit_var,
            "p_tot_var": p_tot_var,
            "lbl_assemblabili": lbl_assemblabili,
            "lbl_totale_disp": lbl_totale_disp,
            "lbl_negozio": lbl_negozio
        })

    def _crea_pulsanti(self):
        """Crea i pulsanti in fondo al dialog."""
        bottom = tk.Frame(self, bg="#f7f1e1")
        bottom.pack(fill="x", padx=10, pady=5)

        tk.Button(bottom, text="Conferma Ordine", command=self.on_confirm,
                  bg="#90EE90", font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)
        tk.Button(bottom, text="Annulla", command=self.on_cancel,
                  bg="#f0f0f0", font=("Segoe UI", 9)).pack(side="right", padx=3)

    def _aggiorna_totali(self):
        """Aggiorna il totale dell'ordine."""
        totale = 0
        for rw in self.row_widgets:
            totale += rw["p_tot_var"].get()
        return totale

    def _aggiorna_totale_se_non_modificato(self):
        """Aggiorna il totale solo se l'utente non l'ha modificato."""
        if not self.totale_modificato:
            self.totale_ordine_var.set(self._calcola_totale())

    def _calcola_totale(self):
        """Calcola il totale corrente."""
        tot = 0.0
        for rw in self.row_widgets:
            tot += rw["p_tot_var"].get()
        return round(tot, 2)

    def _aggiorna_componenti_mancanti_display(self, progetto_id=None, quantita=None):
        """Aggiorna il display dei componenti mancanti (versione compatta)."""
        from logic.ordini import OrdineManager

        progetti_quantita = {}
        for rw in self.row_widgets:
            q = rw["q_var"].get()
            if q > 0:
                progetti_quantita[rw["progetto_id"]] = q

        if not progetti_quantita:
            self.text_mancanti.config(state="normal")
            self.text_mancanti.delete("1.0", tk.END)
            self.text_mancanti.insert("1.0", "✅ Carrello vuoto")
            self.text_mancanti.config(state="disabled")
            return

        info_ordine = OrdineManager.verifica_ordine_completo(progetti_quantita)

        self.text_mancanti.config(state="normal")
        self.text_mancanti.delete("1.0", tk.END)

        if info_ordine["ordine_completabile"]:
            testo = "✅ ORDINE COMPLETABILE\n"
            testo += "-" * 20 + "\n\n"
            for nome_comp, qta_nec in sorted(info_ordine["componenti_necessari"].items()):
                qta_disp = info_ordine["componenti_disponibili"].get(nome_comp, 0)
                testo += f"{nome_comp[:15]}: {int(qta_nec)} (disp:{qta_disp})\n"
        else:
            testo = "🔴 COMPONENTI MANCANTI\n"
            testo += "-" * 20 + "\n\n"
            for nome_comp, qta_nec in sorted(info_ordine["componenti_necessari"].items()):
                qta_disp = info_ordine["componenti_disponibili"].get(nome_comp, 0)
                if nome_comp in info_ordine["componenti_mancanti"]:
                    manca = info_ordine["componenti_mancanti"][nome_comp]
                    testo += f"❌ {nome_comp[:15]}: manca {int(manca)}\n"
                else:
                    testo += f"✅ {nome_comp[:15]}: OK\n"

        self.text_mancanti.insert("1.0", testo)
        self.text_mancanti.config(state="disabled")

    def _aggiorna_label_assemblabili(self):
        """Aggiorna i label dei progetti assemblabili (versione ottimizzata)."""
        consumo_cumulativo = {}

        for rw in self.row_widgets:
            progetto_id = rw["progetto_id"]
            q = rw["q_var"].get()

            if q <= 0:
                rw["lbl_assemblabili"].config(text="0")
                continue

            with db_cursor() as cur:
                cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?", (progetto_id,))
                row = cur.fetchone()
                disp_negozio = row[0] if row else 0

                da_assemblare = max(0, q - disp_negozio)

                if da_assemblare <= 0:
                    rw["lbl_assemblabili"].config(text="0")
                    continue

                cur.execute("""
                            SELECT m.nome, cp.quantita
                            FROM componenti_progetto cp
                                     JOIN magazzino m ON m.id = cp.componente_id
                            WHERE cp.progetto_id = ?
                            """, (progetto_id,))

                componenti_questo = cur.fetchall()

                if not componenti_questo:
                    rw["lbl_assemblabili"].config(text="0")
                    continue

                assemblabili = float('inf')

                for nome_comp, qta_per_prog in componenti_questo:
                    if qta_per_prog <= 0:
                        continue

                    cur.execute("SELECT quantita FROM magazzino WHERE nome = ?", (nome_comp,))
                    row = cur.fetchone()
                    disp_tot = row[0] if row else 0

                    già_consumato = consumo_cumulativo.get(nome_comp, 0)
                    rimane = disp_tot - già_consumato

                    se_questo = rimane // qta_per_prog if qta_per_prog > 0 else 0
                    assemblabili = min(assemblabili, se_questo)

                if assemblabili == float('inf'):
                    assemblabili = 0
                else:
                    assemblabili = max(0, int(assemblabili))

                rw["lbl_assemblabili"].config(text=str(assemblabili))

                for nome_comp, qta_per_prog in componenti_questo:
                    qta_consumata = qta_per_prog * da_assemblare
                    if nome_comp not in consumo_cumulativo:
                        consumo_cumulativo[nome_comp] = 0
                    consumo_cumulativo[nome_comp] += qta_consumata

    def on_confirm(self):
        """Conferma la creazione dell'ordine."""
        cliente = self.entry_cliente.get().strip()
        if not cliente:
            messagebox.showwarning("Attenzione", "Inserisci il nome del cliente.", parent=self)
            return

        data_consegna = self.data_consegna.get_date().strftime("%Y-%m-%d")
        if not data_consegna:
            messagebox.showwarning("Attenzione", "Inserisci la data di consegna.", parent=self)
            return

        progetti_quantita_prezzi = {}
        for rw in self.row_widgets:
            q = rw["q_var"].get()
            if q > 0:
                progetti_quantita_prezzi[rw["progetto_id"]] = {
                    "nome": rw["nome"],
                    "quantita": q,
                    "prezzo_unitario": rw["p_unit_var"].get(),
                    "prezzo_totale": rw["p_tot_var"].get()
                }

        if not progetti_quantita_prezzi:
            messagebox.showwarning("Attenzione", "Seleziona almeno un progetto.", parent=self)
            return

        acconto = self.acconto_var.get()
        note = self.text_note.get("1.0", "end").strip()

        self.result = {
            "cliente": cliente,
            "data_consegna": data_consegna,
            "progetti": progetti_quantita_prezzi,
            "acconto": acconto,
            "note": note,
            "totale_ordine": self.totale_ordine_var.get()
        }
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

    def _centra_finestra(self):
        self.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")



class TabComponentiMancanti(tk.Frame):
    """Tab per la gestione dei componenti mancanti."""

    def __init__(self, parent):
        super().__init__(parent, bg="#f7f1e1")
        self.pack(padx=10, pady=10, fill="both", expand=True)

        self.ordina_colonna = None
        self.ordina_asc = True

        self.crea_interfaccia()
        self.carica_componenti_mancanti()

    def crea_interfaccia(self):
        """Crea l'interfaccia del tab."""
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

        # Frame pulsanti
        frame_bottoni = tk.Frame(self, bg="#f7f1e1")
        frame_bottoni.pack(fill="x", pady=(10, 5))

        pulsanti = [
            ("🔄 Aggiorna", self.carica_componenti_mancanti, btn_opts),
            ("✅ Depenna", self.depenna_componente, btn_opts),
            ("📦 Componente ricevuto", self.componente_ricevuto, btn_opts),
        ]

        for testo, comando, opts in pulsanti:
            btn = tk.Button(frame_bottoni, text=testo, command=comando, **opts)
            btn.pack(side="left", padx=6)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg='#f0d9b5'))
            btn.bind("<Leave>", lambda e, b=btn, c=opts["bg"]: b.configure(bg=c))

        # Treeview
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 11))

        colonne = ("comp_id", "id", "progetto", "componente", "quantita", "data_rilevamento")
        intestazioni = ["CompID", "ID", "Progetto", "Componente", "Quantità", "Data rilevamento"]

        self.tree = ttk.Treeview(self, columns=colonne, show="headings")

        for col, nome in zip(colonne, intestazioni):
            self.tree.heading(col, text=nome, command=lambda c=col: self.ordina_per_colonna(c))
            if col in ("comp_id", "id"):
                self.tree.column(col, width=0, stretch=False)  # Nascoste
            else:
                self.tree.column(col, anchor="center", width=150)

        # Bind doppio click per aggiungere scorte
        # usiamo la quantità indicata nella colonna 4 come default
        self.tree.bind(
            "<Double-1>",
            lambda e: on_doppio_click(
                self, self.tree, self.carica_componenti_mancanti,
                comp_col=0, nome_col=3, qty_col=4
            )
        )

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def carica_componenti_mancanti(self):
        """Carica la lista dei componenti mancanti con riferimento all'ordine."""
        self.tree.delete(*self.tree.get_children())

        with db_cursor() as cur:
            cur.execute("""
                        SELECT cm.id,
                               cm.progetto_id,
                               cm.componente_id,
                               p.nome AS progetto,
                               m.nome AS componente,
                               cm.quantita_mancante,
                               cm.data_rilevamento,
                               po.ordine_id,
                               o.cliente
                        FROM componenti_mancanti cm
                                 JOIN progetti p ON cm.progetto_id = p.id
                                 JOIN magazzino m ON m.id = cm.componente_id
                                 LEFT JOIN progetti_ordinati po ON po.progetto_id = cm.progetto_id
                                 LEFT JOIN ordini o ON po.ordine_id = o.id
                        ORDER BY cm.data_rilevamento DESC
                        """)

            for row in cur.fetchall():
                data = row[6]
                data_da_mostrare = data[:16] if len(data) > 10 else data

                # Mostra l'ordine associato se disponibile
                if row[7]:  # ordine_id
                    info_ordine = f" (Ordine #{row[7]}: {row[8]})"
                else:
                    info_ordine = ""

                self.tree.insert("", tk.END, iid=str(row[0]), values=(
                    row[2],  # componente_id nascosto
                    row[0],  # id mancante
                    row[3] + info_ordine,  # progetto + info ordine
                    row[4],  # componente
                    f"{row[5]:.2f}",
                    data_da_mostrare
                ))

    def depenna_componente(self):
        """Elimina un componente dalla lista mancanti."""
        selezione = self.tree.selection()
        if not selezione:
            mostra_attenzione("Attenzione", "Seleziona una riga da depennare.")
            return

        id_mancante = int(selezione[0])
        successo, msg = ComponentiMancantiManager.elimina(id_mancante)

        if successo:
            mostra_info("Successo", msg)
            self.carica_componenti_mancanti()
        else:
            mostra_errore("Errore", msg)

    def ordina_per_colonna(self, colonna):
        """Ordina la tabella per colonna."""
        treeview_sort_column(self.tree, colonna, self)

    def componente_ricevuto(self):
        """Registra l'arrivo di un componente mancante."""
        selected = self.tree.focus()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un componente.")
            return

        id_mancante = int(selected)
        values = self.tree.item(selected, "values")
        nome_componente = values[3]
        quantita_mancante = float(values[4])

        # Recupera info componente
        info = ComponentiMancantiManager.get_info_componente(id_mancante)
        if not info:
            mostra_errore("Errore", "Record componente mancante non trovato.")
            return

        # Recupera ultimo movimento
        ultimo = ComponentiMancantiManager.get_ultimo_movimento(info["componente_id"])

        try:
            q_str = simpledialog.askstring(
                "Quantità",
                f"Quantità ricevuta per '{nome_componente}':",
                initialvalue=str(quantita_mancante),
                parent=self
            )
            if q_str is None:
                return
            quantita = round(float(q_str), 2)

            c_str = simpledialog.askstring(
                "Costo totale",
                "Costo totale (€):",
                parent=self
            )
            if c_str is None:
                return
            costo = float(c_str)

            fornitore = simpledialog.askstring(
                "Fornitore",
                "Nome del fornitore (opzionale):",
                initialvalue=ultimo["fornitore"],
                parent=self
            )
            if fornitore is None:
                fornitore = ""

            note = simpledialog.askstring(
                "Note",
                "Note (opzionale):",
                initialvalue=ultimo["note"],
                parent=self
            )
            if note is None:
                note = ""

            # Aggiorna magazzino
            aggiungi_scorte(info["componente_id"], quantita, costo, fornitore, note)

            # Rimuovi dalla lista mancanti
            ComponentiMancantiManager.elimina(id_mancante)

            mostra_info("Successo", f"Componente '{nome_componente}' aggiornato e rimosso dai mancanti.")
            self.carica_componenti_mancanti()

        except ValueError:
            mostra_errore("Errore", "Inserisci un numero valido per quantità e costo.")
        except Exception as e:
            mostra_errore("Errore", str(e))

