# logic/mercatini.py

import os
import re
import json
import traceback
from utils.helpers import mostra_info, mostra_errore
from config.config import config
from logic.progetti import Progetto
from logic import magazzino
from utils.mercatini_pdf import esporta_mercatini_pdf
import tkinter as tk
from tkcalendar import DateEntry
from tkinter import filedialog, messagebox
from datetime import datetime




# File per salvare i progetti del mercatino
MERCATINO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mercatino_progetti.json")

print(f"⚙️ MERCATINO_FILE = {MERCATINO_FILE}")


# =============================================================================
# FUNZIONE 1: PER NEGOZIO (progetti già in vendita)
# =============================================================================
def aggiungi_progetti_a_mercatino(progetti_selezionati):
    """
    Usata da: TabNegozio
    Prepara progetti che sono già in negozio (hanno disponibilità)
    """
    progetti_con_dettagli = []

    for prog in progetti_selezionati:
        progetto_id = prog["progetto_id"]

        # Carica il progetto con la classe Progetto che calcola il prezzo
        progetto_obj = Progetto(carica_da_id=progetto_id)

        # Calcola prezzo dinamicamente
        prezzo_calcolato = progetto_obj.calcola_prezzo()
        prezzo = round(prezzo_calcolato, 1)

        progetti_con_dettagli.append({
            "progetto_id": progetto_id,
            "nome": progetto_obj.nome,
            "prezzo": prezzo,
            "quantita": 1,  # Default
            "note": progetto_obj.note if progetto_obj.note else ""
        })

    return progetti_con_dettagli


# =============================================================================
# FUNZIONE 2: PER PROGETTI (progetti "grezzi")
# =============================================================================
def prepara_progetto_da_progetti(progetto_id, quantita=1):
    """
    Usata da: TabProgetti
    Prepara un progetto direttamente dalla tabella progetti
    """


    progetto_obj = Progetto(carica_da_id=progetto_id)
    prezzo = round(progetto_obj.calcola_prezzo(), 1)

    return {
        "progetto_id": progetto_id,
        "nome": progetto_obj.nome,
        "prezzo": prezzo,
        "quantita": quantita,
        "note": progetto_obj.note or ""
    }


# =============================================================================
# FUNZIONE 3: PER MAGAZZINO (componenti)
# =============================================================================
def prepara_componente_per_mercatino(componente_id, quantita=1):
    """
    Usata da: TabMagazzino
    Prepara un componente del magazzino per il mercatino
    """

    # NOTA: Dovrai implementare questo metodo in Magazzino se non esiste
    componente = magazzino.get_componente_by_id(componente_id)
    if not componente:
        return None

    prezzo = round(componente["costo_unitario"], 1)

    return {
        "componente_id": componente_id,
        "nome": f"[MAT] {componente['nome']}",  # Tag per distinguere
        "prezzo": prezzo,
        "quantita": quantita,
        "note": componente.get("note", ""),
        "tipo": "componente"  # Campo per identificare il tipo
    }


# =============================================================================
# FUNZIONI DI SALVATAGGIO (già esistenti)
# =============================================================================
def carica_progetti_mercatino():
    """Carica i progetti attualmente nel mercatino dal file JSON."""
    print(f"📂 Cerco file: {MERCATINO_FILE}")
    if os.path.exists(MERCATINO_FILE):
        try:
            with open(MERCATINO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📊 Dati caricati: {len(data)} progetti")
                return data
        except Exception as e:
            print(f"❌ Errore nel caricamento: {e}")
            return []
    return []


def salva_progetti_mercatino(progetti):
    """Salva i progetti nel mercatino su file JSON."""
    try:
        print(f"💾 Salvo in: {MERCATINO_FILE}")
        print(f"📦 Progetti da salvare: {len(progetti)}")

        directory = os.path.dirname(MERCATINO_FILE)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(MERCATINO_FILE, 'w', encoding='utf-8') as f:
            json.dump(progetti, f, indent=4, ensure_ascii=False)

        print(f"✅ File salvato con successo!")
        return True
    except Exception as e:
        print(f"❌ Errore nel salvataggio: {e}")
        traceback.print_exc()
        return False


def stampa_prodotto(parent, progetti_ordinati=None):
    """
    Esporta in PDF l'elenco prodotti con dialog personalizzato.
    Se progetti_ordinati è fornito, usa quelli (già ordinati).
    Altrimenti li carica dal file JSON.
    """
    import tkinter as tk
    from tkcalendar import DateEntry
    from tkinter import filedialog, messagebox
    import re
    import os
    from datetime import datetime
    from config.config import config
    from utils.helpers import mostra_info, mostra_errore

    # Recupera i dati anagrafici dal config
    anagrafica = config.get("anagrafica")

    # 🔴 Recupera la cartella di default per i PDF
    cartella_default = config.get("mercati", "cartella_pdf_default", default="")
    if not cartella_default or not os.path.exists(cartella_default):
        cartella_default = os.path.expanduser("~")  # Home directory come fallback

    # Recupera ultimi valori inseriti
    ultima_citta = config.get("mercati", "ultima_citta", default="")
    ultima_data = config.get("mercati", "ultima_data", default="")

    # Crea dialog personalizzato
    dialog = tk.Toplevel(parent)
    dialog.title("Dettagli Mercatino")
    dialog.geometry("400x250")
    dialog.configure(bg="#f7f1e1")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    # Variabili
    citta_var = tk.StringVar(value=ultima_citta)
    data_var = tk.StringVar()

    # Frame principale
    main_frame = tk.Frame(dialog, bg="#f7f1e1", padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    # Città
    tk.Label(main_frame, text="Città / Luogo:", bg="#f7f1e1",
             font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
    tk.Entry(main_frame, textvariable=citta_var, width=30,
             font=("Segoe UI", 10)).grid(row=0, column=1, pady=5, padx=5)

    # Data con calendario
    tk.Label(main_frame, text="Data mercatino:", bg="#f7f1e1",
             font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)

    data_entry = DateEntry(
        main_frame,
        width=15,
        background='darkblue',
        foreground='white',
        borderwidth=2,
        date_pattern='dd/mm/yyyy',
        font=("Segoe UI", 10)
    )
    data_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")

    # Imposta data predefinita se presente
    if ultima_data:
        try:
            data_default = datetime.strptime(ultima_data, "%d/%m/%Y")
            data_entry.set_date(data_default)
        except:
            pass

    # Anteprima nome file
    preview_frame = tk.Frame(main_frame, bg="#e8e0d0", relief="sunken", bd=1)
    preview_frame.grid(row=2, column=0, columnspan=2, pady=20, sticky="ew")

    tk.Label(preview_frame, text="Nome file:", bg="#e8e0d0",
             font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=5, pady=(5, 0))

    preview_label = tk.Label(preview_frame, text="", bg="#e8e0d0",
                             font=("Segoe UI", 9, "italic"))
    preview_label.pack(anchor="w", padx=5, pady=(0, 5))

    def aggiorna_anteprima(*args):
        citta = citta_var.get().strip()
        data = data_entry.get()
        if citta and data:
            preview_label.config(text=f"{citta} - {data}.pdf")
        elif citta:
            preview_label.config(text=f"{citta}.pdf")
        elif data:
            preview_label.config(text=f"{data}.pdf")
        else:
            preview_label.config(text="(nome file non definito)")

    citta_var.trace_add("write", aggiorna_anteprima)
    data_entry.bind("<<DateEntrySelected>>", aggiorna_anteprima)
    aggiorna_anteprima()  # Chiamata iniziale

    # Pulsanti
    btn_frame = tk.Frame(main_frame, bg="#f7f1e1")
    btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

    risultato = {"citta": None, "data": None, "confermato": False}

    def conferma():
        citta = citta_var.get().strip()
        data = data_entry.get()

        if not citta:
            messagebox.showwarning("Attenzione", "Inserisci il nome della città/luogo.", parent=dialog)
            return
        if not data:
            messagebox.showwarning("Attenzione", "Seleziona una data.", parent=dialog)
            return

        # Salva per prossima volta
        config.set("mercati", "ultima_citta", citta)
        config.set("mercati", "ultima_data", data)

        risultato["citta"] = citta
        risultato["data"] = data
        risultato["confermato"] = True
        dialog.destroy()

    def annulla():
        dialog.destroy()

    tk.Button(btn_frame, text="Conferma", command=conferma,
              bg="#90EE90", font=("Segoe UI", 10, "bold"), padx=20).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Annulla", command=annulla,
              bg="#f0f0f0", font=("Segoe UI", 10), padx=20).pack(side="left", padx=5)

    # Centra la finestra
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    # Aspetta che l'utente chiuda il dialog
    parent.wait_window(dialog)

    if not risultato["confermato"]:
        return

    citta = risultato["citta"]
    data = risultato["data"]
    luogo_data = f"{citta} - {data}"

    # Preleva i dati dal config
    prefill_nome = anagrafica.get("nome_cognome", "Pinco")
    prefill_tessera = anagrafica.get("tessera", "004185H00008")
    prefill_rilasciato = anagrafica.get("rilasciato_il", "09/07/2024")
    prefill_comune = anagrafica.get("comune", "Comune di comune")

    # Genera nome file suggerito
    clean = re.sub(r'[^A-Za-z0-9_\-\s/]', '', luogo_data)
    clean = clean.strip().replace(" ", "_").replace("/", "-")
    suggested_filename = f"{clean}.pdf"

    # Usa la cartella di default nel dialog di salvataggio
    initial_dir = cartella_default
    initial_file = suggested_filename

    save_path = filedialog.asksaveasfilename(
        title="Salva elenco mercatino",
        defaultextension=".pdf",
        filetypes=[("PDF file", "*.pdf"), ("All files", "*.*")],
        initialdir=initial_dir,
        initialfile=initial_file,
        parent=parent
    )
    if not save_path:
        return

    try:
        from utils.mercatini_pdf import esporta_mercatini_pdf

        output_dir = os.path.dirname(save_path)
        filename = os.path.basename(save_path)

        # 🔥 Se non sono stati passati progetti ordinati, caricali dal file JSON
        if progetti_ordinati is None:
            from logic.mercatini import carica_progetti_mercatino
            progetti_ordinati = carica_progetti_mercatino()

        out = esporta_mercatini_pdf(
            output_dir=output_dir,
            filename=filename,
            luogo_data_mercatino=luogo_data,
            prefilled_nome_cognome=prefill_nome,
            prefilled_tessera=prefill_tessera,
            prefilled_rilasciato_il=prefill_rilasciato,
            prefilled_comune=prefill_comune,
            include_totals=True,
            orientamento_landscape=True,
            progetti=progetti_ordinati  # <-- Passa i progetti ordinati!
        )

        mostra_info("Stampa creata", f"File PDF creato:\n{out}", parent=parent)

        # Apri il PDF
        _apri_pdf(out, parent)

        return out

    except Exception as e:
        import traceback
        traceback.print_exc()
        mostra_errore("Errore esportazione", f"Si è verificato un errore:\n{e}", parent=parent)
        return None


def _apri_pdf(percorso, parent):
    """Apre il PDF con il programma predefinito."""
    import subprocess
    import sys
    import os

    try:
        if sys.platform == 'win32':
            os.startfile(percorso)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', percorso])
        else:  # linux
            subprocess.run(['xdg-open', percorso])
    except Exception as e:
        mostra_errore("Errore", f"Impossibile aprire il PDF:\n{e}", parent=parent)


def _apri_pdf(percorso, parent):
    """Apre il PDF con il programma predefinito."""
    import subprocess
    import sys
    import os

    try:
        if sys.platform == 'win32':
            os.startfile(percorso)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', percorso])
        else:  # linux
            subprocess.run(['xdg-open', percorso])
    except Exception as e:
        mostra_errore("Errore", f"Impossibile aprire il PDF:\n{e}", parent=parent)















