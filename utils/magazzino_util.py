# utils/magazzino_util.py
import tkinter as tk
from tkinter import messagebox
from db.database import get_connection
from logic.magazzino import aggiungi_scorte, sincronizza_componenti_mancanti
from utils.gui_utils import DialogComponente
import os


def azione_doppio_click(self, event):
    """Mostra l'immagine del componente al doppio click."""
    selected = self.tree.selection()
    if not selected:
        return

    item_id = selected[0]
    immagine_percorso = self.percorsi_immagini.get(item_id)

    if not immagine_percorso or not os.path.isfile(immagine_percorso):
        messagebox.showinfo("Nessuna immagine", "Nessuna immagine trovata per questo componente.")
        return

    # Usa la funzione centralizzata da gui_utils
    from utils.gui_utils import mostra_immagine_zoom
    mostra_immagine_zoom(self, immagine_percorso, "Immagine componente")

def on_doppio_click(tab, tree, refresh_func, comp_col=0, nome_col=1,
                      id_from_iid=False, qty_col=None):
    """Funzione per aggiornare le scorte usando DialogComponente.

    - `qty_col` permette di passare l'indice di una colonna che contiene una
      quantità predefinita (utile nella vista componenti mancanti/ordini).
      In tal caso il costo di default viene calcolato come
      `quantità * costo_unitario_corrente`.
    """
    selected = tree.focus()
    if not selected:
        return

    values = tree.item(selected, "values")
    try:
        if id_from_iid:
            comp_id = int(selected)  # iid è l'ID
        else:
            comp_id = int(values[comp_col])
        nome = values[nome_col] if nome_col < len(values) else "Componente"
    except (IndexError, ValueError):
        messagebox.showerror("Errore", "ID componente non trovato.")
        return

    # Recupera informazioni correnti per il componente
    conn = get_connection()
    cursor = conn.cursor()

    # costo unitario attuale (serve per calcolare valore iniziale quando
    # `qty_col` è impostato)
    cursor.execute("SELECT costo_unitario FROM magazzino WHERE id = ?", (comp_id,))
    row = cursor.fetchone()
    costo_attuale = float(row[0]) if row and row[0] is not None else 0.0

    # storicizziamo l'ultimo movimento per default di fornitore/note/costo
    cursor.execute("""
                   SELECT fornitore, note, quantita, costo_totale
                   FROM movimenti_magazzino
                   WHERE componente_id = ?
                   ORDER BY data DESC, id DESC LIMIT 1
                   """, (comp_id,))
    result = cursor.fetchone()
    conn.close()

    # Valori predefiniti base
    fornitore_attuale = result[0] if result and result[0] else ""
    note_attuali = result[1] if result and result[1] else ""

    if qty_col is not None:
        # cerco di estrarre la quantità direttamente dalla riga, altrimenti
        # ricado sul valore storico o su 1
        try:
            quantita_predefinita = float(values[qty_col])
        except Exception:
            quantita_predefinita = float(result[2]) if result and result[2] else 1.0
        costo_predefinito = quantita_predefinita * costo_attuale
    else:
        quantita_predefinita = float(result[2]) if result and result[2] else 1.0
        costo_predefinito = float(result[3]) if result and result[3] else 0.0

    dialog = DialogComponente(
        parent=tab,
        titolo=f"Aggiungi scorte - {nome}",
        modalita=DialogComponente.MODALITA_SCORTE,
        nome_componente=nome,
        quantita_max=999999,
        fornitore_default=fornitore_attuale,
        note_default=note_attuali,
        quantita_default=quantita_predefinita,
        costo_default=costo_predefinito,
        costo_unitario_attuale=costo_attuale
    )

    tab.wait_window(dialog)

    if dialog.risultato:
        dati = dialog.risultato
        aggiungi_scorte(comp_id, dati['quantita'], dati['costo_totale'],
                        dati['fornitore'], dati['note'])
        sincronizza_componenti_mancanti(comp_id, dati['quantita'])
        messagebox.showinfo("Successo", f"Scorte aggiornate per '{nome}'.")
        refresh_func()