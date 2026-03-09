# gui/bilancio_gui.py
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from dateutil.relativedelta import relativedelta
import mplcursors
from logic.bilancio import BilancioManager
from utils.helpers import (
    mostra_info, mostra_attenzione, mostra_errore
)
from utils.gui_utils import crea_finestra_con_treeview


class TabBilancio(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(padx=10, pady=10, fill="both", expand=True)
        self.configure(bg="#f7f1e1")

        self.crea_interfaccia()
        self._imposta_date_default()
        self.calcola_bilancio()

    # =========================================================================
    # CREAZIONE INTERFACCIA
    # =========================================================================

    def crea_interfaccia(self):
        """Crea tutti gli elementi dell'interfaccia."""
        self._crea_filtri()
        self._crea_risultati()
        self._crea_grafico()

    def _crea_filtri(self):
        """Crea i filtri per la selezione del periodo."""
        filtro_frame = tk.Frame(self, bg="#f7f1e1")
        filtro_frame.pack(fill="x", pady=(0, 10))

        lbl_font = ("Segoe UI", 10, "bold")
        btn_opts = {
            "font": ("Segoe Print", 10, "bold"),
            "relief": "raised",
            "bd": 2,
            "bg": "#deb887",
            "activebackground": "#d2b48c",
            "fg": "#5a3e1b",
            "activeforeground": "#3e2f1c",
            "cursor": "hand2",
            "padx": 10,
            "pady": 6,
        }

        # Data DA
        tk.Label(filtro_frame, text="Periodo da:", bg="#f7f1e1", font=lbl_font).pack(side="left", padx=(0, 5))
        self.data_da = DateEntry(filtro_frame, width=14, background='darkblue',
                                 foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.data_da.pack(side="left")

        tk.Label(filtro_frame, text="a", bg="#f7f1e1", font=lbl_font).pack(side="left", padx=5)

        # Data A
        self.data_a = DateEntry(filtro_frame, width=14, background='darkblue',
                                foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.data_a.pack(side="left")

        # Filtro rapido
        opzioni_periodo = ["Ultimi 30 giorni", "Ultimi 3 mesi", "Ultimi 6 mesi", "Ultimo anno", "Tutto"]
        self.var_periodo = tk.StringVar()
        self.var_periodo.set("⏱️ Filtro rapido")
        menu = ttk.OptionMenu(filtro_frame, self.var_periodo, self.var_periodo.get(),
                              *opzioni_periodo, command=self.applica_filtro_predefinito)
        menu.pack(side="left", padx=10)

        # Pulsante calcolo
        self.btn_calcola = tk.Button(filtro_frame, text="📊 Calcola Bilancio",
                                     command=self.calcola_bilancio, **btn_opts)
        self.btn_calcola.pack(side="left", padx=10)

    def _crea_risultati(self):
        """Crea il frame con i risultati numerici (inclusi buoni e acconti)."""
        # Frame contenitore dati + grafici
        contenitore = tk.Frame(self, bg="#f7f1e1")
        contenitore.pack(fill="both", expand=True)

        # Frame sinistro per i dati principali
        self.frame_sx = tk.Frame(contenitore, bg="#f7f1e1")
        self.frame_sx.pack(side="left", fill="y", padx=(0, 10), pady=5)

        # Dati principali
        self.valori = {}
        voci_principali = ["Spese Magazzino", "Spese Gestione", "Totale Spese", "Ricavi", "Utile Netto"]

        for voce in voci_principali:
            frame = tk.Frame(self.frame_sx, bg="#f7f1e1")
            frame.pack(fill="x", pady=8)

            lbl_descr = tk.Label(frame, text=voce + ":", font=("Segoe UI", 12, "bold"),
                                 bg="#f7f1e1", fg="#5a3e1b")
            lbl_descr.pack(side="left", padx=5)

            lbl_val = tk.Label(frame, text="0.00 €", font=("Segoe UI", 12), bg="#f7f1e1")
            lbl_val.pack(side="left", padx=(0, 10))

            self.valori[voce] = lbl_val

        # Separatore
        ttk.Separator(self.frame_sx, orient='horizontal').pack(fill="x", pady=15)

        # 🔥 SEZIONE BUONI
        tk.Label(self.frame_sx, text="📊 BUONI REGALO/SCONTO",
                 font=("Segoe UI", 12, "bold"), bg="#f7f1e1", fg="#5a3e1b").pack(anchor="w", pady=(0, 5))

        voci_buoni = [
            ("Buoni venduti", "buoni_venduti", ""),
            ("Incassato da buoni", "incassato_buoni", "€"),
            ("Buoni utilizzati", "utilizzi_buoni", ""),
            ("Valore utilizzato", "valore_utilizzato", "€"),
            ("Buoni attivi residui", "buoni_residui", "€"),
        ]

        self.valori_buoni = {}
        for desc, chiave, unita in voci_buoni:
            frame = tk.Frame(self.frame_sx, bg="#f7f1e1")
            frame.pack(fill="x", pady=4)

            lbl_descr = tk.Label(frame, text=desc + ":", font=("Segoe UI", 10),
                                 bg="#f7f1e1", fg="#5a3e1b")
            lbl_descr.pack(side="left", padx=5)

            lbl_val = tk.Label(frame, text="0", font=("Segoe UI", 10, "bold"),
                               bg="#f7f1e1", fg="#3366cc")
            lbl_val.pack(side="left", padx=(0, 5))

            if unita:
                tk.Label(frame, text=unita, font=("Segoe UI", 10),
                         bg="#f7f1e1").pack(side="left")

            self.valori_buoni[chiave] = lbl_val

        # 🔥 NUOVA SEZIONE ACCONTI
        ttk.Separator(self.frame_sx, orient='horizontal').pack(fill="x", pady=15)

        tk.Label(self.frame_sx, text="💰 ACCONTI SU ORDINI",
                 font=("Segoe UI", 12, "bold"), bg="#f7f1e1", fg="#5a3e1b").pack(anchor="w", pady=(0, 5))

        voci_acconti = [
            ("Ordini con acconto", "numero_acconti", ""),
            ("Totale acconti", "totale_acconti", "€"),
            ("Acconti attivi residui", "acconti_attivi", "€"),
        ]

        self.valori_acconti = {}
        for desc, chiave, unita in voci_acconti:
            frame = tk.Frame(self.frame_sx, bg="#f7f1e1")
            frame.pack(fill="x", pady=4)

            lbl_descr = tk.Label(frame, text=desc + ":", font=("Segoe UI", 10),
                                 bg="#f7f1e1", fg="#5a3e1b")
            lbl_descr.pack(side="left", padx=5)

            lbl_val = tk.Label(frame, text="0", font=("Segoe UI", 10, "bold"),
                               bg="#f7f1e1", fg="#cc6633")  # Colore arancio per distinguere
            lbl_val.pack(side="left", padx=(0, 5))

            if unita:
                tk.Label(frame, text=unita, font=("Segoe UI", 10),
                         bg="#f7f1e1").pack(side="left")

            self.valori_acconti[chiave] = lbl_val

        # Pulsante dettaglio acconti
        btn_dettaglio_acconti = tk.Button(self.frame_sx, text="📋 Dettaglio Ordini con Acconto",
                                          command=self.mostra_dettaglio_acconti,
                                          bg="#deb887", font=("Segoe UI", 9))
        btn_dettaglio_acconti.pack(anchor="w", pady=(10, 5))

        # 🔥 NOTA ESPLICATIVA (aggiornata con acconti)
        nota_frame = tk.Frame(self.frame_sx, bg="#f7f1e1")
        nota_frame.pack(fill="x", pady=(20, 5))

        tk.Label(nota_frame,
                 text="📌 Nota: I ricavi includono:",
                 font=("Segoe UI", 9, "bold"),
                 bg="#f7f1e1", fg="#5a3e1b").pack(anchor="w")

        tk.Label(nota_frame,
                 text="   • Vendite dirette (contanti/carta)",
                 font=("Segoe UI", 8),
                 bg="#f7f1e1").pack(anchor="w")

        tk.Label(nota_frame,
                 text="   • Utilizzo buoni regalo (quando vengono spesi)",
                 font=("Segoe UI", 8),
                 bg="#f7f1e1").pack(anchor="w")

        tk.Label(nota_frame,
                 text="   • La vendita dei buoni NON è un ricavo immediato",
                 font=("Segoe UI", 8),
                 bg="#f7f1e1", fg="gray").pack(anchor="w")

        tk.Label(nota_frame,
                 text="   • Gli acconti sono passività fino al saldo finale",
                 font=("Segoe UI", 8),
                 bg="#f7f1e1", fg="gray").pack(anchor="w")

        # Salva il contenitore
        self.contenitore = contenitore

    def _crea_grafico(self):
        """Crea il frame per il grafico."""
        self.grafico_frame = tk.Frame(self.contenitore, bg="#f7f1e1", bd=2, relief="sunken")
        self.grafico_frame.pack(side="left", fill="both", expand=True, pady=5)

        # Setup figura matplotlib
        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.set_title("Bilancio cumulativo nel tempo", fontsize=14, color="#5a3e1b")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.grafico_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _imposta_date_default(self):
        """Imposta le date predefinite (ultimo anno)."""
        oggi = datetime.today()
        dodici_mesi_fa = oggi - timedelta(days=365)
        self.data_da.set_date(dodici_mesi_fa)
        self.data_a.set_date(oggi)

    # =========================================================================
    # LOGICA DI CALCOLO
    # =========================================================================

    def calcola_bilancio(self):
        """Calcola il bilancio per il periodo selezionato (inclusi buoni e acconti)."""
        da = self.data_da.get_date()
        a = self.data_a.get_date()

        if da > a:
            mostra_attenzione("Attenzione",
                              "La data 'Da' deve essere precedente o uguale alla data 'A'.",
                              parent=self)
            return



        da_str = da.strftime("%Y-%m-%d")
        # Aggiungi un giorno alla data di fine per includere tutto il giorno
        a_plus_one = a + timedelta(days=1)
        a_str = a_plus_one.strftime("%Y-%m-%d")

        print(f"📅 Periodo selezionato (inclusivo): {da_str} → {a_str}")

        try:


            # Ottieni il bilancio completo (con buoni)
            bilancio = BilancioManager.get_bilancio_completo(da_str, a_str)

            # 🔥 NUOVO: Ottieni riepilogo acconti
            riepilogo_acconti = BilancioManager.get_riepilogo_acconti(da_str, a_str)

            # Ottieni i dati mensili
            spese_magazzino_mese = BilancioManager.get_spese_magazzino_mensili(da_str, a_str)
            spese_gestione_mese = BilancioManager.get_spese_gestione_mensili(da_str, a_str)
            ricavi_mese = BilancioManager.get_ricavi_mensili(da_str, a_str)

            # Prepara i mesi per il grafico
            mesi, ricavi_cum, spese_cum, bilancio_cum = \
                self._prepara_dati_grafico(da, a, ricavi_mese, spese_magazzino_mese, spese_gestione_mese)

            # Aggiorna i dati numerici
            self._aggiorna_dati_numerici(bilancio)
            self._aggiorna_dati_buoni(bilancio['buoni'])
            self._aggiorna_dati_acconti(riepilogo_acconti)  # <-- NUOVO

            # Aggiorna il grafico
            self._aggiorna_grafico(mesi, ricavi_cum, spese_cum, bilancio_cum)

        except Exception as e:
            mostra_errore("Errore", f"Errore nel calcolo del bilancio: {e}", parent=self)
            import traceback
            traceback.print_exc()

    def _prepara_dati_grafico(self, da, a, ricavi_mese, spese_magazzino_mese, spese_gestione_mese):
        """
        Prepara i dati per il grafico cumulativo.
        """
        # Genera lista completa dei mesi nel periodo
        mesi = []
        cur = da
        while cur <= a:
            mesi.append(cur.strftime("%Y-%m"))
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur + relativedelta(months=1)

        # Crea liste con valori mensili
        ricavi_list = [ricavi_mese.get(m, 0) for m in mesi]
        spese_magazzino_list = [spese_magazzino_mese.get(m, 0) for m in mesi]
        spese_gestione_list = [spese_gestione_mese.get(m, 0) for m in mesi]

        # Calcola cumulativi
        ricavi_cumulativi = []
        spese_cumulative = []
        bilancio_cumulativo = []

        tot_ricavi = 0.0
        tot_spese = 0.0

        for i in range(len(mesi)):
            tot_ricavi += ricavi_list[i]
            tot_spese += spese_magazzino_list[i] + spese_gestione_list[i]

            ricavi_cumulativi.append(tot_ricavi)
            spese_cumulative.append(tot_spese)
            bilancio_cumulativo.append(tot_ricavi - tot_spese)

        return mesi, ricavi_cumulativi, spese_cumulative, bilancio_cumulativo

    def _aggiorna_dati_numerici(self, dati):
        """Aggiorna i label con i dati numerici."""
        self.valori["Spese Magazzino"].config(text=f"{dati['spese_magazzino']:.2f} €")
        self.valori["Spese Gestione"].config(text=f"{dati['spese_gestione']:.2f} €")
        self.valori["Totale Spese"].config(text=f"{dati['totale_spese']:.2f} €")
        self.valori["Ricavi"].config(text=f"{dati['ricavi']:.2f} €")
        self.valori["Utile Netto"].config(text=f"{dati['utile']:.2f} €")

    def _aggiorna_grafico(self, mesi, ricavi_cum, spese_cum, bilancio_cum):
        """Aggiorna il grafico con i nuovi dati."""
        self.ax.clear()
        self.ax.grid(True, linestyle='--', alpha=0.4)
        self.ax.set_title("Bilancio cumulativo nel tempo", fontsize=14, color="#5a3e1b")

        x = [datetime.strptime(m, "%Y-%m") for m in mesi]

        # Linea ricavi
        line_ricavi, = self.ax.plot(
            x, ricavi_cum,
            label="Ricavi cumulativi",
            color="#5cb85c",
            linewidth=2
        )

        # Linea spese
        line_spese, = self.ax.plot(
            x, spese_cum,
            label="Spese cumulative",
            color="#d9534f",
            linewidth=2
        )

        # Linea zero
        self.ax.axhline(0, color="black", linewidth=1, alpha=0.6)

        # Linea bilancio
        line_bilancio, = self.ax.plot(
            x, bilancio_cum,
            label="Bilancio cumulativo",
            color="#3366cc",
            linestyle="--",
            linewidth=2
        )

        # Formatta asse x
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.ax.xaxis.set_major_locator(mdates.MonthLocator())
        self.fig.autofmt_xdate(rotation=45)

        self.ax.legend()

        # Tooltip interattivi
        self._aggiungi_tooltip([line_ricavi, line_spese, line_bilancio])

        self.canvas.draw()

    def _aggiungi_tooltip(self, lines):
        """Aggiunge tooltip interattivi al grafico."""
        cursor = mplcursors.cursor(lines, hover=True)

        @cursor.connect("add")
        def on_add(sel):
            x_val, y_val = sel.target
            data = mdates.num2date(x_val).strftime("%Y-%m")
            label = sel.artist.get_label()

            sel.annotation.set(
                text=f"{label}\n{data}\n{y_val:,.2f} €"
            )
            sel.annotation.get_bbox_patch().set(alpha=0.85)

    # =========================================================================
    # FILTRI RAPIDI
    # =========================================================================

    def applica_filtro_predefinito(self, opzione):
        """Applica un filtro rapido predefinito."""
        oggi = datetime.today()

        if opzione == "Ultimi 30 giorni":
            nuova_data_da = oggi - timedelta(days=30)
        elif opzione == "Ultimi 3 mesi":
            nuova_data_da = oggi - timedelta(days=90)
        elif opzione == "Ultimi 6 mesi":
            nuova_data_da = oggi - timedelta(days=180)
        elif opzione == "Ultimo anno":
            nuova_data_da = oggi - timedelta(days=365)
        elif opzione == "Tutto":
            nuova_data_da = datetime(2000, 1, 1)
        else:
            return

        self.data_da.set_date(nuova_data_da)
        self.data_a.set_date(oggi)
        self.calcola_bilancio()

    def _aggiorna_dati_acconti(self, dati_acconti):
        """Aggiorna i label con i dati degli acconti."""
        self.valori_acconti["numero_acconti"].config(text=str(dati_acconti['numero_acconti']))
        self.valori_acconti["totale_acconti"].config(text=f"{dati_acconti['totale_acconti']:.2f}")
        self.valori_acconti["acconti_attivi"].config(text=f"{dati_acconti['acconti_attivi']:.2f}")

    def mostra_dettaglio_acconti(self):
        """Mostra una finestra con il dettaglio degli ordini che hanno acconto."""
        da = self.data_da.get_date().strftime("%Y-%m-%d")
        a_date = self.data_a.get_date()

        # 🔥 AGGIUNGI UN GIORNO per includere tutto il giorno finale
        a_plus_one = (a_date + timedelta(days=1)).strftime("%Y-%m-%d")

        print(f"🔍 DEBUG - Dettaglio acconti: {da} → {a_plus_one} (inclusivo)")

        acconti = BilancioManager.get_dettaglio_acconti(da, a_plus_one)

        if not acconti:
            mostra_info("Nessun acconto",
                        f"Nessun ordine con acconto nel periodo {da} - {a_date.strftime('%Y-%m-%d')}.",
                        parent=self)
            return

        colonne = [
            ("data_inserimento", "Data Ordine"),
            ("cliente", "Cliente"),
            ("acconto", "Acconto (€)"),
            ("prezzo_totale", "Totale Ordine (€)"),
            ("stato_pagamento", "Stato"),
            ("consegnato", "Consegnato"),
            ("progetti", "Progetti")
        ]

        dati = []
        for acconto in acconti:  # 🔥 RINOMINATO per non confondere con la variabile a
            dati.append((
                acconto['data_inserimento'][:10],
                acconto['cliente'],
                f"{acconto['acconto']:.2f}",
                f"{acconto['prezzo_totale']:.2f}" if acconto['prezzo_totale'] else "0.00",
                acconto['stato_pagamento'],
                "✅" if acconto['consegnato'] else "❌",
                acconto['progetti'] or "-"
            ))

        column_types = {"data_inserimento": "date", "acconto": "numeric", "prezzo_totale": "numeric"}

        crea_finestra_con_treeview(
            self,
            f"Ordini con Acconto ({da} - {a_date.strftime('%Y-%m-%d')})",
            colonne,
            dati,
            column_types
        )

    def _aggiorna_grafico_buoni(self, mesi, ricavi_cum, spese_cum, bilancio_cum, dati_buoni_mensili):
        """Aggiorna il grafico includendo i dati dei buoni."""
        self.ax.clear()
        self.ax.grid(True, linestyle='--', alpha=0.4)
        self.ax.set_title("Bilancio cumulativo e movimenti buoni", fontsize=14, color="#5a3e1b")

        x = [datetime.strptime(m, "%Y-%m") for m in mesi]

        # Linee principali
        line_ricavi, = self.ax.plot(x, ricavi_cum, label="Ricavi cumulativi",
                                    color="#5cb85c", linewidth=2)
        line_spese, = self.ax.plot(x, spese_cum, label="Spese cumulative",
                                   color="#d9534f", linewidth=2)
        self.ax.axhline(0, color="black", linewidth=1, alpha=0.6)
        line_bilancio, = self.ax.plot(x, bilancio_cum, label="Bilancio cumulativo",
                                      color="#3366cc", linestyle="--", linewidth=2)

        # 🔥 CORREZIONE: Usa 'creazioni' invece di 'incassi'
        creazioni_mensili = [dati_buoni_mensili['creazioni'].get(m, 0) for m in mesi]
        utilizzi_mensili = [dati_buoni_mensili['utilizzi'].get(m, 0) for m in mesi]

        # Crea un secondo asse y per i buoni
        ax2 = self.ax.twinx()
        ax2.set_ylabel('Movimenti buoni (€)', color='purple')

        # Barre per creazioni buoni
        bars_creazioni = ax2.bar([d for d in x], creazioni_mensili, alpha=0.3,
                                 color='purple', label='Nuovi buoni', width=15)

        # Barre per utilizzi buoni (in negativo per distinguere)
        bars_utilizzi = ax2.bar([d for d in x], [-u for u in utilizzi_mensili], alpha=0.3,
                                color='orange', label='Utilizzi buoni', width=15)

        # Formatta asse x
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.ax.xaxis.set_major_locator(mdates.MonthLocator())
        self.fig.autofmt_xdate(rotation=45)

        # Legende combinate
        lines = [line_ricavi, line_spese, line_bilancio]
        bars = [bars_creazioni, bars_utilizzi]
        labels = [l.get_label() for l in lines] + ['Nuovi buoni', 'Utilizzi buoni']
        self.ax.legend(lines + bars, labels, loc='upper left')

        # Tooltip interattivi
        self._aggiungi_tooltip(lines)

        self.canvas.draw()

    def _aggiorna_dati_buoni(self, dati_buoni):
        """Aggiorna i label con i dati dei buoni."""
        self.valori_buoni["buoni_venduti"].config(text=str(dati_buoni['buoni_venduti']))
        self.valori_buoni["incassato_buoni"].config(text=f"{dati_buoni['totale_incassato']:.2f}")
        self.valori_buoni["utilizzi_buoni"].config(text=str(dati_buoni['utilizzi']))
        self.valori_buoni["valore_utilizzato"].config(text=f"{dati_buoni['totale_utilizzato']:.2f}")
        self.valori_buoni["buoni_residui"].config(text=f"{dati_buoni['valore_residuo_totale']:.2f}")


