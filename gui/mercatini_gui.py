# gui/mercatini_gui.py

import tkinter as tk

from tkinter import ttk, messagebox
from utils.helpers import mostra_info

from logic.mercatini import carica_progetti_mercatino
from utils.gui_utils import ordina_colonna_treeview



class TabMercatini(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg="#f7f1e1")
        self.stato_ordinamento = {'colonna': None, 'ascendente': True}

        self._crea_tabella_mercatino()

    def ordina_per_colonna(self, colonna):
        """Ordina la tabella per la colonna selezionata."""
        if colonna == "Prezzo":
            # Raccogli i dati
            items = [(self.tree.set(k, colonna), k) for k in self.tree.get_children('')]

            # Funzione per classificare e convertire i valori
            def chiave_ordinamento(valore):
                try:
                    # Prova a convertire in float
                    num = float(valore.replace("€", "").replace(",", ".").strip())
                    return (0, num)  # I numeri vengono prima (0)
                except ValueError:
                    # Se non è un numero, restituisci la stringa in minuscolo
                    return (1, str(valore).lower())  # Le stringhe dopo (1)

            # Ordina usando la chiave personalizzata
            items.sort(key=lambda x: chiave_ordinamento(x[0]),
                       reverse=not self.stato_ordinamento['ascendente'])

            # Aggiorna lo stato
            self.stato_ordinamento['colonna'] = colonna
            self.stato_ordinamento['ascendente'] = not self.stato_ordinamento['ascendente']

            # Riordina le righe
            for index, (_, k) in enumerate(items):
                self.tree.move(k, '', index)
        else:
            # Per le altre colonne usa la funzione standard

            self.stato_ordinamento = ordina_colonna_treeview(
                self.tree,
                colonna,
                self.stato_ordinamento
            )

    def _crea_tabella_mercatino(self):
        """Crea la tabella per visualizzare i progetti del mercatino."""
        # Pulisci eventuale contenuto esistente
        for widget in self.winfo_children():
            widget.destroy()

        # Frame principale
        main_frame = tk.Frame(self, bg="#f7f1e1")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Intestazione
        header_frame = tk.Frame(main_frame, bg="#f7f1e1")
        header_frame.pack(fill="x", pady=5)

        tk.Label(header_frame, text="📋 PROGETTI PER MERCATINO",
                 font=("Segoe Print", 16, "bold"), bg="#f7f1e1", fg="#7b4b1d").pack(side="left")

        # Pulsanti
        btn_frame = tk.Frame(header_frame, bg="#f7f1e1")
        btn_frame.pack(side="right")

        tk.Button(btn_frame, text="➕ Nuovo", command=self._nuovo_progetto,
                  bg="#90EE90", font=("Segoe UI", 10)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️ Modifica", command=self._modifica_selezionato,
                  bg="#FFD700", font=("Segoe UI", 10)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="🗑️ Elimina", command=self._elimina_selezionato,
                  bg="#d9534f", fg="white", font=("Segoe UI", 10)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="📄 Stampa Lista", command=self._stampa_lista,
                  bg="#deb887", font=("Segoe UI", 10)).pack(side="left", padx=2)

        columns = ("Nome Progetto", "Prezzo", "Quantità", "Note")

        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)

        # 🔥 MODIFICATO: Intestazioni con ordinamento
        self.tree.heading("Nome Progetto", text="Nome Progetto",
                          command=lambda: self.ordina_per_colonna("Nome Progetto"))
        self.tree.heading("Prezzo", text="Prezzo",
                          command=lambda: self.ordina_per_colonna("Prezzo"))
        self.tree.heading("Quantità", text="Quantità",
                          command=lambda: self.ordina_per_colonna("Quantità"))
        self.tree.heading("Note", text="Note",
                          command=lambda: self.ordina_per_colonna("Note"))

        self.tree.column("Nome Progetto", width=300, anchor="w")
        self.tree.column("Prezzo", width=100, anchor="center")
        self.tree.column("Quantità", width=80, anchor="center")
        self.tree.column("Note", width=350, anchor="w")

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._modifica_selezionato)

        # Carica dati
        self._carica_dati_mercatino()

    def _carica_dati_mercatino(self):
        """Carica i dati nella tabella dal file."""
        progetti = carica_progetti_mercatino()

        for prog in progetti:
            # 🔴 NON convertire in float, mantieni come stringa
            self.tree.insert("", "end", values=(
                prog["nome"],
                prog["prezzo"],  # <-- Già stringa dal JSON
                prog["quantita"],  # <-- Già stringa dal JSON
                prog["note"]
            ))

    def _raccogli_tutti_progetti(self):
        """Raccoglie tutti i progetti dalla tabella per il salvataggio."""
        progetti = []
        for item in self.tree.get_children():
            valori = self.tree.item(item)['values']
            progetti.append({
                "nome": valori[0],
                "prezzo": valori[1],  # <-- Salva come stringa, non convertire in float
                "quantita": valori[2],  # <-- Salva come stringa, non convertire in int
                "note": valori[3]
            })
        return progetti

    def aggiungi_progetti(self, progetti):
        """Aggiunge progetti ricevuti dal tab Negozio."""
        print(f"🔵 aggiungi_progetti chiamato con {len(progetti)} progetti")

        for prog in progetti:
            print(f"   - {prog['nome']} | prezzo: {prog['prezzo']} | qta: {prog['quantita']}")
            # 🔴 Non formattare il prezzo, usa direttamente la stringa
            self.tree.insert("", "end", values=(
                prog["nome"],
                prog["prezzo"],  # <-- Già stringa
                prog["quantita"],  # <-- Già stringa
                prog["note"]
            ))

        print("🟡 Chiamo _salva_progetti()...")
        self._salva_progetti()
        print("🟢 _salva_progetti() completato")

        mostra_info("Completato",
                    f"{len(progetti)} progetti aggiunti al tab Mercatini!",
                    parent=self)

    def _salva_progetti(self):
        """Salva i progetti correnti su file."""
        print("=" * 50)
        print("📝 _salva_progetti: inizio")

        try:
            progetti = self._raccogli_tutti_progetti()
            print(f"📊 Progetti raccolti: {len(progetti)}")

            if not progetti:
                print("⚠️ Nessun progetto da salvare!")
                return False

            from logic.mercatini import salva_progetti_mercatino
            print("💾 Chiamo salva_progetti_mercatino...")

            risultato = salva_progetti_mercatino(progetti)
            print(f"📤 Risultato da salva_progetti_mercatino: {risultato} (tipo: {type(risultato)})")

            if risultato:
                print("✅ Salvataggio completato con successo!")
            else:
                print("❌ Salvataggio fallito!")

            print("🟢 _salva_progetti() completato")
            print("=" * 50)

            return risultato

        except Exception as e:
            print(f"💥 ERRORE in _salva_progetti: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _nuovo_progetto(self):
        """Aggiunge un nuovo progetto manualmente."""
        dialog = tk.Toplevel(self)
        dialog.title("Nuovo Progetto Mercatino")
        dialog.geometry("500x300")
        dialog.configure(bg="#f7f1e1")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Nome Progetto:", bg="#f7f1e1").pack(pady=5)
        nome_var = tk.StringVar()
        tk.Entry(dialog, textvariable=nome_var, width=50).pack(pady=5)

        tk.Label(dialog, text="Prezzo:", bg="#f7f1e1").pack(pady=5)  # <-- Senza (€)
        prezzo_var = tk.StringVar()  # <-- StringVar, può contenere qualsiasi testo
        tk.Entry(dialog, textvariable=prezzo_var, width=20).pack(pady=5)

        tk.Label(dialog, text="Quantità:", bg="#f7f1e1").pack(pady=5)
        qta_var = tk.StringVar(value="1")  # <-- Anche quantità come StringVar
        tk.Entry(dialog, textvariable=qta_var, width=10).pack(pady=5)  # <-- Entry invece di Spinbox

        tk.Label(dialog, text="Note:", bg="#f7f1e1").pack(pady=5)
        note_var = tk.StringVar()
        tk.Entry(dialog, textvariable=note_var, width=50).pack(pady=5)

        btn_frame = tk.Frame(dialog, bg="#f7f1e1")
        btn_frame.pack(pady=20)

        def conferma():
            self.tree.insert("", "end", values=(
                nome_var.get(),
                prezzo_var.get(),  # <-- Testo libero, nessuna conversione
                qta_var.get(),  # <-- Testo libero
                note_var.get()
            ))
            self._salva_progetti()
            dialog.destroy()

        tk.Button(btn_frame, text="Conferma", command=conferma,
                  bg="#90EE90").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Annulla", command=dialog.destroy,
                  bg="#f0f0f0").pack(side="left", padx=5)

    def _modifica_selezionato(self, event=None):
        """Modifica il progetto selezionato."""
        print(f"🔍 _modifica_selezionato chiamato con event={event}")

        # Determina quale item modificare
        item_id = None

        if event:  # Doppio clic
            print(f"   📍 Doppio clic - coordinate: x={event.x}, y={event.y}")
            # Identifica la riga cliccata
            item_id = self.tree.identify_row(event.y)
            print(f"   🆔 Item identificato: {item_id}")

            if not item_id:
                print("   ❌ Nessun item identificato!")
                return

            # Seleziona l'item per sicurezza
            self.tree.selection_set(item_id)
            print(f"   ✅ Item selezionato: {item_id}")

        else:  # Pulsante
            print(f"   🔘 Chiamato da pulsante")
            sel = self.tree.selection()
            print(f"   📋 Selezione corrente: {sel}")

            if not sel:
                messagebox.showwarning("Attenzione", "Seleziona un progetto da modificare.", parent=self)
                return
            item_id = sel[0]
            print(f"   ✅ Item selezionato dal pulsante: {item_id}")

        # Ottieni i valori
        print(f"   📊 Recupero valori per item {item_id}")
        valori = self.tree.item(item_id, 'values')
        print(f"   📋 Valori recuperati: {valori}")

        if not valori or len(valori) < 4:
            print(f"   ❌ Valori insufficienti: {valori}")
            return

        print(f"   ✅ Valori OK, apro dialog di modifica")

        # Dialog di modifica
        dialog = tk.Toplevel(self)
        dialog.title("Modifica Progetto Mercatino")
        dialog.geometry("500x300")
        dialog.configure(bg="#f7f1e1")
        dialog.transient(self)

        # 🔴 NON chiamare grab_set() immediatamente
        # Aspetta che la finestra sia visualizzata

        # Frame per il contenuto
        main_frame = tk.Frame(dialog, bg="#f7f1e1")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Campi
        tk.Label(main_frame, text="Nome Progetto:", bg="#f7f1e1", anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        nome_entry = tk.Entry(main_frame, width=40)
        nome_entry.grid(row=0, column=1, pady=5, padx=5)
        nome_entry.insert(0, valori[0])

        tk.Label(main_frame, text="Prezzo:", bg="#f7f1e1", anchor="w").grid(row=1, column=0, sticky="w", pady=5)
        prezzo_entry = tk.Entry(main_frame, width=20)
        prezzo_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        prezzo_entry.insert(0, valori[1])

        tk.Label(main_frame, text="Quantità:", bg="#f7f1e1", anchor="w").grid(row=2, column=0, sticky="w", pady=5)
        qta_entry = tk.Entry(main_frame, width=10)
        qta_entry.grid(row=2, column=1, pady=5, padx=5, sticky="w")
        qta_entry.insert(0, valori[2])

        tk.Label(main_frame, text="Note:", bg="#f7f1e1", anchor="w").grid(row=3, column=0, sticky="w", pady=5)
        note_entry = tk.Entry(main_frame, width=40)
        note_entry.grid(row=3, column=1, pady=5, padx=5)
        note_entry.insert(0, valori[3])

        # Pulsanti
        btn_frame = tk.Frame(main_frame, bg="#f7f1e1")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

        def conferma():
            self.tree.item(item_id, values=(
                nome_entry.get(),
                prezzo_entry.get(),
                qta_entry.get(),
                note_entry.get()
            ))
            self._salva_progetti()
            dialog.destroy()

        tk.Button(btn_frame, text="Conferma", command=conferma,
                  bg="#90EE90", padx=20, pady=5).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Annulla", command=dialog.destroy,
                  bg="#f0f0f0", padx=20, pady=5).pack(side="left", padx=5)

        # 🔴 Chiama grab_set() DOPO aver creato tutti i widget
        # e usa after per assicurarti che la finestra sia visibile
        def set_grab():
            try:
                dialog.grab_set()
                print(f"✅ grab_set eseguito con successo")
            except Exception as e:
                print(f"⚠️ grab_set fallito: {e}")

        dialog.after(100, set_grab)  # Aspetta 100ms prima di fare grab_set

        print(f"✅ Dialog aperto, grab_set programmato")

    def _mostra_dialog_modifica(self, item_id, valori):
        """Mostra il dialog di modifica per un item specifico."""
        dialog = tk.Toplevel(self)
        dialog.title("Modifica Progetto Mercatino")
        dialog.geometry("500x300")
        dialog.configure(bg="#f7f1e1")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Nome Progetto:", bg="#f7f1e1").pack(pady=5)
        nome_var = tk.StringVar(value=valori[0])
        tk.Entry(dialog, textvariable=nome_var, width=50).pack(pady=5)

        tk.Label(dialog, text="Prezzo:", bg="#f7f1e1").pack(pady=5)
        prezzo_var = tk.StringVar(value=valori[1])
        tk.Entry(dialog, textvariable=prezzo_var, width=20).pack(pady=5)

        tk.Label(dialog, text="Quantità:", bg="#f7f1e1").pack(pady=5)
        qta_var = tk.StringVar(value=valori[2])
        tk.Entry(dialog, textvariable=qta_var, width=10).pack(pady=5)

        tk.Label(dialog, text="Note:", bg="#f7f1e1").pack(pady=5)
        note_var = tk.StringVar(value=valori[3])
        tk.Entry(dialog, textvariable=note_var, width=50).pack(pady=5)

        btn_frame = tk.Frame(dialog, bg="#f7f1e1")
        btn_frame.pack(pady=20)

        def conferma():
            self.tree.item(item_id, values=(
                nome_var.get(),
                prezzo_var.get(),
                qta_var.get(),
                note_var.get()
            ))
            self._salva_progetti()
            dialog.destroy()

        tk.Button(btn_frame, text="Conferma", command=conferma,
                  bg="#90EE90").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Annulla", command=dialog.destroy,
                  bg="#f0f0f0").pack(side="left", padx=5)

    def _elimina_selezionato(self):
        """Elimina il progetto selezionato."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un progetto da eliminare.", parent=self)
            return

        if messagebox.askyesno("Conferma", "Eliminare il progetto selezionato?", parent=self):
            for item in sel:
                self.tree.delete(item)
            self._salva_progetti()

    def _stampa_lista(self):
        """Stampa la lista dei progetti rispettando l'ordinamento corrente."""
        # Raccogli i progetti nell'ordine corrente della tabella
        progetti_ordinati = []
        for item_id in self.tree.get_children():
            valori = self.tree.item(item_id)['values']
            progetti_ordinati.append({
                "nome": valori[0],
                "prezzo": valori[1],
                "quantita": valori[2],
                "note": valori[3]
            })

        # Chiama la funzione di stampa passando i progetti già ordinati
        from logic.mercatini import stampa_prodotto
        stampa_prodotto(self, progetti_ordinati)