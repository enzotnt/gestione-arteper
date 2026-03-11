# logic/negozio.py
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from utils.helpers import db_cursor
from logic.progetti import Progetto


class NegozioManager:
    """Gestisce la logica di business per il negozio."""

    @staticmethod
    def get_progetti_in_negozio(ordina_per: str = None, ordine_asc: bool = True, includi_esauriti: bool = True) -> List[
        Dict]:
        """
        Recupera tutti i progetti presenti nel negozio.

        Args:
            ordina_per: campo per ordinamento
            ordine_asc: True per ascendente, False per discendente
            includi_esauriti: Se True, include anche i progetti con disponibili = 0
        """
        with db_cursor(show_errors=False) as cur:
            query = """
                    SELECT n.id as negozio_id,
                           p.id as progetto_id,
                           p.nome,
                           n.data_inserimento,
                           n.disponibili,
                           n.venduti,
                           p.immagine_percorso
                    FROM negozio n
                             JOIN progetti p ON n.progetto_id = p.id \
                    """

            # Aggiungi filtro condizionale
            if not includi_esauriti:
                query += " WHERE n.disponibili > 0"

            cur.execute(query)
            rows = cur.fetchall()

        risultati = []
        for row in rows:
            # Calcola prezzo dinamico
            progetto = Progetto(carica_da_id=row[1])
            prezzo = progetto.calcola_prezzo()

            risultati.append({
                "negozio_id": row[0],
                "progetto_id": row[1],
                "nome": row[2],
                "data_inserimento": row[3][:10] if row[3] else "",
                "disponibili": row[4],
                "venduti": row[5],
                "immagine_percorso": row[6],
                "prezzo": prezzo
            })

        # Ordinamento
        if ordina_per:
            reverse = not ordine_asc
            risultati.sort(key=lambda x: x[ordina_per], reverse=reverse)
        else:
            risultati.sort(key=lambda x: x["nome"])

        return risultati

    @staticmethod
    def get_progetto_da_negozio(negozio_id: int) -> Optional[Dict]:
        """Recupera i dati di un progetto specifico dal negozio."""
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                SELECT n.*, p.nome as nome_progetto
                FROM negozio n
                JOIN progetti p ON n.progetto_id = p.id
                WHERE n.id = ?
            """, (negozio_id,))
            row = cur.fetchone()

        if not row:
            return None

        # Converte la tupla in dizionario usando le descrizioni della colonna
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))

    @staticmethod
    def verifica_disponibilita(negozio_id: int, quantita_richiesta: int) -> Tuple[bool, int, str]:
        """
        Verifica se la quantità richiesta è disponibile.
        Restituisce (disponibile, disponibili_attuali, nome_progetto)
        """
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                SELECT n.disponibili, p.nome
                FROM negozio n
                JOIN progetti p ON n.progetto_id = p.id
                WHERE n.id = ?
            """, (negozio_id,))
            row = cur.fetchone()

        if not row:
            return False, 0, "Progetto non trovato"

        disponibili, nome = row
        return (quantita_richiesta <= disponibili), disponibili, nome

    @staticmethod
    def aggiorna_quantita_negozio(negozio_id: int, quantita_venduta: int) -> Tuple[bool, int, int]:
        """
        Aggiorna le quantità dopo una vendita.
        Restituisce (successo, nuovi_disponibili, nuovi_venduti)
        """
        with db_cursor(commit=True, show_errors=False) as cur:
            cur.execute("""
                        UPDATE negozio
                        SET disponibili = disponibili - ?,
                            venduti     = venduti + ?
                        WHERE id = ?
                          AND disponibili >= ? RETURNING disponibili, venduti
                        """, (quantita_venduta, quantita_venduta, negozio_id, quantita_venduta))

            row = cur.fetchone()
            if not row:
                return False, 0, 0

            return True, row[0], row[1]
        # Il context manager chiude automaticamente la connessione qui

    @staticmethod
    def elimina_da_negozio(negozio_id: int) -> bool:
        """Elimina un progetto dal negozio."""
        with db_cursor(commit=True, show_errors=False) as cur:
            cur.execute("DELETE FROM negozio WHERE id = ?", (negozio_id,))
            return cur.rowcount > 0
        # Chiusura automatica
    @staticmethod
    def cliente_esiste(cliente: str) -> bool:
        """Verifica se un cliente esiste già nella tabella venduti."""
        with db_cursor(show_errors=False) as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM venduti WHERE cliente = ?", (cliente,))
            row = cur.fetchone()
            return row[0] > 0 if row else False


class VenditaManager:
    """Gestisce la logica delle vendite."""

    @staticmethod
    def calcola_costi_progetto(progetto_id: int) -> Tuple[float, List]:
        """
        Calcola il costo totale e i componenti di un progetto.
        Restituisce (costo_totale, lista_componenti)
        """
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                SELECT cp.quantita, m.costo_unitario
                FROM componenti_progetto cp
                JOIN magazzino m ON cp.componente_id = m.id
                WHERE cp.progetto_id = ?
            """, (progetto_id,))
            componenti = cur.fetchall()

        costo_totale = sum(q * cu for q, cu in componenti)
        return costo_totale, componenti

    @staticmethod
    def registra_vendita(negozio_id: int, progetto_id: int, cliente: str,
                         quantita: int, prezzo_totale: float, prezzo_unitario: float,
                         note: str = "", codice_sconto: str = None,
                         nome_progetto: str = None, **kwargs) -> int:
        """
        Registra una vendita nel database.

        Args:
            negozio_id: ID del negozio
            progetto_id: ID del progetto
            cliente: nome del cliente
            quantita: quantità venduta
            prezzo_totale: prezzo totale della vendita
            prezzo_unitario: prezzo unitario
            note: note aggiuntive
            codice_sconto: codice sconto utilizzato (opzionale)
            nome_progetto: nome del progetto (se None, viene recuperato dal DB)
            **kwargs: parametri aggiuntivi ignorati (per compatibilità)

        Returns:
            int: ID della vendita inserita
        """
        with db_cursor(commit=True, show_errors=False) as cur:
            # Calcola costi
            costo_totale, _ = VenditaManager.calcola_costi_progetto(progetto_id)
            costo_totale_vendita = costo_totale * quantita
            ricavo = prezzo_totale - costo_totale_vendita

            # 🔥 MODIFICA: usa nome_progetto se fornito, altrimenti recuperalo dal DB
            if nome_progetto is not None:
                nome = nome_progetto
            else:
                cur.execute("SELECT nome FROM progetti WHERE id = ?", (progetto_id,))
                row = cur.fetchone()
                nome = row[0] if row else "[Progetto non trovato]"

            # Aggiungi codice sconto alle note se presente
            if codice_sconto:
                if note:
                    note = f"[CODICE SCONTO: {codice_sconto}] {note}"
                else:
                    note = f"[CODICE SCONTO: {codice_sconto}]"

            # Inserisci vendita
            cur.execute("""
                        INSERT INTO venduti (negozio_id, data_vendita, cliente, quantita,
                                             prezzo_totale, prezzo_unitario,
                                             costo_totale, ricavo, note, nome)
                        VALUES (?, CURRENT_DATE, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            negozio_id, cliente, quantita, prezzo_totale,
                            prezzo_unitario, costo_totale_vendita, ricavo, note, nome
                        ))

            return cur.lastrowid
    @staticmethod
    def get_vendite_cliente(cliente: str) -> List[Dict]:
        """Recupera tutte le vendite di un cliente."""
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                SELECT *
                FROM venduti
                WHERE cliente = ?
                ORDER BY data_vendita DESC
            """, (cliente,))
            rows = cur.fetchall()

        if not rows:
            return []

        # Converte in dizionari usando le descrizioni delle colonne
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]