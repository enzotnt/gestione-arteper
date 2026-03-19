# gui/lavorazione_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from db.database import get_connection

from logic.lavorazione import LavorazioneManager, VenditaOrdineManager
from utils.helpers import (
    mostra_info, mostra_attenzione, mostra_errore, chiedi_conferma,
    db_cursor
)


class TabLavorazione(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#f7f1e1")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.ordini_dettaglio = {}  # Cache per i dettagli degli ordini
        self._crea_tabella()
        self._crea_pulsanti()
        self.carica_dati()

    def _crea_tabella(self):
        """Crea la tabella principale degli ordini in lavorazione."""
        colonne = [
            "ordine_id", "cliente", "data_inserimento", "data_consegna",
            "quantita", "stato", "in_lavorazione", "assemblati"
        ]

        self.tree = ttk.Treeview(self, columns=colonne, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.configure(xscrollcommand=hsb.set)

        # Intestazioni
        headings = {
            "ordine_id": "ID Ordine",
            "cliente": "Cliente",
            "data_inserimento": "Data Ordine",
            "data_consegna": "Data Consegna",
            "quantita": "Qtà",
            "stato": "Stato",
            "in_lavorazione": "In Lavorazione",
            "assemblati": "Assemblati"
        }

        for col, text in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=120, anchor='center')

        # Configurazione tag per colori
        self.tree.tag_configure("green", background="#d4edda")
        self.tree.tag_configure("orange", background="#ffe5b4")
        self.tree.tag_configure("red", background="#f8d7da")

        self.tree.bind("<Double-1>", self.apri_dettaglio)

    def _crea_pulsanti(self):
        """Crea i pulsanti di controllo."""
        btn_frame = tk.Frame(self, bg="#f7f1e1")
        btn_frame.grid(row=2, column=0, pady=5, sticky='w')

        btn_refresh = tk.Button(btn_frame, text="🔄 Aggiorna", command=self.carica_dati,
                                bg="#d8c3a5", font=("Segoe Print", 12, "bold"))
        btn_refresh.pack(side="left", padx=5)

    def carica_dati(self):
        """Carica tutti gli ordini in lavorazione."""
        self.tree.delete(*self.tree.get_children())

        # Raccogli tutti i dati
        righe = LavorazioneManager.get_ordini_in_lavorazione()

        # Raggruppa per ordine
        ordini = {}
        dettagli_ordini = {}

        for r in righe:
            ordine_id = r["ordine_id"]

            dettagli_ordini.setdefault(ordine_id, []).append({
                "progetto_id": r["progetto_id"],
                "quantita": r["quantita"],
                "assemblato": r["assemblato"]
            })

            if ordine_id not in ordini:
                ordini[ordine_id] = {
                    "cliente": r["cliente"],
                    "data_inserimento": r["data_inserimento"],
                    "data_consegna": r["data_consegna"],
                    "data_in_lavorazione": r["data_in_lavorazione"]
                }

        # Inserisci nel Treeview
        for ordine_id, info in ordini.items():
            progetti = dettagli_ordini[ordine_id]

            # Calcola stato assemblaggio
            stato_assemblaggio = self._calcola_stato_assemblaggio(progetti)

            stato_lavorazione = "🛠️ In lavorazione" if info["data_in_lavorazione"] else "❌ Non avviato"

            self.tree.insert("", "end", values=(
                ordine_id,
                info["cliente"],
                info["data_inserimento"][:10] if info["data_inserimento"] else "",
                info["data_consegna"][:10] if info["data_consegna"] else "",
                stato_assemblaggio["totale_quantita"],
                stato_lavorazione,
                info["data_in_lavorazione"] or "",
                stato_assemblaggio["testo"]
            ), tags=(stato_assemblaggio["colore"],))

    def _calcola_stato_assemblaggio(self, progetti):
        """Calcola lo stato di assemblaggio per un insieme di progetti."""
        tot_quantita = sum(p["quantita"] for p in progetti)
        tot_assemblati = sum(p["assemblato"] for p in progetti)

        if tot_assemblati >= tot_quantita:
            return {
                "totale_quantita": tot_quantita,
                "testo": "✅ Tutti",
                "colore": "green"
            }
        elif tot_assemblati > 0:
            return {
                "totale_quantita": tot_quantita,
                "testo": "🟠 Parziale",
                "colore": "orange"
            }
        else:
            return {
                "totale_quantita": tot_quantita,
                "testo": "❌ Nessuno",
                "colore": "red"
            }

    def apri_dettaglio(self, event):
        """Apre la finestra dettaglio per l'ordine selezionato."""
        item = self.tree.selection()
        if not item:
            return

        ordine_id = self.tree.item(item[0])["values"][0]
        DettaglioOrdineWindow(self, ordine_id)


class DettaglioOrdineWindow(tk.Toplevel):
    """Finestra di dettaglio per un ordine in lavorazione."""

    def __init__(self, parent, ordine_id):
        super().__init__(parent)
        self.parent = parent
        self.ordine_id = ordine_id

        self.title(f"Dettaglio Ordine #{ordine_id}")
        self.configure(bg="#f7f1e1")
        self.geometry("750x850")
        self.transient(parent)

        # 🔥 NON chiamare grab_set() qui - aspetta che la finestra sia visibile

        self.progetto_selezionato = None
        self._crea_interfaccia()
        self._carica_dati()
        self._centra_finestra()

        # 🔥 Dopo aver creato l'interfaccia e centrato, imposta grab
        self.after(100, self._set_grab)  # Ritardo di 100ms

    def _set_grab(self):
        """Imposta il grab in modo sicuro."""
        try:
            self.grab_set()
        except tk.TclError:
            # Se ancora non funziona, riprova dopo
            self.after(100, self._set_grab)

    def _crea_interfaccia(self):
        """Crea l'interfaccia della finestra."""
        # Intestazione
        tk.Label(self, text=f"Ordine ID: {self.ordine_id}",
                 font=("Segoe Print", 16, "bold"), bg="#f7f1e1").pack(pady=10)

        # Frame principale con scroll
        canvas = tk.Canvas(self, bg="#f7f1e1", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#f7f1e1")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        row = 0

        # Dati ordine
        self._crea_sezione_ordine(scroll_frame, row)
        row += 6

        # Aggiornamento assemblaggio
        self._crea_sezione_assemblaggio(scroll_frame, row)
        row += 1

        # Tabella progetti
        self._crea_tabella_progetti(scroll_frame, row)
        row += 2

        # Componenti mancanti
        self._crea_sezione_mancanti(scroll_frame, row)
        row += 2

        # Pulsante vendita
        self._crea_pulsante_vendita(scroll_frame, row)

    def _crea_sezione_ordine(self, parent, row):
        """Crea la sezione con i dati dell'ordine."""
        # Cliente
        tk.Label(parent, text="Cliente:", font=("Segoe UI", 11, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=2)
        self.lbl_cliente = tk.Label(parent, text="", bg="#f7f1e1", font=("Segoe UI", 11))
        self.lbl_cliente.grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # Date
        tk.Label(parent, text="Data Ordine:", font=("Segoe UI", 11, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=2)
        self.lbl_data_ordine = tk.Label(parent, text="", bg="#f7f1e1", font=("Segoe UI", 11))
        self.lbl_data_ordine.grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        tk.Label(parent, text="Data Consegna:", font=("Segoe UI", 11, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=2)
        self.lbl_data_consegna = tk.Label(parent, text="", bg="#f7f1e1", font=("Segoe UI", 11))
        self.lbl_data_consegna.grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # Prezzi (se presenti)
        tk.Label(parent, text="Totale Ordine:", font=("Segoe UI", 11, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=2)
        self.lbl_totale = tk.Label(parent, text="", bg="#f7f1e1", font=("Segoe UI", 11))
        self.lbl_totale.grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        tk.Label(parent, text="Acconto Versato:", font=("Segoe UI", 11, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, sticky="w", pady=2)
        self.lbl_acconto = tk.Label(parent, text="", bg="#f7f1e1", font=("Segoe UI", 11))
        self.lbl_acconto.grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # Data lavorazione
        self._crea_controllo_data_lavorazione(parent, row)

    def _crea_controllo_data_lavorazione(self, parent, row):
        """Crea il controllo per la data di inizio lavorazione."""
        frame = tk.Frame(parent, bg="#f7f1e1")
        frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="w")

        tk.Label(frame, text="In lavorazione (AAAA-MM-GG):",
                 font=("Segoe UI", 10), bg="#f7f1e1").pack(side="left")

        oggi = datetime.now().strftime("%Y-%m-%d")
        self.data_lavorazione_var = tk.StringVar(value=oggi)
        entry = tk.Entry(frame, textvariable=self.data_lavorazione_var, width=12)
        entry.pack(side="left", padx=5)

        tk.Button(frame, text="Salva", command=self._salva_data_lavorazione,
                  bg="#d8c3a5").pack(side="left", padx=5)

    def _crea_tabella_progetti(self, parent, row):
        """Crea la tabella dei progetti dell'ordine."""
        tk.Label(parent, text="Progetti Ordinati:", font=("Segoe UI", 12, "bold"),
                 bg="#f7f1e1").grid(row=row, column=0, columnspan=2, pady=(15, 5), sticky="w")
        row += 1

        # Treeview progetti
        self.tree_progetti = ttk.Treeview(
            parent,
            columns=("nome", "quantita", "assemblato", "prezzo_unitario", "prezzo_totale"),
            show="headings",
            height=6
        )

        headings = [
            ("nome", "Progetto", 200),
            ("quantita", "Qtà", 60),
            ("assemblato", "Assemblati", 80),
            ("prezzo_unitario", "Prezzo Unit.", 100),
            ("prezzo_totale", "Prezzo Tot.", 100)
        ]

        for col, text, width in headings:
            self.tree_progetti.heading(col, text=text)
            self.tree_progetti.column(col, width=width, anchor="center")

        self.tree_progetti.grid(row=row, column=0, columnspan=2, pady=5, sticky="nsew")
        self.tree_progetti.bind("<<TreeviewSelect>>", self._aggiorna_mancanti)

    def _crea_sezione_mancanti(self, parent, row):
        """Crea la sezione componenti mancanti."""
        tk.Label(parent, text="Componenti Mancanti:",
                 font=("Segoe UI", 12, "bold"), bg="#f7f1e1").grid(
                     row=row, column=0, columnspan=2, pady=(15, 5), sticky="w")
        row += 1

        self.listbox_mancanti = tk.Listbox(parent, height=6, width=70)
        self.listbox_mancanti.grid(row=row, column=0, columnspan=2, pady=5)

    def _crea_sezione_assemblaggio(self, parent, row):
        """Crea la sezione per aggiornare la quantità assemblata."""
        frame = tk.Frame(parent, bg="#f7f1e1")
        frame.grid(row=row, column=0, columnspan=2, pady=15, sticky="w")

        tk.Label(frame, text="Aggiorna quantità assemblata:",
                 font=("Segoe UI", 10), bg="#f7f1e1").pack(side="left")

        self.spin_assemblati = tk.Spinbox(frame, from_=0, to=999, width=5)
        self.spin_assemblati.pack(side="left", padx=5)

        tk.Button(frame, text="Salva", command=self._salva_assemblati,
                  bg="#d8c3a5").pack(side="left", padx=5)

    def _crea_pulsante_vendita(self, parent, row):
        """Crea il pulsante per vendere l'ordine."""
        self.btn_vendi = tk.Button(
            parent,
            text="💰 Consegna Ordine",
            command=self._vendi_ordine,
            bg="#a3d8c3",
            font=("Segoe Print", 12, "bold"),
            padx=20,
            pady=10
        )
        self.btn_vendi.grid(row=row, column=0, columnspan=2, pady=20)

    def _carica_dati(self):
        """Carica tutti i dati nella finestra."""
        from logic.lavorazione import LavorazioneManager
        from logic.ordini import OrdineManager  # 🔥 Importa anche questo

        # 🔥 PARTE 1: CARICA I DETTAGLI DELL'ORDINE usando OrdineManager
        dettagli = OrdineManager.get_ordine_dettaglio(self.ordine_id)

        if dettagli:
            self.lbl_cliente.config(text=dettagli["cliente"] or "")
            self.lbl_data_ordine.config(text=dettagli["data_inserimento"][:10] if dettagli["data_inserimento"] else "")
            self.lbl_data_consegna.config(text=dettagli["data_consegna"][:10] if dettagli["data_consegna"] else "")

            # Calcola totale sommando i prezzi dei progetti (o prendi dal dettaglio se presente)
            progetti_ordine = OrdineManager.get_progetti_ordinati(self.ordine_id)
            totale = sum(p["prezzo_totale"] for p in progetti_ordine)
            self.lbl_totale.config(text=f"€ {totale:.2f}")

            # Acconto (se presente nel dettaglio, altrimenti 0)
            acconto = dettagli.get("acconto", 0) or 0
            self.lbl_acconto.config(text=f"€ {acconto:.2f}")

            # Preimposta la data di lavorazione se presente
            if dettagli.get("data_in_lavorazione"):
                self.data_lavorazione_var.set(dettagli["data_in_lavorazione"][:10])
        else:
            # Se non ci sono dettagli, mostra valori di default
            self.lbl_cliente.config(text="N/D")
            self.lbl_data_ordine.config(text="N/D")
            self.lbl_data_consegna.config(text="N/D")
            self.lbl_totale.config(text="N/D")
            self.lbl_acconto.config(text="€ 0.00")

        # 🔥 PARTE 2: CARICA I PROGETTI DELL'ORDINE (CODICE ESISTENTE)
        progetti = LavorazioneManager.get_progetti_ordine(self.ordine_id)
        for p in progetti:
            # Usa progetto_ordinato_id come iid
            self.tree_progetti.insert("", "end", iid=str(p["progetto_ordinato_id"]), values=(
                p["nome"],
                p["quantita"],
                p["assemblato_effettivo"],
                f"€ {p['prezzo_unitario']:.2f}" if p.get('prezzo_unitario') else "N/D",
                f"€ {p['prezzo_totale']:.2f}" if p.get('prezzo_totale') else "N/D"
            ))

    def _salva_data_lavorazione(self):
        """Salva la data di inizio lavorazione."""
        val = self.data_lavorazione_var.get().strip()
        LavorazioneManager.aggiorna_data_lavorazione(self.ordine_id, val)
        self.parent.carica_dati()
        mostra_info("Salvato", "Data inizio lavorazione aggiornata!", parent=self)

    def _aggiorna_mancanti(self, event):
        """Aggiorna la lista dei componenti mancanti per il progetto selezionato."""
        self.listbox_mancanti.delete(0, tk.END)

        selected = self.tree_progetti.selection()
        if not selected:
            return

        # 🔥 selected[0] è l'ID del progetto_ordinato (che usiamo come iid nella treeview)
        progetto_ordinato_id = int(selected[0])

        from logic.lavorazione import LavorazioneManager
        mancanti = LavorazioneManager.get_componenti_mancanti(progetto_ordinato_id)

        if mancanti:
            for m in mancanti:
                data = m.get('data', '')
                if len(data) > 10:
                    self.listbox_mancanti.insert(tk.END,
                                                 f"{m['nome']} (-{m['quantita']}) [dal {data[:16]}]")
                else:
                    self.listbox_mancanti.insert(tk.END, f"{m['nome']} (-{m['quantita']})")
        else:
            self.listbox_mancanti.insert(tk.END, "✅ Nessun componente mancante per questo ordine")

    def _salva_assemblati(self):
        """Salva la quantità assemblata per il progetto selezionato."""
        selected = self.tree_progetti.selection()
        if not selected:
            mostra_attenzione("Attenzione", "Seleziona un progetto", parent=self)
            return

        progetto_ordinato_id = int(selected[0])
        nuova_qt = int(self.spin_assemblati.get())

        LavorazioneManager.aggiorna_assemblato(progetto_ordinato_id, nuova_qt)

        # Aggiorna la visualizzazione
        valori = list(self.tree_progetti.item(selected[0])["values"])
        valori[2] = nuova_qt
        self.tree_progetti.item(selected[0], values=valori)

        self.parent.carica_dati()
        mostra_info("Salvato", "Quantità assemblata aggiornata!", parent=self)

    def _vendi_ordine(self):
        """Apre il dialog di vendita per l'ordine completato."""
        from logic.lavorazione import VenditaOrdineManager

        # Prepara i dati per la vendita
        successo, msg, dati_vendita = VenditaOrdineManager.prepara_dati_per_vendita(self.ordine_id)

        if not successo:
            mostra_errore("Errore", msg, parent=self)
            return

        # Apri il dialog di vendita
        dialog = DialogVenditaOrdine(self, dati_vendita)
        self.wait_window(dialog)

        if not dialog or not dialog.result:
            return

        risultato = dialog.result

        # Qui processa la vendita effettiva
        self._processa_vendita_ordine(risultato)

    def _processa_vendita_ordine(self, risultato):
        """Processa la vendita dell'ordine direttamente in Venduti e aggiorna negozio."""
        print("\n" + "=" * 60)
        print("🔍 DEBUG VENDITA ORDINE")
        print("=" * 60)
        print(f"Risultato ricevuto: {risultato}")

        try:
            # Variabili per gestire il buono dopo la transazione principale
            buono_da_applicare = None
            sconto_da_applicare = 0
            vendita_ids_per_buono = []

            from logic.venduti import VendutiManager

            # Calcola proporzione per eventuale sconto globale
            totale_vendita = sum(item["prezzo_totale"] for item in risultato["items"])
            totale_finale = risultato.get("totale_finale", totale_vendita)
            proporzione = (totale_finale / totale_vendita) if totale_vendita else 1.0

            vendita_ids = []

            # 🔥 USA UNA SOLA CONNESSIONE PER TUTTO
            conn = get_connection()
            cur = conn.cursor()

            try:
                for i, item in enumerate(risultato["items"]):
                    prezzo_totale_scontato = round(item["prezzo_totale"] * proporzione, 2)
                    prezzo_unitario_scontato = round(item["prezzo_unitario"] * proporzione, 4)

                    # 🔥 PASSO 1: AGGIORNA TABELLA NEGOZIO
                    # Verifica se il progetto esiste già in negozio
                    cur.execute("""
                                SELECT id, disponibili, venduti
                                FROM negozio
                                WHERE progetto_id = ?
                                """, (item["progetto_id"],))
                    esistente = cur.fetchone()

                    if esistente:
                        # ✅ Progetto esiste: incrementa SOLO venduti
                        negozio_id, disponibili, venduti_attuali = esistente
                        nuovi_venduti = venduti_attuali + item["quantita"]

                        cur.execute("""
                                    UPDATE negozio
                                    SET venduti = ?
                                    WHERE id = ?
                                    """, (nuovi_venduti, negozio_id))

                        print(
                            f"   ✅ Incrementati venduti per progetto {item['progetto_id']}: {venduti_attuali} → {nuovi_venduti}")
                    else:
                        # ✅ Progetto non esiste: crea record con disponibili=0, venduti=quantita
                        cur.execute("SELECT nome FROM progetti WHERE id = ?", (item["progetto_id"],))
                        nome_progetto = cur.fetchone()[0]

                        data_inserimento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        cur.execute("""
                                    INSERT INTO negozio
                                    (progetto_id, nome_progetto_negozio, data_inserimento,
                                     prezzo_vendita, disponibili, venduti)
                                    VALUES (?, ?, ?, ?, 0, ?)
                                    """, (item["progetto_id"], nome_progetto, data_inserimento,
                                          prezzo_unitario_scontato, item["quantita"]))

                        print(
                            f"   ✅ Creato record in negozio per progetto {item['progetto_id']} con venduti={item['quantita']}")

                        # Ottieni l'ID appena inserito
                        negozio_id = cur.lastrowid

                    # 🔥 PASSO 2: REGISTRA IN VENDUTI (CON ORDINE_ID)
                    data_vendita = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur.execute("""
                                INSERT INTO venduti (negozio_id, cliente, quantita, prezzo_totale,
                                                     prezzo_unitario, note, nome, data_vendita, ordine_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (negozio_id,
                                      risultato["cliente"],
                                      item["quantita"],
                                      prezzo_totale_scontato,
                                      prezzo_unitario_scontato,
                                      f"Da ordine #{risultato['ordine_id']}",
                                      item["nome_visibile"],
                                      data_vendita,
                                      risultato["ordine_id"]))  # 🔥 ORDINE_ID SALVATO!

                    vendita_id = cur.lastrowid
                    if vendita_id:
                        vendita_ids.append(vendita_id)

                    print(
                        f"   ✅ Inserito vendita per {item['nome_visibile']} (ID: {vendita_id}, ordine_id: {risultato['ordine_id']})")

                # 🔥 PASSO 3: SEGNA ORDINE COME CONSEGNATO E AGGIORNA STATO PAGAMENTO
                data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                stato_pagamento = f"PAGATO {data_ora}"

                cur.execute("""
                            UPDATE ordini
                            SET consegnato      = 1,
                                stato_pagamento = ?
                            WHERE id = ?
                            """, (stato_pagamento, risultato["ordine_id"]))

                print(f"   ✅ Ordine {risultato['ordine_id']} segnato come consegnato")
                print(f"   ✅ Stato pagamento aggiornato: {stato_pagamento}")

                # 🔥 COMMIT FINALE
                conn.commit()
                print("   ✅ Transazione completata con successo")

            except Exception as e:
                conn.rollback()
                print(f"❌ Errore durante la transazione: {e}")
                raise
            finally:
                conn.close()

            # Applica buono se necessario (fuori dalla transazione principale)
            if risultato.get("buono_applicato") and vendita_ids and risultato.get("sconto", 0) > 0:
                from logic.buoni import BuonoManager

                buono_da_applicare = risultato["buono_applicato"]
                sconto_da_applicare = risultato["sconto"]
                vendita_ids_per_buono = vendita_ids

                success, msg = BuonoManager.applica_utilizzo(
                    buono_id=buono_da_applicare["id"],
                    importo_utilizzato=sconto_da_applicare,
                    vendita_id=vendita_ids_per_buono[0]
                )

                if success:
                    print(f"   ✅ Buono applicato: {msg}")
                else:
                    print(f"   ❌ Errore buono: {msg}")

            print("\n" + "=" * 60)
            print("✅ VENDITA COMPLETATA CON SUCCESSO")
            print("=" * 60)

            mostra_info("✅ Successo", "Ordine venduto e registrato con successo!", parent=self.parent)
            self.parent.carica_dati()

        except Exception as e:
            print("\n❌" + "=" * 60)
            print("❌ ERRORE DURANTE LA VENDITA")
            print("=" * 60)
            print(f"Errore: {e}")
            import traceback
            traceback.print_exc()
            mostra_errore("Errore", str(e), parent=self.parent)

    def _centra_finestra(self):
        """Centra la finestra rispetto al parent."""
        self.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


class DialogVenditaOrdine(tk.Toplevel):
    """Dialog per la vendita di un ordine completato (simile a quello del negozio)."""

    def __init__(self, parent, dati_ordine):
        super().__init__(parent)
        self.parent = parent
        self.dati_ordine = dati_ordine
        self.items = dati_ordine["items"]
        self.cliente = dati_ordine["cliente"]
        self.acconto = dati_ordine["acconto"]
        self.result = None
        self.buono_applicato = None

        self.title(f"Consegna Ordine #{dati_ordine['ordine_id']} - {self.cliente}")
        self.configure(bg="#f7f1e1")
        self.geometry("950x650")
        self.transient(parent)
        self.grab_set()

        self._crea_interfaccia()
        self._centra_finestra()

    def _crea_interfaccia(self):
        """Crea l'interfaccia del dialog."""
        # Intestazione cliente
        tk.Label(self, text=f"Cliente: {self.cliente}", bg="#f7f1e1",
                 font=("Segoe UI", 12, "bold")).pack(pady=(8, 2))

        # Info acconto
        if self.acconto > 0:
            frame_acconto = tk.Frame(self, bg="#f7f1e1")
            frame_acconto.pack(fill="x", padx=10, pady=5)

            tk.Label(frame_acconto, text=f"Acconto già versato: € {self.acconto:.2f}",
                     bg="#f7f1e1", font=("Segoe UI", 10, "bold"), fg="green").pack(side="left")

            tk.Label(frame_acconto, text="(verrà detratto dal totale)",
                     bg="#f7f1e1", font=("Segoe UI", 9, "italic"), fg="gray").pack(side="left", padx=10)

        # Frame per il codice sconto
        frame_sconto = tk.Frame(self, bg="#f7f1e1")
        frame_sconto.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_sconto, text="Codice sconto:", bg="#f7f1e1",
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))

        self.codice_sconto_var = tk.StringVar()
        self.entry_codice = tk.Entry(frame_sconto, textvariable=self.codice_sconto_var, width=15)
        self.entry_codice.pack(side="left", padx=5)

        btn_verifica = tk.Button(frame_sconto, text="Applica",
                                 command=self._verifica_codice_sconto,
                                 bg="#e0e0e0")
        btn_verifica.pack(side="left", padx=5)

        self.label_sconto = tk.Label(frame_sconto, text="", bg="#f7f1e1",
                                     font=("Segoe UI", 9, "italic"))
        self.label_sconto.pack(side="left", padx=10)

        # Area scrollabile per i prodotti
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

        # Righe prodotti (con prezzi già impostati)
        self.row_widgets = []
        for item in self.items:
            self._crea_riga_prodotto(scroll_frame, item)

        # Pulsanti in basso
        self._crea_pulsanti_dialog()

    def _crea_intestazioni(self, parent):
        """Crea la riga di intestazione."""
        header = tk.Frame(parent, bg="#f7f1e1")
        header.pack(fill="x", pady=(0, 2))

        headings = [
            ("Nome oggetto", 48),
            ("Disponibili", 10),
            ("Quantità", 10),
            ("Prezzo unitario (€)", 16),
            ("Prezzo totale (€)", 16)
        ]

        for txt, w in headings:
            tk.Label(header, text=txt, font=("Segoe UI", 10, "bold"),
                     bg="#f7f1e1", width=w).pack(side="left", padx=6)

    def _crea_riga_prodotto(self, parent, item):
        """Crea una riga per un prodotto."""
        row = tk.Frame(parent, bg="#fffafa", bd=1, relief="solid")
        row.pack(fill="x", pady=4, padx=2)

        # Nome
        lbl_nome = tk.Label(row, text=item["nome_visibile"], anchor="w",
                            bg="#fffafa", width=48)
        lbl_nome.pack(side="left", fill="x", expand=True, padx=(6, 4))

        # Disponibili (quantità dell'ordine)
        lbl_disp = tk.Label(row, text=str(item["disponibili"]), width=10, bg="#fffafa")
        lbl_disp.pack(side="left", padx=6)

        # Quantità (spinbox, default = disponibili)
        q_var = tk.IntVar(value=item["disponibili"])
        sb = tk.Spinbox(row, from_=1, to=item["disponibili"], textvariable=q_var, width=6)
        sb.pack(side="left", padx=6)

        # Prezzo unitario (modificabile)
        p_unit_var = tk.DoubleVar(value=item["prezzo_vendita"])
        entry_prezzo_u = tk.Entry(row, textvariable=p_unit_var, width=12, justify="center")
        entry_prezzo_u.pack(side="left", padx=6)

        # Prezzo totale (modificabile)
        p_tot_var = tk.DoubleVar(value=item["prezzo_totale"])
        entry_prezzo_tot = tk.Entry(row, textvariable=p_tot_var, width=12, justify="center")
        entry_prezzo_tot.pack(side="left", padx=6)

        # Flag per tracciare modifiche
        user_edited = {"unit": False, "total": False}

        def on_unit_edit(e):
            user_edited["unit"] = True

        entry_prezzo_u.bind("<KeyRelease>", on_unit_edit)

        def on_total_edit(e):
            user_edited["total"] = True

        entry_prezzo_tot.bind("<KeyRelease>", on_total_edit)

        # Callback per aggiornamento
        def on_qty_change(*a):
            try:
                q = q_var.get()
                p_unit = p_unit_var.get()

                if not user_edited["total"]:
                    nuovo_tot = p_unit * q
                    p_tot_var.set(round(nuovo_tot, 2))

                self._aggiorna_totali()
            except Exception:
                pass

        def on_unit_change(*a):
            try:
                q = q_var.get()
                p_unit = p_unit_var.get()

                if not user_edited["total"]:
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
            "progetto_id": item["progetto_id"],
            "nome_visibile": item["nome_visibile"],
            "disponibili": item["disponibili"],
            "q_var": q_var,
            "p_unit_var": p_unit_var,
            "p_tot_var": p_tot_var,
            "user_edited": user_edited
        })

    def _crea_pulsanti_dialog(self):
        """Crea i pulsanti in fondo al dialog."""
        bottom = tk.Frame(self, bg="#f7f1e1")
        bottom.pack(fill="x", padx=10, pady=8)

        frame_totali = tk.Frame(bottom, bg="#f7f1e1")
        frame_totali.pack(side="left", fill="x", expand=True)

        # Totale lordo
        tk.Label(frame_totali, text="Totale lordo: €", bg="#f7f1e1",
                 font=("Segoe UI", 9)).pack(side="left", padx=5)
        self.totale_lordo_var = tk.DoubleVar(value=self._calcola_totale())
        tk.Label(frame_totali, textvariable=self.totale_lordo_var,
                 bg="#f7f1e1", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)

        # Acconto
        if self.acconto > 0:
            tk.Label(frame_totali, text="Acconto: €", bg="#f7f1e1",
                     font=("Segoe UI", 9)).pack(side="left", padx=(20, 5))
            self.acconto_var = tk.DoubleVar(value=self.acconto)
            tk.Label(frame_totali, textvariable=self.acconto_var,
                     bg="#f7f1e1", font=("Segoe UI", 9, "bold"), fg="green").pack(side="left", padx=5)

        # Sconto
        tk.Label(frame_totali, text="Sconto: €", bg="#f7f1e1",
                 font=("Segoe UI", 9)).pack(side="left", padx=(20, 5))
        self.sconto_var = tk.DoubleVar(value=0.0)
        tk.Label(frame_totali, textvariable=self.sconto_var,
                 bg="#f7f1e1", font=("Segoe UI", 9, "bold"), fg="red").pack(side="left", padx=5)

        # Totale netto
        tk.Label(frame_totali, text="Totale da pagare: €", bg="#f7f1e1",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(20, 5))
        self.totale_netto_var = tk.DoubleVar(value=self._calcola_totale() - self.acconto)
        tk.Label(frame_totali, textvariable=self.totale_netto_var,
                 bg="#f7f1e1", font=("Segoe UI", 10, "bold"), fg="#3366cc").pack(side="left", padx=5)

        # Pulsanti
        frame_btn = tk.Frame(bottom, bg="#f7f1e1")
        frame_btn.pack(side="right")

        tk.Button(frame_btn, text="Conferma Vendita", command=self.on_confirm,
                  bg="#90EE90", font=("Segoe UI", 10, "bold")).pack(side="left", padx=6)
        tk.Button(frame_btn, text="Annulla", command=self.on_cancel,
                  bg="#f0f0f0").pack(side="left", padx=6)

        # Aggiorna totali quando cambiano i valori
        for rw in self.row_widgets:
            rw["p_tot_var"].trace_add("write", lambda *a: self._aggiorna_totali())
            rw["q_var"].trace_add("write", lambda *a: self._aggiorna_totali())

    def _calcola_totale(self):
        """Calcola il totale corrente."""
        tot = 0.0
        for rw in self.row_widgets:
            tot += rw["p_tot_var"].get()
        return round(tot, 2)

    def _aggiorna_totali(self):
        """Aggiorna i totali."""
        totale_lordo = self._calcola_totale()
        self.totale_lordo_var.set(totale_lordo)

        # Applica sconto se presente
        sconto = self.sconto_var.get()
        totale_con_sconto = totale_lordo - sconto

        # Detrai acconto
        totale_netto = totale_con_sconto - self.acconto
        self.totale_netto_var.set(max(0, round(totale_netto, 2)))

    def _verifica_codice_sconto(self):
        """Verifica il codice sconto inserito."""
        codice = self.codice_sconto_var.get().strip()
        if not codice:
            return

        from logic.buoni import BuonoManager
        valido, msg, buono = BuonoManager.valida_buono(codice)

        if not valido:
            messagebox.showerror("Codice non valido", msg, parent=self)
            self.label_sconto.config(text=msg, fg="red")
            self.codice_sconto_var.set("")
            if hasattr(self, 'buono_applicato'):
                delattr(self, 'buono_applicato')
            self.sconto_var.set(0)
            self._aggiorna_totali()
            return

        # Calcola sconto
        totale_lordo = self._calcola_totale()
        if buono['tipo'] == 'REGALO':
            sconto = min(buono['valore_residuo'], totale_lordo)
            self.label_sconto.config(text=f"✓ Buono regalo €{buono['valore_residuo']:.2f}", fg="green")
        else:
            percentuale = buono['valore_originale']
            sconto = totale_lordo * (percentuale / 100)
            self.label_sconto.config(text=f"✓ Sconto {percentuale:.0f}%", fg="green")

        self.buono_applicato = {
            'id': buono['id'],
            'codice': buono['codice'],
            'tipo': buono['tipo'],
            'valore_residuo': buono['valore_residuo']
        }
        self.sconto_var.set(round(sconto, 2))
        self._aggiorna_totali()

    def on_confirm(self):
        """Conferma la vendita."""
        risultati = []
        for rw in self.row_widgets:
            q = rw["q_var"].get()
            if q <= 0:
                continue

            risultati.append({
                "progetto_id": rw["progetto_id"],
                "nome_visibile": rw["nome_visibile"],
                "quantita": q,
                "prezzo_unitario": rw["p_unit_var"].get(),
                "prezzo_totale": rw["p_tot_var"].get()
            })

        self.result = {
            "cliente": self.cliente,
            "ordine_id": self.dati_ordine["ordine_id"],
            "items": risultati,
            "acconto": self.acconto,
            "sconto": self.sconto_var.get(),
            "buono_applicato": getattr(self, 'buono_applicato', None),
            "totale_finale": self.totale_netto_var.get()
        }
        self.grab_release()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

    def _centra_finestra(self):
        self.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")