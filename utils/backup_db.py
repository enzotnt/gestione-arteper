import shutil
import os
import json
from datetime import datetime
from tkinter import filedialog, messagebox

CONFIG_PATH = os.path.join("utils", "backup_config.json")
DB_PATH = os.path.join("database", "gestione.db")

def salva_cartella_backup(percorso):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"last_backup_dir": percorso}, f)

def carica_cartella_backup():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                data = json.load(f)
                return data.get("last_backup_dir", os.getcwd())
            except json.JSONDecodeError:
                return os.getcwd()
    return os.getcwd()

def backup_database(root):
    initial_dir = carica_cartella_backup()

    folder_selected = filedialog.askdirectory(
        title="Scegli cartella di destinazione backup",
        initialdir=initial_dir
    )

    if not folder_selected:
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(folder_selected, backup_filename)
        shutil.copy2(DB_PATH, backup_path)

        salva_cartella_backup(folder_selected)

        messagebox.showinfo("Backup completato", f"Backup salvato in:\n{backup_path}")
    except Exception as e:
        messagebox.showerror("Errore", f"Errore durante il backup:\n{str(e)}")

def ripristina_backup(root):
    initial_dir = carica_cartella_backup()

    file_backup = filedialog.askopenfilename(
        title="Seleziona un file di backup",
        filetypes=[("Database files", "*.db")],
        initialdir=initial_dir
    )

    if not file_backup:
        return

    conferma = messagebox.askyesno(
        "Conferma Ripristino",
        f"Vuoi davvero ripristinare il backup:\n{os.path.basename(file_backup)}?"
    )

    if not conferma:
        return

    try:
        # Backup di sicurezza prima di sovrascrivere
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        sicurezza_path = os.path.join("database", f"gestione_backup_prima_del_ripristino_{timestamp}.db")
        shutil.copy2(DB_PATH, sicurezza_path)

        shutil.copy2(file_backup, DB_PATH)

        salva_cartella_backup(os.path.dirname(file_backup))

        messagebox.showinfo("Ripristino completato", "Ripristino completato con successo.\nRiavvia l'applicazione.")
    except Exception as e:
        messagebox.showerror("Errore", f"Errore durante il ripristino:\n{str(e)}")
