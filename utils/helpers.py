import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
from contextlib import contextmanager
from db.database import get_connection
# =============================================================================
# NUOVE FUNZIONI DA AGGIUNGERE A HELPERS.PY
# =============================================================================


# AGGIUNGI QUESTE FUNZIONI A utils/helpers.py



@contextmanager
def db_cursor(commit=False, show_errors=True, parent=None):
    """
    Context manager per operazioni database.
    Utilizza le funzioni di messaggio già presenti in helpers.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        if show_errors:
            # Usa le funzioni già esistenti
            if hasattr(parent, 'winfo_exists') and parent.winfo_exists():
                mostra_errore("Errore Database", str(e))
            else:
                mostra_errore("Errore Database", str(e))
        else:
            raise
    finally:
        if conn:
            conn.close()

def conferma_e_esegui(titolo, messaggio, funzione, *args, **kwargs):
    """
    Chiede conferma e se positiva esegue una funzione.
    Gestisce automaticamente gli errori.
    """
    if chiedi_conferma(titolo, messaggio):
        try:
            risultato = funzione(*args, **kwargs)
            mostra_info("Operazione completata", "Operazione eseguita con successo.")
            return risultato
        except Exception as e:
            mostra_errore("Errore", f"Errore durante l'operazione: {e}")
            return None

def format_currency(value):
    """Formatta un valore come valuta."""
    return f"€ {value:.2f}"

def format_date(date_str, format_in='%Y-%m-%d %H:%M:%S', format_out='%d/%m/%Y'):
    """Formatta una data da un formato all'altro."""
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, format_in)
        return dt.strftime(format_out)
    except:
        return date_str

def safe_float_conversion(value, default=0.0):
    """Converte in float in modo sicuro."""
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(',', '.').strip()
            if not value:
                return default
        return float(value)
    except (ValueError, TypeError):
        return default

def calcola_totale_componenti(componenti):
    """
    Calcola totale da lista componenti.
    componenti: lista di tuple (quantita, costo_unitario, moltiplicatore)
    """
    return sum(q * cu * m for q, cu, m in componenti if q and cu and m)

def esegui_con_indicatore(parent, funzione, titolo="Elaborazione in corso...", *args, **kwargs):
    """
    Esegue una funzione mostrando un indicatore di caricamento.
    Utile per operazioni lunghe.
    """
    # Crea finestra di caricamento
    loading = tk.Toplevel(parent)
    loading.title("")
    loading.transient(parent)
    loading.grab_set()

    tk.Label(loading, text=titolo, padx=20, pady=10).pack()
    loading.update()

    try:
        risultato = funzione(*args, **kwargs)
        loading.destroy()
        return risultato
    except Exception as e:
        loading.destroy()
        mostra_errore("Errore", str(e))
        return None

def treeview_sort_column(treeview, col, reverse, column_types=None):
    data = [(treeview.set(k, col), k) for k in treeview.get_children('')]

    if column_types and col in column_types:
        if column_types[col] == 'numeric':
            data = [(float(item[0].replace(',', '.')) if item[0] else 0, item[1]) for item in data]
        elif column_types[col] == 'date':
            from datetime import datetime
            try:
                data = [(datetime.strptime(item[0], '%Y-%m-%d'), item[1]) for item in data]
            except ValueError:
                # In caso serva gestire anche date in formato diverso in futuro
                data = [(item[0], item[1]) for item in data]

    data.sort(reverse=reverse)
    for index, (val, k) in enumerate(data):
        treeview.move(k, '', index)

    treeview.heading(col, command=lambda: treeview_sort_column(treeview, col, not reverse, column_types))

# ... (treeview_sort_column già esistente)

def chiedi_conferma(titolo, messaggio, parent=None):
    """Mostra una finestra di dialogo di conferma."""
    if parent:
        return messagebox.askyesno(titolo, messaggio, parent=parent)
    else:
        return messagebox.askyesno(titolo, messaggio)

# In utils/helpers.py, modifica la funzione mostra_errore:

def mostra_errore(titolo, messaggio, parent=None):
    """Mostra una finestra di dialogo di errore."""
    if parent:
        messagebox.showerror(titolo, messaggio, parent=parent)
    else:
        messagebox.showerror(titolo, messaggio)

def mostra_info(titolo, messaggio, parent=None):
    """Mostra una finestra di dialogo informativa."""
    if parent:
        messagebox.showinfo(titolo, messaggio, parent=parent)
    else:
        messagebox.showinfo(titolo, messaggio)

def mostra_attenzione(titolo, messaggio, parent=None):
    """Mostra una finestra di dialogo di avvertimento."""
    if parent:
        messagebox.showwarning(titolo, messaggio, parent=parent)
    else:
        messagebox.showwarning(titolo, messaggio)

def salva_csv(dati, intestazioni, titolo_finestra="Esporta CSV"):
    """
    Funzione generica per salvare dati in un file CSV.
    Mostra una finestra di dialogo per scegliere il percorso.
    """
    percorso = filedialog.asksaveasfilename(
        title=titolo_finestra,
        defaultextension=".csv",
        filetypes=[("File CSV", "*.csv")]
    )
    if not percorso:
        return False
    try:
        with open(percorso, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(intestazioni)
            writer.writerows(dati)
        messagebox.showinfo("Esportazione riuscita", f"Dati esportati in:\n{percorso}")
        return True
    except Exception as e:
        messagebox.showerror("Errore", f"Errore durante l'esportazione:\n{e}")
        return False

def carica_immagine_percorso(percorso, size=(32, 32)):
    """Carica un'immagine da un percorso e la ridimensiona."""
    if percorso and os.path.isfile(percorso):
        try:
            img = Image.open(percorso)
            img = img.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None
    return None

def crea_finestra_zoom_immagine(parent, percorso_immagine):
    """Crea una nuova finestra con un'immagine zoomabile."""
    if not percorso_immagine or not os.path.isfile(percorso_immagine):
        mostra_attenzione("Attenzione", "Nessuna immagine trovata per questo componente.")
        return

    try:
        img_originale = Image.open(percorso_immagine)
        zoom_ratio = [1.0]

        popup = tk.Toplevel(parent)
        popup.title("Immagine")
        popup.geometry("500x500")

        # ... (il codice del canvas, scrollbar, zoom e pan)
        # Lo copiamo qui dentro, esattamente come era in mostra_immagine

    except Exception as e:
        mostra_errore("Errore", f"Errore durante il caricamento dell'immagine: {e}")

# Nota: per crea_finestra_zoom_immagine, dovresti spostare tutto il codice
# della vecchia funzione mostra_immagine qui dentro.
