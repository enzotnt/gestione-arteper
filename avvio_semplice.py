# avvio_semplice.py - Versione SEMPLICISSIMA che funziona
import os
import sys
import subprocess

def main():
    # Determina dove siamo
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
    
    # Avvia main.py come processo separato
    try:
        # Usa lo stesso python che sta eseguendo questo script
        python_exe = sys.executable
        subprocess.run([python_exe, "main.py"])
    except Exception as e:
        # Se c'è errore, mostra una finestra
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Errore", f"Impossibile avviare main.py:\n{str(e)}")
            root.destroy()
        except:
            pass

if __name__ == "__main__":
    main()