# utils/gui_utils.py

import tkinter as tk
from tkinter import ttk, messagebox
from utils.helpers import treeview_sort_column
from PIL import Image, ImageTk

def crea_finestra_con_treeview(parent, titolo, colonne, dati, column_types=None):
    """
    Crea una finestra popup con una Treeview popolata con dati.
    colonne: lista di tuple (nome_colonna, testo_intestazione)
    dati: lista di tuple/valori da inserire
    column_types: dizionario con il tipo per l'ordinamento (opzionale)
    """
    finestra = tk.Toplevel(parent)
    finestra.title(titolo)

    tree = ttk.Treeview(finestra, columns=[c[0] for c in colonne], show="headings")

    for nome_colonna, testo in colonne:
        tree.heading(
            nome_colonna,
            text=testo,
            command=lambda _col=nome_colonna: treeview_sort_column(tree, _col, False, column_types or {})
        )
        tree.column(nome_colonna, anchor="center")

    tree.pack(expand=True, fill="both", padx=10, pady=10)

    for riga in dati:
        tree.insert("", tk.END, values=riga)

    return finestra, tree


# =============================================================================
# ORDINAMENTO TABELLE
# =============================================================================

def ordina_colonna_treeview(tree, colonna, stato_ordinamento):
    """
    Ordina una Treeview per colonna con riconoscimento intelligente di numeri e date.

    Args:
        tree: la Treeview da ordinare
        colonna: il nome della colonna cliccata
        stato_ordinamento: dizionario con lo stato corrente
            {
                'colonna': colonna_corrente (o None),
                'ascendente': True/False
            }

    Returns:
        dict: nuovo stato dell'ordinamento
    """
    # Raccogli i dati
    dati = [(tree.set(k, colonna), k) for k in tree.get_children('')]

    # Funzione di conversione intelligente
    def try_convert(val):
        # Prova a convertire in float (rimuovendo simboli € e formattazione)
        try:
            return float(val.replace(" €", "").replace(",", ".").replace("€", "").strip())
        except:
            pass

        # Prova a convertire in data
        try:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt)
                except:
                    continue
        except:
            pass

        # Altrimenti restituisci stringa in minuscolo
        return val.lower()

    # Converti i valori
    dati = [(try_convert(v), k) for v, k in dati]

    # Gestisci direzione ordinamento
    if stato_ordinamento['colonna'] == colonna:
        stato_ordinamento['ascendente'] = not stato_ordinamento['ascendente']
    else:
        stato_ordinamento['ascendente'] = True
        stato_ordinamento['colonna'] = colonna

    # Ordina
    dati.sort(reverse=not stato_ordinamento['ascendente'])

    # Riordina le righe nella Treeview
    for index, (val, k) in enumerate(dati):
        tree.move(k, '', index)

    return stato_ordinamento


# =============================================================================
# DIALOGHI COMUNI
# =============================================================================

def mostra_finestra_testo(parent, titolo, testo, larghezza=600, altezza=400):
    """
    Mostra una finestra con testo (utile per note, log, ecc.)
    """
    finestra = tk.Toplevel(parent)
    finestra.title(titolo)
    finestra.geometry(f"{larghezza}x{altezza}")
    finestra.transient(parent)

    text_widget = tk.Text(finestra, wrap="word", font=("Segoe UI", 10))
    text_widget.pack(fill="both", expand=True, padx=10, pady=10)
    text_widget.insert("1.0", testo)
    text_widget.config(state="disabled")  # Sola lettura

    ttk.Button(finestra, text="Chiudi", command=finestra.destroy).pack(pady=5)

    return finestra


def chiedi_modifica_testo(parent, titolo, etichetta, testo_iniziale=""):
    """
    Mostra un dialog per modificare un testo (note, descrizioni, ecc.)

    Returns:
        str: il testo modificato, o None se annullato
    """
    risultato = [None]  # Usiamo una lista per modificare dentro la funzione interna

    dialog = tk.Toplevel(parent)
    dialog.title(titolo)
    dialog.geometry("600x400")
    dialog.transient(parent)
    dialog.grab_set()

    ttk.Label(dialog, text=etichetta, font=("Segoe UI", 11, "bold")).pack(pady=(10, 5))

    text_widget = tk.Text(dialog, wrap="word", font=("Segoe UI", 10))
    text_widget.pack(fill="both", expand=True, padx=10, pady=5)
    text_widget.insert("1.0", testo_iniziale)

    def conferma():
        risultato[0] = text_widget.get("1.0", "end").strip()
        dialog.destroy()

    def annulla():
        dialog.destroy()

    frame_btn = ttk.Frame(dialog)
    frame_btn.pack(pady=10)

    ttk.Button(frame_btn, text="Conferma", command=conferma).pack(side="left", padx=5)
    ttk.Button(frame_btn, text="Annulla", command=annulla).pack(side="left", padx=5)

    parent.wait_window(dialog)
    return risultato[0]


# =============================================================================
# MENU CONTESTUALE TASTO DESTRO
# =============================================================================

def crea_menu_contestuale(tree, voci_menu, callback_click=None):
    """
    Crea un menu contestuale generico per una Treeview.
    Il menu si chiude cliccando fuori o premendo ESC.
    """
    menu = tk.Menu(tree, tearoff=0)

    for testo, funzione in voci_menu:
        menu.add_command(label=testo, command=funzione)

    def mostra_menu(event):
        # Seleziona la riga su cui si è cliccato
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            tree.focus(item)

            if callback_click:
                callback_click(item)

            # Mostra il menu
            try:
                menu.post(event.x_root, event.y_root)

                # 🔥 FORZA IL FOCUS SUL MENU
                menu.focus_set()

                # 🔥 CHIUDI CON ESC
                menu.bind("<Escape>", lambda e: menu.unpost())

                # 🔥 CHIUDI CON CLICK FUORI - metodo alternativo
                def close_on_click(e):
                    # Se il click non è sul menu, chiudi
                    if e.widget != menu:
                        menu.unpost()
                        tree.unbind("<Button-1>", close_id)

                close_id = tree.bind("<Button-1>", close_on_click, add=True)

            except Exception as e:
                print(f"Errore menu: {e}")

    tree.bind("<Button-3>", mostra_menu)
    return menu

def mostra_immagine_zoom(parent: object, percorso_immagine: object, titolo: object = "Immagine") -> None:
    """Mostra una finestra con immagine zoomabile."""
    try:
        img = Image.open(percorso_immagine)
        img_originale = img.copy()
        zoom_ratio = [1.0]

        win = tk.Toplevel(parent)
        win.title(titolo)
        win.geometry("500x500")

        # ... tutto il resto del codice uguale, ma usa 'parent' invece di 'self'
        # e 'win' invece di mantenere riferimenti a self
        # ...
        # Canvas con scrollbars
        frame_canvas = tk.Frame(win)
        frame_canvas.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame_canvas, bg="white")
        hbar = tk.Scrollbar(frame_canvas, orient='horizontal', command=canvas.xview)
        vbar = tk.Scrollbar(frame_canvas, orient='vertical', command=canvas.yview)
        canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        hbar.grid(row=1, column=0, sticky="ew")
        vbar.grid(row=0, column=1, sticky="ns")
        frame_canvas.rowconfigure(0, weight=1)
        frame_canvas.columnconfigure(0, weight=1)

        def ridisegna():
            zoom = zoom_ratio[0]
            larghezza = int(img_originale.width * zoom)
            altezza = int(img_originale.height * zoom)
            img_resized = img_originale.resize((larghezza, altezza), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img_resized)
            canvas.image = photo
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=photo)
            canvas.config(scrollregion=(0, 0, larghezza, altezza))

        ridisegna()

        # Zoom con rotella
        def zoom(event):
            if event.delta > 0:
                zoom_ratio[0] *= 1.1
            else:
                zoom_ratio[0] /= 1.1
            ridisegna()

        canvas.bind("<MouseWheel>", zoom)
        canvas.bind("<Button-4>", lambda e: zoom(type('event', (), {'delta': 1})))
        canvas.bind("<Button-5>", lambda e: zoom(type('event', (), {'delta': -1})))

        # Pan (trascinamento)
        dragging = {"x": 0, "y": 0}

        def start_drag(event):
            dragging["x"] = event.x
            dragging["y"] = event.y

        def do_drag(event):
            dx = dragging["x"] - event.x
            dy = dragging["y"] - event.y
            canvas.xview_scroll(int(dx), "units")
            canvas.yview_scroll(int(dy), "units")
            dragging["x"] = event.x
            dragging["y"] = event.y

        canvas.bind("<ButtonPress-1>", start_drag)
        canvas.bind("<B1-Motion>", do_drag)

    except Exception as e:
        messagebox.showerror("Errore", f"Errore nel caricamento dell'immagine: {e}")

# =============================================================================
# GESTIONE SELEZIONE COMPONENTI (COMUNE A PIÙ TAB)
# =============================================================================

class SelezionaQuantitaDialog(tk.Toplevel):
    """
    Dialog generico per selezionare quantità e moltiplicatore.
    """

    def __init__(self, parent, titolo, nome_componente, quantita_max, moltiplicatore_default=3.0):
        super().__init__(parent)
        self.title(titolo)
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()

        self.risultato = None

        ttk.Label(self, text=f"Componente: {nome_componente}", font=("Segoe UI", 11)).pack(pady=(20, 10))

        # Quantità
        frame_qta = ttk.Frame(self)
        frame_qta.pack(pady=5)
        ttk.Label(frame_qta, text="Quantità:").pack(side="left", padx=5)
        self.qta_var = tk.StringVar(value="1")
        self.entry_qta = ttk.Entry(frame_qta, textvariable=self.qta_var, width=10)
        self.entry_qta.pack(side="left")
        ttk.Label(frame_qta, text=f"(max {quantita_max:.2f})").pack(side="left", padx=5)

        # Moltiplicatore
        frame_molt = ttk.Frame(self)
        frame_molt.pack(pady=5)
        ttk.Label(frame_molt, text="Moltiplicatore:").pack(side="left", padx=5)
        self.molt_var = tk.DoubleVar(value=moltiplicatore_default)
        self.entry_molt = ttk.Entry(frame_molt, textvariable=self.molt_var, width=10)
        self.entry_molt.pack(side="left")

        # Pulsanti
        frame_btn = ttk.Frame(self)
        frame_btn.pack(pady=20)
        ttk.Button(frame_btn, text="Conferma", command=self.conferma).pack(side="left", padx=5)
        ttk.Button(frame_btn, text="Annulla", command=self.annulla).pack(side="left", padx=5)

        self.entry_qta.focus_set()

    def conferma(self):
        try:
            qta = float(self.qta_var.get())
            molt = self.molt_var.get()
            if qta <= 0 or molt <= 0:
                messagebox.showerror("Errore", "Quantità e moltiplicatore devono essere positivi")
                return
            self.risultato = (qta, molt)
            self.destroy()
        except ValueError:
            messagebox.showerror("Errore", "Inserisci valori numerici validi")

    def annulla(self):
        self.destroy()


# =============================================================================
# DECORATORI PER GESTIONE ERRORI (OPZIONALE)
# =============================================================================

def gestisci_errori_gui(func):
    """
    Decoratore per gestire errori nelle funzioni GUI e mostrarli con messagebox.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{str(e)}")
            return None

    return wrapper

    # ===============================
    # MOSTRA IMMAGINE
    # ===============================



def mostra_immagine_da_treeview(tree, conn, tabella, colonna_img, parent=None, colonna_nome="nome", record_id=None):

    # ---------------------------
    # controllo selezione
    # ---------------------------
    if record_id is None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Selezione", "Seleziona prima una riga!", parent=parent)
            return
        record_id = tree.item(selected[0], "values")[0]  # prende il primo valore della riga selezionata

    cur = conn.cursor()
    cur.execute(f"SELECT {colonna_img}, {colonna_nome} FROM {tabella} WHERE id=?", (record_id,))
    row = cur.fetchone()

    percorso = None
    nome_progetto = "Sconosciuto"
    if row:
        try:
            percorso = row[colonna_img]
        except:
            percorso = row[0]

        try:
            nome_progetto = row[colonna_nome]
        except:
            nome_progetto = "Sconosciuto"

    if not percorso or not os.path.exists(percorso):
        messagebox.showinfo("Immagine", "Nessuna immagine disponibile", parent=parent)
        return

    # ---------------------------
    # finestra anteprima
    # ---------------------------
    anteprima = tk.Toplevel(parent)
    anteprima.title(f"Immagine del Progetto: {nome_progetto}")
    anteprima.configure(bg="#f7f1e1")
    anteprima.geometry("600x600")
    anteprima.transient(parent)

    canvas_frame = tk.Frame(anteprima)
    canvas_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(canvas_frame, bg="#f7f1e1")
    hbar = tk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
    vbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

    hbar.pack(side="bottom", fill="x")
    vbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    img_orig = Image.open(percorso)
    img = img_orig.copy()
    zoom = 1.0

    img_tk = ImageTk.PhotoImage(img)
    img_id = canvas.create_image(0, 0, anchor="nw", image=img_tk)
    canvas.config(scrollregion=canvas.bbox("all"))

    def zoom_event(event):
        nonlocal img, img_tk, zoom

        if event.delta:  # Windows / Mac
            delta = event.delta
        else:            # Linux
            delta = 120 if event.num == 4 else -120

        if delta > 0:
            zoom *= 1.1
        else:
            zoom /= 1.1

        w, h = img_orig.size
        img = img_orig.resize((int(w * zoom), int(h * zoom)), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        canvas.itemconfig(img_id, image=img_tk)
        canvas.config(scrollregion=canvas.bbox("all"))

    canvas.bind("<MouseWheel>", zoom_event)
    canvas.bind("<Button-4>", zoom_event)
    canvas.bind("<Button-5>", zoom_event)

    def start_drag(event):
        canvas.scan_mark(event.x, event.y)

    def drag(event):
        canvas.scan_dragto(event.x, event.y, gain=1)

    canvas.bind("<ButtonPress-1>", start_drag)
    canvas.bind("<B1-Motion>", drag)

    tk.Button(anteprima, text="Chiudi", bg="#d8c3a5",
              command=anteprima.destroy).pack(pady=5)

    anteprima.wait_window()




import tkinter as tk
from tkinter import ttk, messagebox
import os




class DialogComponente(tk.Toplevel):
    """
    Dialog unificato per:
    - Nuovo componente (tutti i campi)
    - Modifica componente (nome, unità, fornitore, note, immagine)
    - Aggiunta scorte (solo quantità, costo, fornitore, note)
    """

    # Modalità del dialog
    MODALITA_NUOVO = "nuovo"
    MODALITA_MODIFICA = "modifica"
    MODALITA_SCORTE = "scorte"

    def __init__(self, parent, titolo, modalita=MODALITA_NUOVO, nome_componente="",
                 unita_componente="pz", fornitore_default="", note_default="",
                 immagine_corrente=None,
                 quantita_max=None, costo_unitario_attuale=None,
                 quantita_default=1.0, costo_default=0.0):
        super().__init__(parent)
        self.title(titolo)
        self.geometry("550x500")
        self.transient(parent)

        self.modalita = modalita
        self.risultato = None

        # Variabili di input
        self.nome_var = tk.StringVar(value=nome_componente)
        self.unita_var = tk.StringVar(value=unita_componente)
        self.quantita_var = tk.DoubleVar(value=quantita_default)
        self.costo_totale_var = tk.DoubleVar(value=costo_default)
        self.costo_unitario_var = tk.DoubleVar(value=0.0)
        self.fornitore_var = tk.StringVar(value=fornitore_default)
        self.note_var = tk.StringVar(value=note_default)
        self.immagine_percorso = immagine_corrente

        self.quantita_max = quantita_max
        self.costo_unitario_attuale = costo_unitario_attuale
        # flag per distinguere modifiche manuali al costo totale
        self._user_edited_cost = False

        self._crea_interfaccia()
        self._aggiorna_stato_iniziale()

        # Mostra immagine esistente se presente (solo per NUOVO e MODIFICA)
        if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_MODIFICA]:
            if self.immagine_percorso and os.path.exists(self.immagine_percorso):
                self._mostra_anteprima(self.immagine_percorso)

        # Ricalcola costo unitario SOLO se siamo in modalità SCORTE
        if self.modalita == self.MODALITA_SCORTE:
            self._ricalcola_costo_unitario()

        # Centra la finestra
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.after(100, self._set_grab)


    def _set_grab(self):
        """Imposta il grab in modo sicuro."""
        try:
            self.grab_set()
        except tk.TclError:
            self.after(100, self._set_grab)

    def _crea_interfaccia(self):
        """Crea l'interfaccia in base alla modalità."""

        # Main frame con canvas per scroll
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_frame = scrollable_frame
        main_frame.columnconfigure(1, weight=1)

        riga = 0

        # === Nome componente (per NUOVO e MODIFICA) ===
        if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_MODIFICA]:
            ttk.Label(main_frame, text="Nome componente:").grid(row=riga, column=0, sticky="w", pady=5)
            ttk.Entry(main_frame, textvariable=self.nome_var, width=40).grid(row=riga, column=1, columnspan=2,
                                                                             sticky="ew", padx=5)
            riga += 1

            # Unità di misura
            ttk.Label(main_frame, text="Unità:").grid(row=riga, column=0, sticky="w", pady=5)
            ttk.Combobox(main_frame, textvariable=self.unita_var, values=["pz", "g", "ml", "m", "kg", "l"],
                         width=10).grid(row=riga, column=1, sticky="w", padx=5)
            riga += 1
        elif self.modalita == self.MODALITA_SCORTE:
            # Nome componente in sola lettura per aggiunta scorte
            ttk.Label(main_frame, text="Componente:").grid(row=riga, column=0, sticky="w", pady=5)
            ttk.Label(main_frame, text=self.nome_var.get(), font=("Segoe UI", 10, "bold")).grid(row=riga, column=1,
                                                                                                sticky="w", padx=5)
            riga += 1

        # === Quantità e Costo (per NUOVO e SCORTE) ===
        if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_SCORTE]:
            # Quantità
            ttk.Label(main_frame, text="Quantità:").grid(row=riga, column=0, sticky="w", pady=5)
            frame_qta = ttk.Frame(main_frame)
            frame_qta.grid(row=riga, column=1, columnspan=2, sticky="w", padx=5)

            self.entry_quantita = ttk.Entry(frame_qta, textvariable=self.quantita_var, width=10)
            self.entry_quantita.pack(side="left")

            if self.quantita_max and self.modalita == self.MODALITA_SCORTE:
                ttk.Label(frame_qta, text=f"(max {self.quantita_max:.2f})", foreground="gray").pack(side="left", padx=5)

            # Evento per ricalcolo costo unitario e per aggiornare automaticamente il
            # costo totale se non è stato modificato manualmente
            self.quantita_var.trace_add("write", self._on_quantita_change)
            riga += 1

            # Costo totale
            ttk.Label(main_frame, text="Costo totale (€):").grid(row=riga, column=0, sticky="w", pady=5)
            self.entry_costo_totale = ttk.Entry(main_frame, textvariable=self.costo_totale_var, width=15)
            self.entry_costo_totale.grid(row=riga, column=1, sticky="w", padx=5)

            # Evento per ricalcolo costo unitario e per segnare modifica manuale
            self.costo_totale_var.trace_add("write", self._on_costo_totale_change)
            riga += 1

            # Costo unitario (calcolato automaticamente)
            ttk.Label(main_frame, text="Costo unitario (€):").grid(row=riga, column=0, sticky="w", pady=5)
            self.label_costo_unitario = ttk.Label(main_frame, text="0.00", font=("Segoe UI", 10, "bold"))
            self.label_costo_unitario.grid(row=riga, column=1, sticky="w", padx=5)

            if self.costo_unitario_attuale and self.modalita == self.MODALITA_SCORTE:
                ttk.Label(main_frame, text=f"(attuale: {self.costo_unitario_attuale:.2f}€)",
                          foreground="blue").grid(row=riga, column=2, sticky="w", padx=5)
            riga += 1

        # === Fornitore (sempre visibile) ===
        ttk.Label(main_frame, text="Fornitore:").grid(row=riga, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.fornitore_var, width=30).grid(row=riga, column=1, columnspan=2,
                                                                              sticky="ew", padx=5)
        riga += 1

        # === Note (sempre visibili) ===
        ttk.Label(main_frame, text="Note:").grid(row=riga, column=0, sticky="w", pady=5)
        self.text_note = tk.Text(main_frame, width=40, height=4, font=("Segoe UI", 9))
        self.text_note.grid(row=riga, column=1, columnspan=2, sticky="ew", padx=5)

        if self.note_var.get():
            self.text_note.insert("1.0", self.note_var.get())
        riga += 1

        # === Immagine con ANTEPRIMA (per NUOVO e MODIFICA) ===
        if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_MODIFICA]:
            # Riga per il pulsante e il nome file
            frame_img = ttk.Frame(main_frame)
            frame_img.grid(row=riga, column=0, columnspan=3, sticky="w", pady=5)

            ttk.Button(frame_img, text="Seleziona immagine", command=self._seleziona_immagine).pack(side="left", padx=5)

            testo_img = os.path.basename(self.immagine_percorso) if self.immagine_percorso else "Nessuna immagine"
            self.label_img = ttk.Label(frame_img, text=testo_img,
                                       foreground="gray" if not self.immagine_percorso else "black")
            self.label_img.pack(side="left", padx=5)
            riga += 1

            # Riga per l'anteprima dell'immagine
            self.anteprima_label = ttk.Label(main_frame)
            self.anteprima_label.grid(row=riga, column=0, columnspan=3, pady=5)
            riga += 1

        # === Pulsanti (sempre visibili) ===
        frame_btn = ttk.Frame(self)
        frame_btn.pack(pady=10)

        ttk.Button(frame_btn, text="Conferma", command=self._conferma).pack(side="left", padx=5)
        ttk.Button(frame_btn, text="Annulla", command=self._annulla).pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self._conferma())
        self.bind("<Escape>", lambda e: self._annulla())
        self.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _aggiorna_stato_iniziale(self):
        """Imposta lo stato iniziale in base alla modalità."""
        if self.modalita == self.MODALITA_SCORTE:
            # Disabilita campi non modificabili per le scorte
            self.entry_costo_totale.config(state="normal")
        else:
            # Nuovo componente e modifica: tutto modificabile
            pass

    def _on_quantita_change(self, *args):
        """Callback invocato quando cambia la quantità.

        Se siamo in modalità scorte e l'utente non ha modificato manualmente
        il costo totale, aggiorniamo automaticamente il costo totale in modo
        da mantenere lo stesso costo unitario attuale.
        """
        if self.modalita == self.MODALITA_SCORTE and self.costo_unitario_attuale is not None:
            if not self._user_edited_cost:
                try:
                    q = self.quantita_var.get()
                    # imposto direttamente il valore, la trace sul costo totale
                    # segnalerà la modifica e richiamerà il ricalcolo
                    self.costo_totale_var.set(q * self.costo_unitario_attuale)
                except Exception:
                    pass
        self._ricalcola_costo_unitario()

    def _on_costo_totale_change(self, *args):
        """Callback invocato quando l'utente modifica il costo totale.

        Segnaliamo che l'utente ha toccato il campo, in modo da non sovrascrivere
        più avanti il valore durante la variazione della quantità.
        """
        self._user_edited_cost = True
        self._ricalcola_costo_unitario()

    def _ricalcola_costo_unitario(self):
        """Calcola il costo unitario in base a quantità e costo totale."""
        # Se non siamo in modalità che richiedono il calcolo, non fare nulla
        if self.modalita not in [self.MODALITA_NUOVO, self.MODALITA_SCORTE]:
            return

        try:
            qta = self.quantita_var.get()
            costo_tot = self.costo_totale_var.get()

            # Verifica che il label esista prima di usarlo
            if hasattr(self, 'label_costo_unitario') and self.label_costo_unitario:
                if qta > 0 and costo_tot > 0:
                    costo_unit = costo_tot / qta
                    self.label_costo_unitario.config(text=f"{costo_unit:.2f}€")
                    self.costo_unitario_var.set(costo_unit)
                else:
                    self.label_costo_unitario.config(text="0.00€")
                    self.costo_unitario_var.set(0.0)
        except:
            if hasattr(self, 'label_costo_unitario') and self.label_costo_unitario:
                self.label_costo_unitario.config(text="0.00€")
            self.costo_unitario_var.set(0.0)

    def _seleziona_immagine(self):
        """Seleziona un'immagine per il componente."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Seleziona immagine",
            filetypes=[("Immagini", "*.png *.jpg *.jpeg *.gif *.bmp")],
            parent=self
        )
        if path:
            self.immagine_percorso = path
            self.label_img.config(text=os.path.basename(path), foreground="black")
            self._mostra_anteprima(path)

    def _mostra_anteprima(self, percorso):
        """Mostra un'anteprima dell'immagine."""
        try:
            from PIL import Image, ImageTk

            # Apri e ridimensiona l'immagine
            img = Image.open(percorso)
            img.thumbnail((200, 200))  # Ridimensiona a max 200x200
            photo = ImageTk.PhotoImage(img)

            # Mantieni un riferimento per evitare garbage collection
            self.anteprima_photo = photo

            # Mostra l'immagine (supponendo che esista self.anteprima_label)
            if hasattr(self, 'anteprima_label'):
                self.anteprima_label.config(image=photo)
                self.anteprima_label.image = photo  # Altro riferimento
        except Exception as e:
            if hasattr(self, 'anteprima_label'):
                self.anteprima_label.config(text=f"Errore: {e}")


    def _conferma(self):
        """Valida i dati e restituisce il risultato."""
        try:
            # Validazioni base (comuni a tutte le modalità)
            if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_MODIFICA]:
                if not self.nome_var.get().strip():
                    messagebox.showerror("Errore", "Il nome del componente è obbligatorio.", parent=self)
                    return
                if not self.unita_var.get().strip():
                    messagebox.showerror("Errore", "L'unità di misura è obbligatoria.", parent=self)
                    return

            # Validazioni per quantità e costo (NUOVO e SCORTE)
            if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_SCORTE]:
                qta = self.quantita_var.get()
                if qta <= 0:
                    messagebox.showerror("Errore", "La quantità deve essere maggiore di zero.", parent=self)
                    return

                if self.modalita == self.MODALITA_SCORTE and self.quantita_max and qta > self.quantita_max:
                    messagebox.showerror("Errore", f"La quantità non può superare {self.quantita_max:.2f}.",
                                         parent=self)
                    return

                costo_tot = self.costo_totale_var.get()
                if costo_tot < 0:
                    messagebox.showerror("Errore", "Il costo non può essere negativo.", parent=self)
                    return

            # Recupera note dal Text widget
            note = self.text_note.get("1.0", "end").strip()

            # Prepara il risultato base
            risultato = {
                'modalita': self.modalita,
                'nome': self.nome_var.get().strip(),
                'unita': self.unita_var.get().strip(),
                'fornitore': self.fornitore_var.get().strip(),
                'note': note,
                'immagine_percorso': self.immagine_percorso
            }

            # Aggiungi campi specifici per NUOVO e SCORTE
            if self.modalita in [self.MODALITA_NUOVO, self.MODALITA_SCORTE]:
                risultato.update({
                    'quantita': self.quantita_var.get(),
                    'costo_totale': self.costo_totale_var.get(),
                    'costo_unitario': self.costo_unitario_var.get()
                })

            self.risultato = risultato
            self.destroy()

        except Exception as e:
            messagebox.showerror("Errore", f"Dati non validi: {str(e)}", parent=self)

    def _annulla(self):
        """Annulla l'operazione."""
        self.risultato = None
        self.destroy()

