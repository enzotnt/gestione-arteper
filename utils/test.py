# logic/negozio_pdf.py
import os
import re
from datetime import datetime
import sqlite3
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

from db.database import get_connection
from utils.helpers import db_cursor  # Anche se non usato qui, per coerenza


def esporta_mercatini_pdf(
        table="negozio",
        output_dir="export",
        filename=None,
        luogo_data_mercatino=None,
        prefilled_nome_cognome="",
        prefilled_tessera="",
        prefilled_rilasciato_il="",
        prefilled_comune="",
        include_totals=True,
        orientamento_landscape=True
):
    """
    Esporta la tabella 'negozio' in un file PDF pronto per la stampa per uso mercatino.

    Args:
        table: nome della tabella da esportare
        output_dir: directory di output
        filename: nome del file (se None, generato automaticamente)
        luogo_data_mercatino: testo per l'intestazione
        prefilled_nome_cognome: nome espositore
        prefilled_tessera: numero tesserino
        prefilled_rilasciato_il: data rilascio
        prefilled_comune: comune di rilascio
        include_totals: se includere riga totale
        orientamento_landscape: se usare landscape (True) o portrait (False)

    Returns:
        str: percorso del file PDF creato
    """
    # Crea directory di output se non esiste
    os.makedirs(output_dir, exist_ok=True)

    # Genera nome file
    filename = _genera_nome_file(filename, luogo_data_mercatino)
    out_path = os.path.join(output_dir, filename)

    # Verifica esistenza tabella e recupera dati
    rows, columns = _get_dati_negozio(table)

    if not rows:
        raise Exception("Nessun prodotto con quantità esposta maggiore di 0 trovato.")

    # Prepara dati per la tabella
    header_map = {
        "nome_progetto_negozio": "Nome oggetto",
        "data_inserimento": "Data inserimento",
        "prezzo_vendita": "Prezzo (€)",
        "disponibili": "Q.tà esposta",
        "venduti": "Venduti"
    }

    table_data, total_disponibili = _prepara_dati_tabella(rows, columns, header_map, include_totals)

    # Genera PDF
    return _genera_pdf(
        out_path, table_data, total_disponibili,
        luogo_data_mercatino, orientamento_landscape,
        prefilled_nome_cognome, prefilled_tessera,
        prefilled_rilasciato_il, prefilled_comune
    )


def _genera_nome_file(filename: str, luogo_data_mercatino: str) -> str:
    """Genera il nome del file in base ai parametri."""
    if filename:
        return filename

    if luogo_data_mercatino:
        clean_name = re.sub(r'[^A-Za-z0-9_\-\s/]', '', luogo_data_mercatino)
        clean_name = clean_name.replace(" ", "_").replace("/", "-")
        return f"{clean_name}.pdf"

    return f"Mercatino_senza_nome_{datetime.now().strftime('%Y-%m-%d')}.pdf"


def _get_dati_negozio(table: str):
    """
    Recupera i dati dal database.
    Restituisce (rows, columns)
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # Verifica che la tabella esista
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
        if cur.fetchone() is None:
            raise Exception(f"Tabella '{table}' non trovata.")

        # Colonne da esportare
        columns = [
            "nome_progetto_negozio",
            "data_inserimento",
            "prezzo_vendita",
            "disponibili",
            "venduti"
        ]

        # Query dati
        sql = f'''
            SELECT {", ".join([f'"{c}"' for c in columns])}
            FROM "{table}"
            WHERE COALESCE(disponibili, 0) > 0
            ORDER BY nome_progetto_negozio COLLATE NOCASE
        '''
        cur.execute(sql)
        rows = cur.fetchall()

        return rows, columns

    finally:
        conn.close()


def _prepara_dati_tabella(rows, columns, header_map, include_totals):
    """
    Prepara i dati per la tabella PDF.
    Restituisce (table_data, total_disponibili)
    """
    # Intestazione
    table_data = [[header_map[c] for c in columns]]
    total_disponibili = 0

    # Dati
    for r in rows:
        row_data = []
        for c in columns:
            if c == "venduti":
                v = ""  # Lasciamo vuota la colonna venduti
            else:
                v = r[c]
                # Formatta data se necessario
                if c == "data_inserimento" and isinstance(v, str) and len(v) >= 10:
                    v = v[:10]
            row_data.append(v)
        table_data.append(row_data)

        try:
            total_disponibili += int(r["disponibili"] or 0)
        except (ValueError, TypeError):
            pass

    # Riga totale
    if include_totals:
        totals_row = []
        for c in columns:
            if c == columns[0]:
                totals_row.append("TOTALE")
            elif c == "disponibili":
                totals_row.append(total_disponibili)
            elif c == "venduti":
                totals_row.append("")
            else:
                totals_row.append("")
        table_data.append(totals_row)

    return table_data, total_disponibili


def _genera_pdf(out_path, table_data, total_disponibili,
                luogo_data_mercatino, orientamento_landscape,
                prefilled_nome_cognome, prefilled_tessera,
                prefilled_rilasciato_il, prefilled_comune):
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
    elements.append(Paragraph("<b>ELENCO PRODOTTI ESPOSTI</b>", style_bold))
    elements.append(Spacer(1, 0.2 * cm))

    # Luogo e data
    if not luogo_data_mercatino:
        luogo_data_mercatino = f"Luogo non specificato - {datetime.now().strftime('%d/%m/%Y')}"
    elements.append(Paragraph(f"<b>Luogo e data mercatino:</b> {luogo_data_mercatino}", style_normal))
    elements.append(Spacer(1, 0.2 * cm))

    # Info espositore
    info = [
        ["Nome e Cognome:", prefilled_nome_cognome],
        ["Tesserino N°:", prefilled_tessera],
        ["Rilasciato il:", prefilled_rilasciato_il],
        ["Dal comune di:", prefilled_comune],
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
    ]))

    elements.append(t)
    elements.append(Spacer(1, 0.6 * cm))

    # Firma e note legali
    elements.append(Paragraph("<b>Firma dell'espositore: ____________________________</b>", style_normal))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph("<i>Documento da esibire in caso di controllo.</i>", style_normal))

    # Genera PDF
    doc.build(elements)

    return out_path