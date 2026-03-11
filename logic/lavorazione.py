# logic/lavorazione.py
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from utils.helpers import db_cursor



class LavorazioneManager:
    """Gestisce la logica di business per la lavorazione degli ordini."""

    @staticmethod
    def get_ordini_in_lavorazione() -> List[Dict]:
        """
        Restituisce tutti gli ordini in lavorazione (non ancora consegnati).
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT o.id             AS ordine_id,
                               o.cliente,
                               o.data_inserimento,
                               o.data_consegna,
                               o.data_in_lavorazione,
                               o.prezzo_totale,
                               o.acconto,
                               o.stato_pagamento,
                               po.progetto_id,
                               po.quantita,
                               po.assemblato,
                               po.prezzo_unitario,
                               po.prezzo_totale AS prezzo_progetto_totale
                        FROM ordini o
                                 JOIN progetti_ordinati po ON po.ordine_id = o.id
                        WHERE o.consegnato = 0
                        ORDER BY o.data_inserimento
                        """)

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    @staticmethod
    def get_ordine_dettaglio(ordine_id: int) -> Optional[Dict]:
        """Restituisce i dettagli di un ordine specifico."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT id,
                               cliente,
                               data_inserimento,
                               data_consegna,
                               data_in_lavorazione,
                               prezzo_totale,
                               acconto,
                               stato_pagamento
                        FROM ordini
                        WHERE id = ?
                        """, (ordine_id,))
            row = cur.fetchone()
            if not row:
                return None

            columns = [desc[0] for desc in cur.description]
            dati = dict(zip(columns, row))

            # Assicura che i campi numerici abbiano valori predefiniti
            dati["prezzo_totale"] = dati.get("prezzo_totale") or 0.0
            dati["acconto"] = dati.get("acconto") or 0.0

            return dati

    @staticmethod
    def get_progetti_ordine(ordine_id: int) -> List[Dict]:
        """Restituisce i progetti di un ordine con i relativi dati (prezzi modificati)."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT po.id                                                                             AS progetto_ordinato_id,
                               po.progetto_id,
                               p.nome,
                               po.quantita,
                               po.assemblato,
                               po.prezzo_unitario,
                               po.prezzo_totale,
                               (SELECT COALESCE(disponibili, 0)
                                FROM negozio
                                WHERE progetto_id = po.progetto_id)                                              as disponibili_negozio
                        FROM progetti_ordinati po
                                 JOIN progetti p ON p.id = po.progetto_id
                        WHERE po.ordine_id = ?
                        """, (ordine_id,))

            rows = cur.fetchall()
            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            risultati = []
            for row in rows:
                dati = dict(zip(columns, row))
                dati["assemblato_effettivo"] = max(dati["assemblato"] or 0, dati["disponibili_negozio"] or 0)
                risultati.append(dati)

            return risultati

    @staticmethod
    def get_componenti_mancanti(progetto_ordinato_id: int) -> List[Dict]:
        """
        Restituisce i componenti mancanti per uno specifico progetto_ordinato.
        Considera la cronologia degli ordini: un componente è segnalato come mancante
        solo se era stato rilevato come mancante AL O PRIMA della data dell'ordine.
        """
        with db_cursor() as cur:
            # Recupera il progetto_id e la data dell'ordine da progetti_ordinati
            cur.execute("""
                        SELECT po.progetto_id, o.data_inserimento
                        FROM progetti_ordinati po
                        JOIN ordini o ON o.id = po.ordine_id
                        WHERE po.id = ?
                        """, (progetto_ordinato_id,))
            row = cur.fetchone()
            if not row:
                return []

            progetto_id, data_ordine = row

            # Cerca i componenti mancanti per quel progetto
            # SOLO se erano stati rilevati come mancanti prima o al momento dell'ordine
            cur.execute("""
                        SELECT m.nome,
                               cm.quantita_mancante as quantita,
                               cm.data_rilevamento
                        FROM componenti_mancanti cm
                        JOIN magazzino m ON m.id = cm.componente_id
                        WHERE cm.progetto_id = ?
                        AND cm.data_rilevamento <= ?
                        ORDER BY cm.data_rilevamento DESC
                        """, (progetto_id, data_ordine))

            return [{"nome": row[0], "quantita": row[1], "data": row[2]} for row in cur.fetchall()]

    @staticmethod
    def aggiorna_data_lavorazione(ordine_id: int, data_lavorazione: str) -> bool:
        """Aggiorna la data di inizio lavorazione di un ordine."""
        with db_cursor(commit=True) as cur:
            cur.execute("""
                        UPDATE ordini
                        SET data_in_lavorazione = ?
                        WHERE id = ?
                        """, (data_lavorazione or None, ordine_id))
            return True

    @staticmethod
    def aggiorna_assemblato(progetto_ordinato_id: int, nuova_quantita: int) -> bool:
        """Aggiorna la quantità assemblata di un progetto."""
        with db_cursor(commit=True) as cur:
            cur.execute("""
                        UPDATE progetti_ordinati
                        SET assemblato = ?
                        WHERE id = ?
                        """, (nuova_quantita, progetto_ordinato_id))
            return True

    @staticmethod
    def calcola_stato_ordine(progetti: List[Dict]) -> Dict:
        """
        Calcola lo stato complessivo di un ordine basato sui progetti.
        Restituisce: (totale_quantita, totale_assemblati, stato_testuale, colore)
        """
        tot_quantita = sum(p["quantita"] for p in progetti)
        tot_assemblati = sum(p["assemblato_effettivo"] for p in progetti)

        if tot_assemblati >= tot_quantita:
            stato_testuale = "✅ Tutti"
            colore = "green"
        elif tot_assemblati > 0:
            stato_testuale = "🟠 Parziale"
            colore = "orange"
        else:
            stato_testuale = "❌ Nessuno"
            colore = "red"

        return {
            "totale_quantita": tot_quantita,
            "totale_assemblati": tot_assemblati,
            "stato_testuale": stato_testuale,
            "colore": colore
        }

    @staticmethod
    def verifica_pronto_per_vendita(ordine_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verifica se un ordine è pronto per essere venduto.
        Restituisce (pronto, messaggio, dati_ordine)
        """
        progetti = LavorazioneManager.get_progetti_ordine(ordine_id)
        if not progetti:
            return False, "Nessun progetto trovato per questo ordine", None

        stato = LavorazioneManager.calcola_stato_ordine(progetti)

        if stato["totale_assemblati"] < stato["totale_quantita"]:
            return False, f"Ordine non completo: assemblati {stato['totale_assemblati']}/{stato['totale_quantita']}", None

        ordine = LavorazioneManager.get_ordine_dettaglio(ordine_id)

        return True, "Ordine pronto per la vendita", {
            "ordine": ordine,
            "progetti": progetti,
            "stato": stato
        }

    @staticmethod
    def get_dettaglio_ordine(ordine_id):
        """
        Recupera i dettagli di un ordine specifico.
        """
        from logic.ordini import OrdineManager

        # Usa OrdineManager per i dati base
        dettagli = OrdineManager.get_ordine_dettaglio(ordine_id)

        if not dettagli:
            return None

        # Aggiungi totale e acconto (calcolati o dal DB)
        progetti = OrdineManager.get_progetti_ordinati(ordine_id)
        totale = sum(p["prezzo_totale"] for p in progetti)

        # Acconto (se presente nella tabella acconti_ordini)
        with db_cursor() as cur:
            cur.execute("SELECT SUM(importo) FROM acconti_ordini WHERE ordine_id = ?", (ordine_id,))
            acconto = cur.fetchone()[0] or 0

        return {
            "id": dettagli["id"],
            "cliente": dettagli["cliente"],
            "data_inserimento": dettagli["data_inserimento"],
            "data_consegna": dettagli["data_consegna"],
            "data_in_lavorazione": dettagli.get("data_in_lavorazione"),
            "consegnato": dettagli.get("consegnato", 0),
            "totale": totale,
            "acconto": acconto
        }

class VenditaOrdineManager:
    """Gestisce la vendita degli ordini completati."""

    @staticmethod
    def prepara_dati_per_vendita(ordine_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Prepara i dati dell'ordine per la finestra di vendita.
        Restituisce i dati da passare al dialog di vendita del negozio.
        """
        # Verifica che l'ordine sia pronto
        pronto, msg, dati = LavorazioneManager.verifica_pronto_per_vendita(ordine_id)
        if not pronto:
            return False, msg, None

        # Recupera l'ordine completo
        with db_cursor() as cur:
            cur.execute("""
                        SELECT o.id,
                               o.cliente,
                               o.data_inserimento,
                               o.prezzo_totale as totale_ordine,
                               o.acconto,
                               o.stato_pagamento
                        FROM ordini o
                        WHERE o.id = ?
                        """, (ordine_id,))
            ordine = cur.fetchone()

            if not ordine:
                return False, "Ordine non trovato", None

        # Prepara i dati per il dialog di vendita (formato uguale a quello del negozio)
        items = []
        for progetto in dati["progetti"]:
            items.append({
                "negozio_id": None,  # Non c'è un negozio_id perché viene dall'ordine
                "progetto_id": progetto["progetto_id"],
                "nome_visibile": progetto["nome"],
                "disponibili": progetto["quantita"],  # La quantità dell'ordine
                "prezzo_vendita": progetto["prezzo_unitario"],  # Prezzo unitario dall'ordine
                "prezzo_totale": progetto["prezzo_totale"]  # Prezzo totale dall'ordine
            })

        return True, "Dati preparati", {
            "ordine_id": ordine_id,
            "cliente": ordine[1],
            "items": items,
            "totale_ordine": ordine[3],
            "acconto": ordine[4] or 0,
            "stato_pagamento": ordine[5]
        }

    @staticmethod
    def vendi_ordine(ordine_id: int) -> Tuple[bool, str, int]:
        """
        Converte un ordine completato in vendita nel negozio.
        Usa i prezzi modificati salvati in progetti_ordinati.
        """
        # Verifica che l'ordine sia pronto
        pronto, msg, dati = LavorazioneManager.verifica_pronto_per_vendita(ordine_id)
        if not pronto:
            return False, msg, 0

        progetti_venduti = 0

        with db_cursor(commit=True) as cur:
            for progetto in dati["progetti"]:
                # 🔥 USA I PREZZI MODIFICATI DAL DATABASE
                prezzo_unitario = progetto["prezzo_unitario"]
                prezzo_totale = progetto["prezzo_totale"]

                if not prezzo_unitario or prezzo_unitario <= 0:
                    # Fallback: calcola prezzo dinamico
                    from logic.progetti import Progetto
                    p = Progetto(carica_da_id=progetto["progetto_id"])
                    prezzo_unitario = p.calcola_prezzo()
                    prezzo_totale = prezzo_unitario * progetto["quantita"]

                # Verifica se il progetto esiste già in negozio
                cur.execute("""
                            SELECT id, disponibili
                            FROM negozio
                            WHERE progetto_id = ?
                            """, (progetto["progetto_id"],))
                esistente = cur.fetchone()

                data_inserimento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if esistente:
                    # Aggiorna quantità esistente
                    nuove_disponibili = esistente[1] + progetto["quantita"]
                    cur.execute("""
                                UPDATE negozio
                                SET disponibili      = ?,
                                    data_inserimento = ?
                                WHERE id = ?
                                """, (nuove_disponibili, data_inserimento, esistente[0]))
                else:
                    # Inserisci nuovo record in negozio con i prezzi modificati
                    cur.execute("""
                                INSERT INTO negozio
                                (progetto_id, nome_progetto_negozio, data_inserimento, prezzo_vendita, disponibili,
                                 venduti)
                                SELECT ?, nome, ?, ?, ?, 0
                                FROM progetti
                                WHERE id = ?
                                """, (progetto["progetto_id"], data_inserimento, prezzo_unitario,
                                      progetto["quantita"], progetto["progetto_id"]))

                progetti_venduti += 1

            # Segna l'ordine come consegnato
            cur.execute("""
                        UPDATE ordini
                        SET consegnato = 1
                        WHERE id = ?
                        """, (ordine_id,))

        return True, f"Ordine venduto con successo! {progetti_venduti} progetti in negozio.", progetti_venduti