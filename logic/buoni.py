# logic/buoni.py
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from utils.helpers import db_cursor


class BuonoManager:
    """Gestisce la logica dei buoni regalo/sconto."""

    @staticmethod
    def genera_codice(lunghezza: int = 8) -> str:
        """
        Genera un codice univoco per il buono.
        Formato: LETTERE-NUMERI (es. ARTE-4F9K)
        """
        while True:
            # Genera codice: 4 lettere + trattino + 4 caratteri alfanumerici
            parte1 = ''.join(random.choices(string.ascii_uppercase, k=4))
            parte2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            codice = f"{parte1}-{parte2}"

            # Verifica che il codice sia univoco
            with db_cursor() as cur:
                cur.execute("SELECT id FROM buoni WHERE codice = ?", (codice,))
                if not cur.fetchone():
                    return codice

    @staticmethod
    def crea_buono(
            tipo: str,
            valore: float,
            cliente_acquirente: str,
            cliente_beneficiario: str = "",
            giorni_scadenza: Optional[int] = None,
            note: str = "",
            incassato: float = None,  # Se None, usa il valore del buono
            metodo_pagamento: str = ""
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Crea un nuovo buono regalo/sconto.

        Args:
            tipo: 'REGALO' o 'SCONTO'
            valore: valore nominale del buono
            cliente_acquirente: chi acquista il buono
            cliente_beneficiario: a chi è intestato
            giorni_scadenza: giorni di validità
            note: note aggiuntive
            incassato: quanto è stato effettivamente pagato (None = tutto il valore)
            metodo_pagamento: come è stato pagato
        """
        try:
            codice = BuonoManager.genera_codice()
            data_creazione = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Se incassato non specificato, usa il valore totale
            if incassato is None:
                incassato = valore

            # Data incasso (solo se c'è un importo incassato)
            data_incasso = data_creazione if incassato > 0 else None

            data_scadenza = None
            if giorni_scadenza:
                data_scadenza = (datetime.now() + timedelta(days=giorni_scadenza)).strftime("%Y-%m-%d")

            with db_cursor(commit=True) as cur:
                cur.execute("""
                            INSERT INTO buoni (codice, tipo, valore_originale, valore_residuo,
                                               data_creazione, data_scadenza, cliente_acquirente,
                                               cliente_beneficiario, note, stato, incassato, data_incasso,
                                               metodo_pagamento)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATTIVO', ?, ?, ?)
                            """, (
                                codice, tipo, valore, valore,
                                data_creazione, data_scadenza,
                                cliente_acquirente, cliente_beneficiario, note,
                                incassato, data_incasso, metodo_pagamento
                            ))

                buono_id = cur.lastrowid
                cur.execute("SELECT * FROM buoni WHERE id = ?", (buono_id,))
                columns = [desc[0] for desc in cur.description]
                buono = dict(zip(columns, cur.fetchone()))

            return True, f"Buono {codice} creato con successo", buono

        except Exception as e:
            return False, f"Errore nella creazione del buono: {e}", None

    @staticmethod
    def valida_buono(codice: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verifica se un buono è valido e attivo.

        Returns:
            (valido, messaggio, dati_buono)
        """
        with db_cursor() as cur:
            cur.execute("SELECT * FROM buoni WHERE codice = ?", (codice,))
            row = cur.fetchone()

            if not row:
                return False, "Codice buono non trovato", None

            columns = [desc[0] for desc in cur.description]
            buono = dict(zip(columns, row))

            # Verifica stato
            if buono['stato'] != 'ATTIVO':
                return False, f"Buono non valido (stato: {buono['stato']})", buono

            # Verifica scadenza
            if buono['data_scadenza']:
                data_scad = datetime.strptime(buono['data_scadenza'], "%Y-%m-%d")
                if data_scad < datetime.now():
                    return False, "Buono scaduto", buono

            # Verifica valore residuo
            if buono['valore_residuo'] <= 0:
                return False, "Buono già esaurito", buono

            return True, "Buono valido", buono

    @staticmethod
    def applica_sconto(
            codice: str,
            importo_spesa: float,
            vendita_id: Optional[int] = None
    ) -> Tuple[bool, str, float]:
        """
        Applica un buono a una spesa.

        Returns:
            (successo, messaggio, nuovo_importo)
        """
        valido, msg, buono = BuonoManager.valida_buono(codice)
        if not valido:
            return False, msg, importo_spesa

        with db_cursor(commit=True) as cur:
            if buono['tipo'] == 'REGALO':
                # Buono regalo: scalare dall'importo totale
                importo_da_scalare = min(buono['valore_residuo'], importo_spesa)
                nuovo_importo = importo_spesa - importo_da_scalare

                nuovo_residuo = buono['valore_residuo'] - importo_da_scalare

            else:  # SCONTO PERCENTUALE (ipotizziamo 10% come default)
                percentuale = buono['valore_originale']  # es. 10 = 10%
                importo_sconto = importo_spesa * (percentuale / 100)
                nuovo_importo = importo_spesa - importo_sconto
                importo_da_scalare = importo_sconto
                nuovo_residuo = 0  # gli sconti percentuali si esauriscono in un uso

            # Aggiorna il buono
            nuovo_stato = 'UTILIZZATO' if nuovo_residuo <= 0 else 'ATTIVO'
            cur.execute("""
                        UPDATE buoni
                        SET valore_residuo = ?,
                            stato          = ?
                        WHERE id = ?
                        """, (nuovo_residuo, nuovo_stato, buono['id']))

            # Registra l'utilizzo
            cur.execute("""
                        INSERT INTO utilizzi_buoni (buono_id, vendita_id, data_utilizzo, importo_utilizzato)
                        VALUES (?, ?, ?, ?)
                        """,
                        (buono['id'], vendita_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), importo_da_scalare))

        return True, f"Buono applicato: sconto di €{importo_da_scalare:.2f}", nuovo_importo

    @staticmethod
    def get_lista_buoni(
            stato: Optional[str] = None,
            tipo: Optional[str] = None,
            ordina_per: str = "data_creazione",
            ordine_asc: bool = False
    ) -> List[Dict]:
        """Recupera la lista dei buoni con filtri opzionali."""
        with db_cursor() as cur:
            query = "SELECT * FROM buoni WHERE 1=1"
            params = []

            if stato:
                query += " AND stato = ?"
                params.append(stato)

            if tipo:
                query += " AND tipo = ?"
                params.append(tipo)

            query += f" ORDER BY {ordina_per} {'ASC' if ordine_asc else 'DESC'}"

            cur.execute(query, params)
            rows = cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_utilizzi_buono(buono_id: int) -> List[Dict]:
        """Recupera lo storico degli utilizzi di un buono."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT u.*, v.cliente, v.data_vendita
                        FROM utilizzi_buoni u
                                 LEFT JOIN venduti v ON u.vendita_id = v.id
                        WHERE u.buono_id = ?
                        ORDER BY u.data_utilizzo DESC
                        """, (buono_id,))
            rows = cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def applica_utilizzo(buono_id: int, importo_utilizzato: float, vendita_id: int = None) -> Tuple[bool, str]:
        """
        Applica un utilizzo a un buono, aggiornando il valore residuo.

        Returns:
            (successo, messaggio)
        """
        with db_cursor(commit=True) as cur:
            # Recupera il buono
            cur.execute("SELECT * FROM buoni WHERE id = ?", (buono_id,))
            row = cur.fetchone()

            if not row:
                return False, "Buono non trovato"

            columns = [desc[0] for desc in cur.description]
            buono = dict(zip(columns, row))

            # Calcola nuovo valore residuo
            nuovo_residuo = buono['valore_residuo'] - importo_utilizzato
            if nuovo_residuo < 0:
                return False, "Importo utilizzato superiore al valore residuo"

            # Determina nuovo stato
            if nuovo_residuo <= 0:
                nuovo_stato = 'UTILIZZATO'
            else:
                nuovo_stato = buono['stato']  # rimane ATTIVO

            # Aggiorna il buono
            cur.execute("""
                        UPDATE buoni
                        SET valore_residuo = ?,
                            stato          = ?
                        WHERE id = ?
                        """, (nuovo_residuo, nuovo_stato, buono_id))

            # Registra l'utilizzo
            cur.execute("""
                        INSERT INTO utilizzi_buoni (buono_id, vendita_id, data_utilizzo, importo_utilizzato)
                        VALUES (?, ?, ?, ?)
                        """, (buono_id, vendita_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), importo_utilizzato))

            return True, f"Buono aggiornato: residuo €{nuovo_residuo:.2f}"

    @staticmethod
    def annulla_buono(buono_id: int, motivazione: str = "") -> bool:
        """Annulla un buono (es. per smarrimento)."""
        with db_cursor(commit=True) as cur:
            cur.execute("""
                        UPDATE buoni
                        SET stato = 'ANNULLATO',
                            note  = note || ?
                        WHERE id = ?
                          AND stato = 'ATTIVO'
                        """, (f"\nANNULLATO: {motivazione}", buono_id))
            return cur.rowcount > 0

    @staticmethod
    def registra_utilizzo(buono_id: int, vendita_id: int, importo_utilizzato: float) -> Tuple[bool, str]:
        """
        Registra l'utilizzo di un buono in una vendita.

        Returns:
            (successo, messaggio)
        """
        with db_cursor(commit=True) as cur:
            # Recupera il buono
            cur.execute("SELECT * FROM buoni WHERE id = ?", (buono_id,))
            row = cur.fetchone()

            if not row:
                return False, "Buono non trovato"

            columns = [desc[0] for desc in cur.description]
            buono = dict(zip(columns, row))

            # Calcola nuovo valore residuo
            nuovo_residuo = buono['valore_residuo'] - importo_utilizzato
            if nuovo_residuo < 0:
                return False, "Importo utilizzato superiore al valore residuo"

            # Determina nuovo stato
            if nuovo_residuo <= 0:
                nuovo_stato = 'UTILIZZATO'
            else:
                nuovo_stato = buono['stato']  # rimane ATTIVO

            # Aggiorna il buono
            cur.execute("""
                        UPDATE buoni
                        SET valore_residuo = ?,
                            stato          = ?
                        WHERE id = ?
                        """, (nuovo_residuo, nuovo_stato, buono_id))

            # Registra l'utilizzo
            cur.execute("""
                        INSERT INTO utilizzi_buoni (buono_id, vendita_id, data_utilizzo, importo_utilizzato)
                        VALUES (?, ?, ?, ?)
                        """, (buono_id, vendita_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), importo_utilizzato))

            return True, f"Buono aggiornato: residuo €{nuovo_residuo:.2f}"