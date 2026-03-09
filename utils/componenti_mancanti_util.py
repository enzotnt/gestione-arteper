# utils/componenti_mancanti_util.py

import tkinter as tk
from tkinter import ttk
from utils.helpers import db_cursor, mostra_info, mostra_errore
from logic.magazzino import aggiungi_scorte
from utils.magazzino_util import on_doppio_click


def apri_componenti_mancanti(master):
    """
    Apre una finestra popup con la lista completa di tutti i componenti mancanti.
    """
    try:
        # Verifica che master esista ancora
        if not master.winfo_exists():
            print("Errore: master non esiste")
            return None

        # Crea la finestra popup
        popup = tk.Toplevel(master)
        popup.title("📋 Componenti Mancanti - Panoramica Generale")
        popup.geometry("1000x500")
        popup.configure(bg="#f7f1e1")

        # Forza la creazione della finestra
        popup.update_idletasks()

        # Assicurati che la finestra sia visibile
        if not popup.winfo_exists():
            print("Errore: popup non creato correttamente")
            return None

        # Intestazione
        header_frame = tk.Frame(popup, bg="#f7f1e1")
        header_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(header_frame, text="📋 COMPONENTI MANCANTI",
                font=("Segoe UI", 14, "bold"), bg="#f7f1e1", fg="#5a3e1b").pack(side="left")

        # Pulsante aggiorna
        btn_refresh = tk.Button(header_frame, text="🔄 Aggiorna",
                               command=lambda: carica_componenti(tree, popup),
                               bg="#deb887", font=("Segoe UI", 10))
        btn_refresh.pack(side="right", padx=5)

        # Frame per la treeview
        tree_frame = tk.Frame(popup, bg="#f7f1e1")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Treeview con scrollbar
        container = ttk.Frame(tree_frame)
        container.pack(fill="both", expand=True)

        tree = ttk.Treeview(container, columns=("componente", "totale", "progetti", "ultima"), show="headings")

        # Scrollbar
        v_scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        h_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Configura colonne
        tree.heading("componente", text="Componente")
        tree.heading("totale", text="Totale Mancante")
        tree.heading("progetti", text="Progetti Coinvolti")
        tree.heading("ultima", text="Ultima Rilevazione")

        tree.column("componente", width=250, anchor="w")
        tree.column("totale", width=120, anchor="center")
        tree.column("progetti", width=400, anchor="w")
        tree.column("ultima", width=150, anchor="center")

        # Bind doppio click
        # quando apriamo il dialog dal pannello componenti mancanti vogliamo
        # preimpostare la quantità con il totale mancante (colonna 1).
        tree.bind("<Double-1>", lambda e: on_doppio_click(
            master, tree, lambda: carica_componenti(tree, popup),
            comp_col=0, nome_col=0, id_from_iid=True, qty_col=1
        ))

        # Pulsanti in basso
        bottom_frame = tk.Frame(popup, bg="#f7f1e1")
        bottom_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(bottom_frame,
                text="💡 Doppio click per aggiungere scorte",
                font=("Segoe UI", 9, "italic"), bg="#f7f1e1", fg="gray").pack(side="left")

        tk.Button(bottom_frame, text="Chiudi", command=popup.destroy,
                 bg="#deb887", font=("Segoe UI", 10)).pack(side="right", padx=5)

        # Carica i dati
        carica_componenti(tree, popup)

        # Centra la finestra
        popup.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - popup.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")

        # Imposta modalità in modo sicuro
        popup.transient(master.winfo_toplevel())
        popup.after(100, lambda: safe_grab_set(popup))

        return popup

    except Exception as e:
        print(f"Errore in apri_componenti_mancanti: {e}")
        import traceback
        traceback.print_exc()
        return None


def safe_grab_set(window):
    """Imposta grab_set in modo sicuro."""
    try:
        if window.winfo_exists():
            window.grab_set()
    except:
        pass


def carica_componenti(tree, parent_window):
    """Carica i dati dei componenti mancanti."""
    try:
        # Pulisci la treeview
        for item in tree.get_children():
            tree.delete(item)

        with db_cursor() as cur:
            # 🔥 QUERY CORRETTA - senza secondo argomento in DISTINCT
            cur.execute("""
                        SELECT m.id,
                               m.nome,
                               SUM(cm.quantita_mancante),
                               COUNT(DISTINCT cm.progetto_id),
                               GROUP_CONCAT(DISTINCT p.nome) as progetti,
                               MAX(cm.data_rilevamento)
                        FROM componenti_mancanti cm
                                 JOIN magazzino m ON cm.componente_id = m.id
                                 JOIN progetti p ON cm.progetto_id = p.id
                        GROUP BY m.id, m.nome
                        ORDER BY SUM(cm.quantita_mancante) DESC
                        """)

            rows = cur.fetchall()

            if not rows:
                tree.insert("", tk.END, values=(
                    "Nessun componente mancante", "0", "", ""
                ))
                return

            for row in rows:
                componente_id, nome, totale, num_progetti, progetti, ultima = row

                # Formatta la data
                if ultima and len(ultima) > 10:
                    ultima = ultima[:16]

                # 🔥 Sostituisci le virgole con ", " per una migliore leggibilità
                if progetti:
                    progetti = progetti.replace(",", ", ")

                # Trunca progetti se troppo lungo
                if len(progetti) > 50:
                    progetti = progetti[:50] + "..."

                tree.insert("", tk.END, iid=str(componente_id), values=(
                    nome,
                    f"{totale:.2f}",
                    f"{progetti} ({num_progetti} progetti)",
                    ultima or "N/D"
                ))

    except Exception as e:
        print(f"Errore in carica_componenti: {e}")
        if parent_window.winfo_exists():
            from tkinter import messagebox
            messagebox.showerror("Errore", f"Errore nel caricamento dati: {e}", parent=parent_window)


