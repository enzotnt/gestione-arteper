# All'inizio del file, dopo gli import
import sys
import os


import requests

def ping_utilizzo():
    try:
        requests.get(
            "https://api.counterapi.dev/v1/enzos-team/arteper_avvii/up",
            timeout=2
        )
    except:
        pass

def setup_environment():
    """Configura l'ambiente per l'EXE"""
    if getattr(sys, 'frozen', False):
        # Siamo in un EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # Siamo in sviluppo
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Vai nella cartella base
    os.chdir(base_path)
    
    # Crea le cartelle necessarie
    cartelle = ["database", "icons", "export", "backup"]
    for cartella in cartelle:
        percorso = os.path.join(base_path, cartella)
        if not os.path.exists(percorso):
            os.makedirs(percorso)
    
    # Crea config.json se non esiste
    config_path = os.path.join(base_path, "config.json")
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding='utf-8') as f:
            f.write("{}")
    
    return base_path

# CHIAMA SUBITO LA FUNZIONE
BASE_PATH = setup_environment()
# main_con_avvio.py - Versione con gestione cartelle integrata
import os
import sys

# =============================================================================
# GESTIONE CARTELLE ALL'AVVIO
# =============================================================================
def crea_struttura_cartelle():
    """Crea le cartelle necessarie se non esistono"""
    # Determina dove siamo (sviluppo o EXE)
    if getattr(sys, 'frozen', False):
        # Siamo in un EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # Siamo in svilupp
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Vai nella cartella base
    os.chdir(base_path)
    
    cartelle = ["database", "icons", "export", "backup"]
    for cartella in cartelle:
        if not os.path.exists(cartella):
            try:
                os.makedirs(cartella)
            except:
                pass
    
    # Crea config.json se non esiste
    if not os.path.exists("config.json"):
        try:
            with open("config.json", "w", encoding='utf-8') as f:
                f.write("{}")
        except:
            pass

# Chiama subito la funzione
crea_struttura_cartelle()

# =============================================================================
# ORA COPIA TUTTO IL TUO MAIN.PY ORIGINALE QUI SOTTO
# =============================================================================

# [INCORPORA QUI TUTTO IL CONTENUTO DEL TUO main.py ORIGINALE]
# Copia da "import tkinter as tk" fino alla fine del file

# Esempio di inizio del tuo codice originale:


import tkinter as tk
from tkinter import ttk
from db.database import init_db
from datetime import datetime
from PIL import Image, ImageTk
import os
from utils.backup_db import backup_database, ripristina_backup
from db.database import init_db
from gui.config_dialog import ConfigDialog


from gui.magazzino_gui import TabMagazzino
from gui.progetti_gui import TabProgetti
from gui.venduti_gui import TabVenduti
from gui.negozio_gui import TabNegozio
from gui.mercatini_gui import TabMercatini  # Aggiungi questa linea
from gui.ordini_gui import TabOrdini
from gui.lavorazione_gui import TabLavorazione
from gui.spese_gui import TabSpese
from gui.bilancio_gui import TabBilancio
from gui.buoni_gui import TabBuoni

def main():
    init_db()

    # Ping statistica utilizzo
    ping_utilizzo()


    root = tk.Tk()
    root.title("Gestione arTEper - Versione 3.5")
    root.geometry("1800x1100")
    root.configure(bg="#f7f1e1")

    # Configurazione del sistema grid per il root
    root.grid_rowconfigure(1, weight=1)  # La riga centrale si espande
    root.grid_columnconfigure(0, weight=1)  # Unica colonna si espande

    # Imposta l'icona
    icon_path = os.path.join("icons", "icona_app.png")
    icon_img = Image.open(icon_path)
    icon_tk = ImageTk.PhotoImage(icon_img)
    root.iconphoto(True, icon_tk)

    # ------------------- STILE -------------------
    style = ttk.Style()
    style.theme_use("clam")
    style.configure('TNotebook', background='#f7f1e1', borderwidth=0)
    style.configure('TNotebook.Tab',
                  background='#d8c3a5',
                  font=('Segoe Print', 14, 'bold'),
                  padding=[20, 10],
                  foreground='black')
    style.map('TNotebook.Tab',
            background=[('selected', '#e4b389')],
            expand=[("selected", [1, 1, 1, 0])])

    # ------------------- HEADER -------------------
    header_frame = tk.Frame(root, bg="#f7f1e1")
    header_frame.grid(row=0, column=0, sticky="ew", pady=10)

    # Logo sinistro
    img_path = os.path.join("icons", "icona_prog.png")
    img = Image.open(img_path).resize((64, 64), Image.Resampling.LANCZOS)
    logo_img = ImageTk.PhotoImage(img)

    tk.Label(header_frame, image=logo_img, bg="#f7f1e1").grid(row=0, column=0, padx=5)
    header_frame.grid_columnconfigure(1, weight=1)  # Centro espandibile

    # Titolo centrale
    tk.Label(header_frame,
            text="   - Gestione arTEper -   ",
            font=("Segoe Print", 24, "bold"),
            fg="#7b4b1d",
            bg="#f7f1e1").grid(row=0, column=1)

    # Logo destro (stessa immagine)
    tk.Label(header_frame, image=logo_img, bg="#f7f1e1").grid(row=0, column=2, padx=5)

    # ------------------- CONTENUTO PRINCIPALE -------------------
    content_frame = tk.Frame(root, bg="#f7f1e1")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,15))
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_columnconfigure(0, weight=1)

    notebook = ttk.Notebook(content_frame, style='TNotebook')
    notebook.grid(row=0, column=0, sticky="nsew")

    # Aggiungi tutte le schede
    tabs = [
        ("📦 Magazzino", TabMagazzino),
        ("🛠️ Progetti", TabProgetti),
        ("🛍️ Negozio", TabNegozio),
        ("🎪 Mercatini", TabMercatini),
        ("🎁 Buoni Regalo", TabBuoni),  # <-- NUOVO TAB
        ("📋 Ordini", TabOrdini),
        ("🛠️ In Lavorazione", TabLavorazione),
        ("✅ Venduti", TabVenduti),
        ("💸 Spese", TabSpese),
        ("📈 Bilancio", TabBilancio),
    ]

    for text, tab_class in tabs:
        notebook.add(tab_class(notebook), text=text)

    # ------------------- FOOTER -------------------
    footer_frame = tk.Frame(root, bg="#f7f1e1", height=60)  # Altezza aumentata
    footer_frame.grid(row=2, column=0, sticky="ew")

    # Linea separatrice con più spazio
    ttk.Separator(root, orient='horizontal').grid(row=2, column=0, sticky="ew", pady=(0,30))

    # Contenuto footer con più spazio verticale
    tk.Label(footer_frame,
            text="By: Enzo TnT",
            font=("Segoe Print", 12, "italic"),  # Font leggermente più grande
            fg="#7b4b1d",
            bg="#f7f1e1").pack(side='left', padx=15, pady=8)  # Aggiunto pady

    data_ora_label = tk.Label(footer_frame,
                            font=("Segoe Print", 16),  # Font più grande
                            fg="#7b4b1d",
                            bg="#f7f1e1")
    data_ora_label.pack(side='right', padx=15, pady=8)  # Aggiunto pady

    def aggiorna_orario():
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data_ora_label.config(text=f"Data/Ora: {now}")
        data_ora_label.after(1000, aggiorna_orario)

    aggiorna_orario()

    def apri_config():
        from gui.config_dialog import ConfigDialog
        ConfigDialog(root)

    # Pulsante Configurazione (NUOVO)
    btn_config = tk.Button(
        footer_frame,
        text="⚙️ Configurazione",
        font=("Segoe Print", 12, "bold"),
        bg="#d8c3a5",
        fg="black",
        relief="raised",
        command=apri_config  # <-- Ora funziona!
    )
    btn_config.pack(side="right", padx=15, pady=8)

    btn_backup = tk.Button(
        footer_frame,
        text="📁 Backup Database",
        font=("Segoe Print", 12, "bold"),
        bg="#d8c3a5",
        fg="black",
        relief="raised",
        command=lambda: backup_database(root)
    )
    btn_backup.pack(side="right", padx=15, pady=8)


    btn_ripristina = tk.Button(
        footer_frame,
        text="♻️ Ripristina Backup",
        font=("Segoe Print", 12, "bold"),
        bg="#e4b389",
        fg="black",
        relief="raised",
        command=lambda: ripristina_backup(root)
    )
    btn_ripristina.pack(side="right", padx=15, pady=8)






    # Assicura che il layout sia calcolato correttamente
    root.update_idletasks()

    # Imposta una dimensione minima basata sul contenuto
    root.minsize(root.winfo_width(), 600)

    root.mainloop()

if __name__ == "__main__":
    main()
