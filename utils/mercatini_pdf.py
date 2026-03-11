# utils/mercatini_pdf.py
import os
import re
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

# File JSON dove sono salvati i progetti del mercatino
MERCATINO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mercatino_progetti.json")


def esporta_mercatini_pdf(
        output_dir="export",
        filename=None,
        luogo_data_mercatino=None,
        prefilled_nome_cognome="",
        prefilled_tessera="",
        prefilled_rilasciato_il="",
        prefilled_comune="",
        include_totals=True,
        orientamento_landscape=True,
        progetti=None  # <-- NUOVO PARAMETRO
):
    """
    Esporta i progetti del mercatino in un file PDF pronto per la stampa.

    Args:
        output_dir: directory di output
        filename: nome del file (se None, generato automaticamente)
        luogo_data_mercatino: testo per l'intestazione
        prefilled_nome_cognome: nome espositore
        prefilled_tessera: numero tesserino
        prefilled_rilasciato_il: data rilascio
        prefilled_comune: comune di rilascio
        include_totals: se includere riga totale
        orientamento_landscape: se usare landscape (True) o portrait (False)
        progetti: lista di progetti già ordinati (se None, carica dal JSON)

    Returns:
        str: percorso del file PDF creato
    """
    # Crea directory di output se non esiste
    os.makedirs(output_dir, exist_ok=True)

    # Genera nome file
    filename = _genera_nome_file(filename, luogo_data_mercatino)
    out_path = os.path.join(output_dir, filename)

    # 🔥 MODIFICATO: Usa i progetti passati se disponibili, altrimenti carica dal JSON
    if progetti is None:
        progetti = _carica_dati_da_json()
        print(f"📄 Caricati {len(progetti)} progetti dal file JSON")
    else:
        print(f"📄 Usati {len(progetti)} progetti già ordinati dalla GUI")

    if not progetti:
        raise Exception("Nessun prodotto nel mercatino da esportare.")

    # Prepara dati per la tabella
    table_data, totali = _prepara_dati_tabella(progetti, include_totals)

    # Genera PDF
    return _genera_pdf(
        out_path, table_data, totali,
        luogo_data_mercatino, orientamento_landscape,
        prefilled_nome_cognome, prefilled_tessera,
        prefilled_rilasciato_il, prefilled_comune
    )

def _carica_dati_da_json():
    """Carica i progetti dal file JSON del mercatino."""
    if not os.path.exists(MERCATINO_FILE):
        print(f"File JSON non trovato: {MERCATINO_FILE}")
        return []

    try:
        with open(MERCATINO_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Caricati {len(data)} progetti dal file JSON")
            return data
    except Exception as e:
        print(f"Errore nel caricamento del file JSON: {e}")
        return []


def _genera_nome_file(filename: str, luogo_data_mercatino: str) -> str:
    """Genera il nome del file in base ai parametri."""
    if filename:
        return filename

    if luogo_data_mercatino:
        clean_name = re.sub(r'[^A-Za-z0-9_\-\s/]', '', luogo_data_mercatino)
        clean_name = clean_name.replace(" ", "_").replace("/", "-")
        return f"{clean_name}.pdf"

    return f"Mercatino_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.pdf"


def _prepara_dati_tabella(progetti, include_totals):
    """
    Prepara i dati per la tabella PDF.
    Restituisce (table_data, totali)
    """
    # Intestazione
    table_data = [["Nome oggetto", "Prezzo (€)", "Quantità", "Note"]]
    totale_pezzi = 0
    totale_valore = 0.0

    # Dati
    for prog in progetti:
        nome = prog.get("nome", "")
        prezzo = prog.get("prezzo", 0)
        quantita = prog.get("quantita", 0)
        note = prog.get("note", "")

        table_data.append([
            nome,
            f"{prezzo:.2f}",
            str(quantita),
            note
        ])

        totale_pezzi += quantita
        totale_valore += prezzo * quantita

    # Riga totale
    if include_totals:
        table_data.append([
            "TOTALE",
            f"{totale_valore:.2f}",
            str(totale_pezzi),
            ""
        ])

    return table_data, {"pezzi": totale_pezzi, "valore": totale_valore}


def _prepara_dati_tabella(progetti, include_totals):
    """
    Prepara i dati per la tabella PDF.
    Restituisce (table_data, totali)
    """
    # Intestazione
    table_data = [["Nome oggetto", "Prezzo", "Quantità", "Note"]]  # <-- Rimosso (€)
    totale_pezzi = 0
    totale_valore = 0.0

    # Dati
    for prog in progetti:
        nome = prog.get("nome", "")
        prezzo = prog.get("prezzo", "")
        quantita = prog.get("quantita", "")
        note = prog.get("note", "")

        # 🔴 NON formattare il prezzo come numero, lascialo come stringa
        row = [
            nome,
            str(prezzo),  # <-- Garantisce che sia stringa
            str(quantita),  # <-- Garantisce che sia stringa
            note
        ]
        table_data.append(row)

        # Prova a convertire in numero solo per i totali (se possibile)
        try:
            # Sostituisci virgola con punto e converti
            prezzo_num = float(str(prezzo).replace(',', '.'))
            quantita_num = float(str(quantita))
            totale_valore += prezzo_num * quantita_num
        except (ValueError, TypeError):
            # Se non è un numero valido, non lo contiamo nei totali
            pass

        try:
            totale_pezzi += float(quantita)
        except (ValueError, TypeError):
            pass

    # Riga totale
    if include_totals:
        # Formatta i totali solo se sono numeri validi
        totale_valore_str = f"{totale_valore:.2f}" if totale_valore > 0 else "-"
        totale_pezzi_str = str(int(totale_pezzi)) if totale_pezzi > 0 else "-"

        table_data.append([
            "TOTALE",
            totale_valore_str,
            totale_pezzi_str,
            ""
        ])

    return table_data, {"pezzi": totale_pezzi, "valore": totale_valore}


def _genera_pdf(out_path, table_data, totali,
                luogo_data_mercatino, orientamento_landscape,
                prefilled_nome_cognome, prefilled_tessera,
                prefilled_rilasciato_il, prefilled_comune, ):
    """
    Genera il file PDF con i dati forniti.
    """
    # Configurazione pagina
    page_size = landscape(A4) if orientamento_landscape else A4
    doc = SimpleDocTemplate(
        out_path,
        pagesize=page_size,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    # Stili
    styles = getSampleStyleSheet()
    style_bold = ParagraphStyle('bold', parent=styles['Normal'],
                                fontName='Helvetica-Bold', fontSize=12)
    style_normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=10)

    elements = []

    # Intestazione principale
    elements.append(Paragraph("<b>ELENCO PRODOTTI PER MERCATINO</b>", style_bold))
    elements.append(Spacer(1, 0.2 * cm))

    # Luogo e data
    if not luogo_data_mercatino:
        luogo_data_mercatino = f"Luogo non specificato - {datetime.now().strftime('%d/%m/%Y')}"
    elements.append(Paragraph(f"<b>Luogo e data:</b> {luogo_data_mercatino}", style_normal))
    elements.append(Spacer(1, 0.2 * cm))

    # Info espositore
    info = [
        ["Espositore:", prefilled_nome_cognome],
        ["Tesserino N°:", prefilled_tessera],
        ["Rilasciato il:", prefilled_rilasciato_il],
        ["Comune:", prefilled_comune],
    ]
    for lbl, val in info:
        elements.append(Paragraph(f"<b>{lbl}</b> {val}", style_normal))
    elements.append(Spacer(1, 0.4 * cm))

    # Tabella prodotti
    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(t)
    elements.append(Spacer(1, 0.4 * cm))

    # 🔴 Riepilogo - gestione sicura dei totali
    # Totale pezzi
    if totali['pezzi'] > 0:
        pezzi_str = str(int(totali['pezzi']))
    else:
        pezzi_str = "-"
    elements.append(Paragraph(f"<b>Totale pezzi:</b> {pezzi_str}", style_normal))

    # Valore totale
    if totali['valore'] > 0:
        valore_str = f"€ {totali['valore']:.2f}"
    else:
        valore_str = "-"
    elements.append(Paragraph(f"<b>Valore totale:</b> {valore_str}", style_normal))

    elements.append(Spacer(1, 0.4 * cm))

    # Firma
    elements.append(Paragraph("<b>Firma dell'espositore: ____________________________</b>", style_normal))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph("<i>Documento da esibire in caso di controllo.</i>", style_normal))

    # Genera PDF
    doc.build(elements)

    return out_path