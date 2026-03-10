# gui/config_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
from config.config import config
import os


class ConfigDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configurazione Applicazione")
        self.configure(bg="#f7f1e1")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()

        self._crea_interfaccia()
        self._centra_finestra()

    def _crea_interfaccia(self):
        """Crea l'interfaccia del dialog di configurazione."""

        # Notebook per organizzare le sezioni
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab Anagrafica
        self._crea_tab_anagrafica(notebook)

        # Tab Applicazione
        self._crea_tab_app(notebook)

        # Tab Mercati
        self._crea_tab_mercati(notebook)

        self._crea_tab_ordini(notebook)

        # Pulsanti
        frame_buttons = tk.Frame(self, bg="#f7f1e1")
        frame_buttons.pack(fill="x", padx=10, pady=10)

        tk.Button(frame_buttons, text="Salva", command=self._salva,
                  bg="#90EE90", font=("Segoe UI", 10, "bold"), padx=20).pack(side="right", padx=5)
        tk.Button(frame_buttons, text="Annulla", command=self.destroy,
                  bg="#f0f0f0", font=("Segoe UI", 10), padx=20).pack(side="right", padx=5)

    def _crea_tab_anagrafica(self, notebook):
        """Tab per i dati anagrafici."""
        tab = tk.Frame(notebook, bg="#fffafa")
        notebook.add(tab, text="Anagrafica")

        # Form
        frame = tk.Frame(tab, bg="#fffafa")
        frame.pack(expand=True, padx=20, pady=20)

        fields = [
            ("Nome e Cognome:", "nome_cognome"),
            ("Numero Tessera:", "tessera"),
            ("Rilasciato il:", "rilasciato_il"),
            ("Comune:", "comune")
        ]

        self.anagrafica_vars = {}

        for i, (label, key) in enumerate(fields):
            tk.Label(frame, text=label, bg="#fffafa",
                     font=("Segoe UI", 11)).grid(row=i, column=0, sticky="w", pady=5, padx=5)

            var = tk.StringVar(value=config.get("anagrafica", key, default=""))
            self.anagrafica_vars[key] = var

            tk.Entry(frame, textvariable=var, width=40,
                     font=("Segoe UI", 11)).grid(row=i, column=1, pady=5, padx=5)

    def _crea_tab_app(self, notebook):
        """Tab per le impostazioni dell'applicazione."""
        tab = tk.Frame(notebook, bg="#fffafa")
        notebook.add(tab, text="Applicazione")

        frame = tk.Frame(tab, bg="#fffafa")
        frame.pack(expand=True, padx=20, pady=20)

        # Tema
        tk.Label(frame, text="Tema:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", pady=5)

        self.theme_var = tk.StringVar(value=config.get("app", "theme", default="clam"))
        theme_combo = ttk.Combobox(frame, textvariable=self.theme_var,
                                   values=["clam", "alt", "default", "classic"],
                                   width=20, font=("Segoe UI", 11))
        theme_combo.grid(row=0, column=1, pady=5)

        # Dimensione font
        tk.Label(frame, text="Dimensione Font:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=5)

        self.font_var = tk.IntVar(value=config.get("app", "font_size", default=12))
        tk.Spinbox(frame, from_=8, to=20, textvariable=self.font_var,
                   width=10, font=("Segoe UI", 11)).grid(row=1, column=1, sticky="w", pady=5)

        # Backup automatico
        self.backup_var = tk.BooleanVar(value=config.get("app", "backup_automatico", default=True))
        tk.Checkbutton(frame, text="Backup automatico", variable=self.backup_var,
                       bg="#fffafa", font=("Segoe UI", 11)).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        # Giorni backup
        tk.Label(frame, text="Giorni tra backup:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=3, column=0, sticky="w", pady=5)

        self.backup_giorni_var = tk.IntVar(value=config.get("app", "backup_giorni", default=7))
        tk.Spinbox(frame, from_=1, to=30, textvariable=self.backup_giorni_var,
                   width=10, font=("Segoe UI", 11)).grid(row=3, column=1, sticky="w", pady=5)

    def _crea_tab_mercati(self, notebook):
        """Tab per le impostazioni dei mercati."""
        tab = tk.Frame(notebook, bg="#fffafa")
        notebook.add(tab, text="Mercati")

        frame = tk.Frame(tab, bg="#fffafa")
        frame.pack(expand=True, padx=20, pady=20)

        # Ultimo Luogo
        tk.Label(frame, text="Ultimo Luogo:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", pady=5)

        self.ultimo_luogo_var = tk.StringVar(value=config.get("mercati", "ultimo_luogo", default=""))
        tk.Entry(frame, textvariable=self.ultimo_luogo_var, width=40,
                 font=("Segoe UI", 11)).grid(row=0, column=1, pady=5)

        # Ultima Data
        tk.Label(frame, text="Ultima Data:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=5)

        self.ultima_data_var = tk.StringVar(value=config.get("mercati", "ultima_data", default=""))
        tk.Entry(frame, textvariable=self.ultima_data_var, width=40,
                 font=("Segoe UI", 11)).grid(row=1, column=1, pady=5)

        # 🔴 NUOVO: Cartella PDF predefinita
        tk.Label(frame, text="Cartella PDF:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=2, column=0, sticky="w", pady=5)

        frame_pdf = tk.Frame(frame, bg="#fffafa")
        frame_pdf.grid(row=2, column=1, sticky="w", pady=5)

        self.cartella_pdf_var = tk.StringVar(value=config.get("mercati", "cartella_pdf_default", default=""))
        self.entry_cartella_pdf = tk.Entry(frame_pdf, textvariable=self.cartella_pdf_var, width=30,
                                           font=("Segoe UI", 11))
        self.entry_cartella_pdf.pack(side="left", padx=(0, 5))

        def seleziona_cartella():
            from tkinter import filedialog
            cartella = filedialog.askdirectory(
                title="Seleziona cartella per i PDF",
                initialdir=self.cartella_pdf_var.get() or os.path.expanduser("~"),
                parent=self
            )
            if cartella:
                self.cartella_pdf_var.set(cartella)

        tk.Button(frame_pdf, text="Sfoglia...", command=seleziona_cartella,
                  bg="#deb887", font=("Segoe UI", 10)).pack(side="left")

        # Pulsante per aprire la cartella
        def apri_cartella():
            cartella = self.cartella_pdf_var.get()
            if cartella and os.path.exists(cartella):
                import subprocess
                import platform
                import os
                if platform.system() == "Windows":
                    os.startfile(cartella)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', cartella])
                else:  # linux
                    subprocess.run(['xdg-open', cartella])

        tk.Button(frame_pdf, text="📂 Apri", command=apri_cartella,
                  bg="#90EE90", font=("Segoe UI", 10)).pack(side="left", padx=5)

    def _crea_tab_ordini(self, notebook):
        """Tab per le impostazioni degli ordini."""
        print("🔧 Creazione tab Ordini...")  # Debug
        tab = tk.Frame(notebook, bg="#fffafa")
        notebook.add(tab, text="Ordini")

        frame = tk.Frame(tab, bg="#fffafa")
        frame.pack(expand=True, padx=20, pady=20)

        riga = 0

        # Cartella sorgente (FILE_ORDINI)
        tk.Label(frame, text="Cartella sorgente:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=riga, column=0, sticky="w", pady=5)

        frame_sorgente = tk.Frame(frame, bg="#fffafa")
        frame_sorgente.grid(row=riga, column=1, sticky="w", pady=5)
        riga += 1

        self.cartella_sorgente_var = tk.StringVar(
            value=config.get("ordini", "cartella_sorgente", default="FILE_ORDINI"))
        self.entry_cartella_sorgente = tk.Entry(frame_sorgente, textvariable=self.cartella_sorgente_var, width=40,
                                                font=("Segoe UI", 11))
        self.entry_cartella_sorgente.pack(side="left", padx=(0, 5))

        def seleziona_cartella_sorgente():
            from tkinter import filedialog
            import os
            cartella = filedialog.askdirectory(
                title="Seleziona cartella sorgente (contenuto da copiare)",
                initialdir=self.cartella_sorgente_var.get() or os.path.expanduser("~"),
                parent=self
            )
            if cartella:
                self.cartella_sorgente_var.set(cartella)

        tk.Button(frame_sorgente, text="Sfoglia...", command=seleziona_cartella_sorgente,
                  bg="#deb887", font=("Segoe UI", 10)).pack(side="left")

        # 🔴 Pulsante per aprire la cartella sorgente
        def apri_cartella_sorgente():
            import subprocess
            import platform
            import os
            cartella = self.cartella_sorgente_var.get()
            if cartella and os.path.exists(cartella):
                try:
                    if platform.system() == "Windows":
                        os.startfile(cartella)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', cartella])
                    else:  # linux
                        subprocess.run(['xdg-open', cartella])
                except Exception as e:

                    messagebox.showerror("Errore", f"Impossibile aprire la cartella:\n{e}", parent=self)

        tk.Button(frame_sorgente, text="📂 Apri", command=apri_cartella_sorgente,
                  bg="#90EE90", font=("Segoe UI", 10)).pack(side="left", padx=5)

        # Cartella destinazione
        tk.Label(frame, text="Cartella destinazione base:", bg="#fffafa",
                 font=("Segoe UI", 11)).grid(row=riga, column=0, sticky="w", pady=5)

        frame_dest = tk.Frame(frame, bg="#fffafa")
        frame_dest.grid(row=riga, column=1, sticky="w", pady=5)
        riga += 1

        self.cartella_destinazione_var = tk.StringVar(value=config.get("ordini", "cartella_destinazione", default=""))
        self.entry_cartella_destinazione = tk.Entry(frame_dest, textvariable=self.cartella_destinazione_var, width=40,
                                                    font=("Segoe UI", 11))
        self.entry_cartella_destinazione.pack(side="left", padx=(0, 5))

        def seleziona_cartella_destinazione():
            from tkinter import filedialog
            import os
            cartella = filedialog.askdirectory(
                title="Seleziona cartella base dove salvare gli ordini",
                initialdir=self.cartella_destinazione_var.get() or os.path.expanduser("~"),
                parent=self
            )
            if cartella:
                self.cartella_destinazione_var.set(cartella)

        tk.Button(frame_dest, text="Sfoglia...", command=seleziona_cartella_destinazione,
                  bg="#deb887", font=("Segoe UI", 10)).pack(side="left")

        # Pulsante per aprire la cartella destinazione
        def apri_cartella_destinazione():
            import subprocess
            import platform
            import os
            cartella = self.cartella_destinazione_var.get()
            if cartella and os.path.exists(cartella):
                try:
                    if platform.system() == "Windows":
                        os.startfile(cartella)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', cartella])
                    else:  # linux
                        subprocess.run(['xdg-open', cartella])
                except Exception as e:

                    messagebox.showerror("Errore", f"Impossibile aprire la cartella:\n{e}", parent=self)

        tk.Button(frame_dest, text="📂 Apri", command=apri_cartella_destinazione,
                  bg="#90EE90", font=("Segoe UI", 10)).pack(side="left", padx=5)

        # Checkbox per copiare i file
        self.copia_file_ordini_var = tk.BooleanVar(value=config.get("ordini", "copia_file_ordini", default=True))
        tk.Checkbutton(frame, text="Copia automaticamente i file dalla cartella sorgente",
                       variable=self.copia_file_ordini_var,
                       bg="#fffafa", font=("Segoe UI", 11)).grid(row=riga, column=0, columnspan=2, sticky="w", pady=5)
        riga += 1

        # Checkbox per aprire cartella dopo salvataggio
        self.apri_cartella_var = tk.BooleanVar(
            value=config.get("ordini", "apri_cartella_dopo_salvataggio", default=False))
        tk.Checkbutton(frame, text="Apri cartella dopo il salvataggio",
                       variable=self.apri_cartella_var,
                       bg="#fffafa", font=("Segoe UI", 11)).grid(row=riga, column=0, columnspan=2, sticky="w", pady=5)
        riga += 1

        # Informazione
        tk.Label(frame,
                 text="💡 Il salvataggio creerà una cartella con il nome del cliente\n   contenente il file ordine.txt e i file dalla cartella sorgente",
                 bg="#fffafa", fg="#5a3e1b", font=("Segoe UI", 9, "italic"), justify="left").grid(row=riga, column=0,
                                                                                                  columnspan=2,
                                                                                                  sticky="w", pady=10)

    def _salva(self):
        """Salva le modifiche."""
        # Salva anagrafica
        for key, var in self.anagrafica_vars.items():
            config.set("anagrafica", key, var.get())

        # Salva app
        config.set("app", "theme", self.theme_var.get())
        config.set("app", "font_size", self.font_var.get())
        config.set("app", "backup_automatico", self.backup_var.get())
        config.set("app", "backup_giorni", self.backup_giorni_var.get())

        # Salva mercati
        config.set("mercati", "ultimo_luogo", self.ultimo_luogo_var.get())
        config.set("mercati", "ultima_data", self.ultima_data_var.get())
        config.set("mercati", "cartella_pdf_default", self.cartella_pdf_var.get())

        # 🔴 SALVA ORDINI (inclusi i percorsi)
        config.set("ordini", "cartella_sorgente", self.cartella_sorgente_var.get())
        config.set("ordini", "cartella_destinazione", self.cartella_destinazione_var.get())
        config.set("ordini", "copia_file_ordini", self.copia_file_ordini_var.get())
        config.set("ordini", "apri_cartella_dopo_salvataggio", self.apri_cartella_var.get())

        messagebox.showinfo("Configurazione", "Impostazioni salvate con successo!", parent=self)
        self.destroy()

    def _centra_finestra(self):
        self.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")