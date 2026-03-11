# avvio.py - Gestisce la creazione delle cartelle e avvia il gestionale
import os
import sys
import importlib.util
import traceback

def crea_struttura_cartelle():
    """Crea le cartelle necessarie se non esistono"""
    # Determina dove siamo (sviluppo o EXE)
    if getattr(sys, 'frozen', False):
        # Siamo in un EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # Siamo in sviluppo
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Ci spostiamo nella cartella giusta
    os.chdir(base_path)
    
    cartelle_necessarie = [
        "database",
        "icons", 
        "export",
        "backup"
    ]
    
    # Crea le cartelle
    for cartella in cartelle_necessarie:
        percorso = os.path.join(base_path, cartella)
        if not os.path.exists(percorso):
            try:
                os.makedirs(percorso)
            except Exception:
                pass  # Ignora errori di creazione
    
    # Crea config.json se non esiste
    config_path = os.path.join(base_path, "config.json")
    if not os.path.exists(config_path):
        try:
            with open(config_path, "w", encoding='utf-8') as f:
                f.write("{}")
        except Exception:
            pass  # Ignora errori di creazione
    
    return base_path

def avvia_gestionale(base_path):
    """Avvia il gestionale (main.py)"""
    try:
        # Costruisce il percorso completo di main.py
        main_path = os.path.join(base_path, "main.py")
        
        if not os.path.exists(main_path):
            # Se non trova main.py, mostra un messagebox di errore
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Errore", f"File main.py non trovato in:\n{main_path}")
                root.destroy()
            except:
                pass
            return
        
        # Carica il modulo main.py
        spec = importlib.util.spec_from_file_location("__main__", main_path)
        main_module = importlib.util.module_from_spec(spec)
        sys.modules["__main__"] = main_module
        spec.loader.exec_module(main_module)
        
    except Exception as e:
        # In caso di errore, mostra un messagebox con l'errore
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            error_msg = f"Errore durante l'avvio:\n{str(e)}\n\n{traceback.format_exc()}"
            messagebox.showerror("Errore", error_msg)
            root.destroy()
        except:
            pass

if __name__ == "__main__":
    try:
        base_path = crea_struttura_cartelle()
        avvia_gestionale(base_path)
    except Exception as e:
        # Errore fatale, mostra messagebox se possibile
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Errore Fatale", str(e))
            root.destroy()
        except:
            pass