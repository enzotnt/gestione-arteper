# logic/venduti.py
import sqlite3
from datetime import datetime
from db.database import get_connection
from typing import List, Dict, Any, Optional, Tuple


class VendutiManager:
    """Gestisce la logica di business per le vendite."""

    @staticmethod
    def get_vendite_aggregate() -> List[Dict]:
        """
        Recupera tutte le vendite e le raggruppa per cliente.
        Restituisce una lista di dizionari con i dati aggregati per cliente.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
                  SELECT v.cliente                                                            AS cliente,
                         COALESCE(p.nome, v.nome)                                             AS progetto_nome,
                         v.quantita                                                           AS quantita,
                         v.prezzo_unitario                                                    AS prezzo_unitario,
                         COALESCE(v.prezzo_totale, v.quantita * IFNULL(v.prezzo_unitario, 0)) AS prezzo_totale,
                         v.data_vendita                                                       AS data_vendita
                  FROM venduti v
                           LEFT JOIN negozio n ON v.negozio_id = n.id
                           LEFT JOIN progetti p ON n.progetto_id = p.id
                  ORDER BY v.cliente COLLATE NOCASE, v.data_vendita DESC
                  """)
        righe = c.fetchall()
        conn.close()

        # Raggruppa per cliente in Python
        clienti = {}
        for r in righe:
            cliente = (r["cliente"] or "").strip() or "[Cliente non specificato]"
            proj = r["progetto_nome"] or "[Sconosciuto]"
            qta = int(r["quantita"] or 0)
            unit = float(r["prezzo_unitario"] or 0.0)
            tot = float(r["prezzo_totale"] or (qta * unit))
            data = r["data_vendita"]

            if cliente not in clienti:
                clienti[cliente] = {
                    "items": {},  # progetto -> {'qta': X, 'unit': unit, 'tot': Y}
                    "quantita_tot": 0,
                    "totale": 0.0,
                    "ultima_data": data
                }

            # accumula quantità e totali per progetto
            items = clienti[cliente]["items"]
            if proj not in items:
                items[proj] = {"qta": 0, "unit": unit, "tot": 0.0}
            items[proj]["qta"] += qta
            items[proj]["unit"] = unit
            items[proj]["tot"] += tot

            clienti[cliente]["quantita_tot"] += qta
            clienti[cliente]["totale"] += tot

            # aggiorna ultima_data (max)
            try:
                if data and (not clienti[cliente]["ultima_data"] or data > clienti[cliente]["ultima_data"]):
                    clienti[cliente]["ultima_data"] = data
            except Exception:
                pass

        # Trasforma in lista ordinata
        risultati = []
        for cliente, info in sorted(clienti.items(), key=lambda t: t[0].lower()):
            items_list = []
            for proj, dat in info["items"].items():
                items_list.append({
                    "progetto": proj,
                    "quantita": dat["qta"],
                    "prezzo_unitario": dat["unit"],
                    "totale": dat["tot"]
                })

            risultati.append({
                "cliente": cliente,
                "items": items_list,
                "quantita_totale": info["quantita_tot"],
                "totale": info["totale"],
                "ultima_data": info["ultima_data"]
            })

        return risultati

    @staticmethod
    def get_vendite_dettaglio() -> List[Dict]:
        """
        Recupera tutte le vendite in formato dettaglio (una riga per vendita).
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
                  SELECT v.id,
                         v.data_vendita           AS data,
                         v.cliente,
                         v.quantita,
                         v.prezzo_totale,
                         v.prezzo_unitario,
                         v.costo_totale,
                         v.ricavo,
                         v.note,
                         v.immagine_percorso,
                         COALESCE(p.nome, v.nome) AS progetto_nome,
                         p.percorso               AS percorso_progetto
                  FROM venduti v
                           LEFT JOIN negozio n ON v.negozio_id = n.id
                           LEFT JOIN progetti p ON n.progetto_id = p.id
                  ORDER BY v.data_vendita DESC
                  """)
        righe = c.fetchall()
        conn.close()

        risultati = []
        for r in righe:
            risultati.append({
                "id": r["id"],
                "data": r["data"],
                "cliente": r["cliente"],
                "quantita": r["quantita"],
                "prezzo_totale": r["prezzo_totale"],
                "prezzo_unitario": r["prezzo_unitario"],
                "costo_totale": r["costo_totale"],
                "ricavo": r["ricavo"],
                "note": r["note"],
                "immagine_percorso": r["immagine_percorso"],
                "progetto_nome": r["progetto_nome"],
                "percorso_progetto": r["percorso_progetto"]
            })

        return risultati

    @staticmethod
    def get_vendite_cliente(cliente_nome: str) -> List[Dict]:
        """
        Recupera tutte le vendite di un cliente specifico.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
                  SELECT v.id,
                         v.data_vendita,
                         v.nome AS v_nome,
                         p.nome AS p_nome,
                         CASE
                             -- PRIMA controlla v.nome (che è corretto)
                             WHEN v.nome IS NOT NULL AND v.nome != '' AND v.nome != 'ORDINI CLIENTI' AND v.nome != '🔹 ORDINI CLIENTI' THEN v.nome
                    -- POI come fallback p.nome
                    WHEN p.nome IS NOT NULL AND p.nome != '' AND p.nome != 'ORDINI CLIENTI' AND p.nome != '🔹 ORDINI CLIENTI' THEN p.nome
                    ELSE 'Progetto sconosciuto'
                  END
                  AS progetto,
                v.quantita,
                v.prezzo_unitario,
                v.prezzo_totale
            FROM venduti v
            LEFT JOIN negozio n ON v.negozio_id = n.id
            LEFT JOIN progetti p ON n.progetto_id = p.id
            WHERE v.cliente = ?
            ORDER BY v.data_vendita DESC
                  """, (cliente_nome,))

        righe = c.fetchall()
        conn.close()

        risultati = []
        for r in righe:
            risultati.append({
                "id": r["id"],
                "data": r["data_vendita"],
                "progetto": r["progetto"],
                "quantita": r["quantita"],
                "prezzo_unitario": r["prezzo_unitario"],
                "prezzo_totale": r["prezzo_totale"]
            })

        return risultati

    @staticmethod
    def get_dettaglio_vendita(vendita_id: int) -> Optional[Dict]:
        """
        Recupera i dettagli di una singola vendita.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
                  SELECT v.id,
                         v.data_vendita,
                         v.cliente,
                         v.quantita,
                         v.prezzo_totale,
                         v.prezzo_unitario,
                         v.costo_totale,
                         v.ricavo,
                         v.note,
                         v.immagine_percorso,
                         COALESCE(p.nome, v.nome) AS nome,
                         p.percorso               AS percorso_progetto
                  FROM venduti v
                           LEFT JOIN negozio n ON v.negozio_id = n.id
                           LEFT JOIN progetti p ON n.progetto_id = p.id
                  WHERE v.id = ?
                  """, (vendita_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row["id"],
            "data": row["data_vendita"],
            "cliente": row["cliente"],
            "quantita": row["quantita"],
            "prezzo_totale": row["prezzo_totale"],
            "prezzo_unitario": row["prezzo_unitario"],
            "costo_totale": row["costo_totale"],
            "ricavo": row["ricavo"],
            "note": row["note"],
            "immagine_percorso": row["immagine_percorso"],
            "progetto_nome": row["nome"],
            "percorso_progetto": row["percorso_progetto"]
        }

    @staticmethod
    def elimina_vendita(vendita_id: int) -> bool:
        """
        Elimina una vendita dal database.
        """
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM venduti WHERE id = ?", (vendita_id,))
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise Exception(f"Errore durante l'eliminazione: {e}")
        finally:
            conn.close()

    @staticmethod
    def aggiorna_vendita(vendita_id: int, note: str, immagine_percorso: Optional[str],
                         percorso_progetto: Optional[str] = None) -> bool:
        """
        Aggiorna i dati di una vendita (note, immagine).
        Se percorso_progetto è fornito, aggiorna anche il percorso del progetto associato.
        """
        conn = get_connection()
        c = conn.cursor()
        try:
            # Aggiorna la tabella venduti
            c.execute("""
                      UPDATE venduti
                      SET note              = ?,
                          immagine_percorso = ?
                      WHERE id = ?
                      """, (note, immagine_percorso, vendita_id))

            # Se c'è un percorso da aggiornare, cerca il progetto associato
            if percorso_progetto:
                c.execute("SELECT negozio_id FROM venduti WHERE id = ?", (vendita_id,))
                row = c.fetchone()
                if row and row[0]:
                    c.execute("SELECT progetto_id FROM negozio WHERE id = ?", (row[0],))
                    row2 = c.fetchone()
                    if row2:
                        c.execute("""
                                  UPDATE progetti
                                  SET percorso = ?
                                  WHERE id = ?
                                  """, (percorso_progetto, row2[0]))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise Exception(f"Errore durante l'aggiornamento: {e}")
        finally:
            conn.close()

    @staticmethod
    def format_items_string(items: List[Dict]) -> str:
        """
        Formatta la lista degli items per la visualizzazione aggregata.
        Esempio: "Lampada Cuore (2x25.00€), Quadro Luna (1x30.00€)"
        """
        items_list = []
        for item in items:
            items_list.append(f"{item['progetto']} ({item['quantita']}x{item['prezzo_unitario']:.2f}€)")
        return ", ".join(items_list)

    @staticmethod
    def registra_vendita(progetto_id: int,
                         cliente: str,
                         quantita: int,
                         prezzo_totale: float,
                         prezzo_unitario: float,
                         note: str = "",
                         nome_progetto: Optional[str] = None,
                         immagine_percorso: Optional[str] = None) -> int:
        """
        Inserisce una nuova vendita direttamente nella tabella 'venduti'.
        Restituisce l'ID della vendita appena creata.
        """
        conn = get_connection()
        c = conn.cursor()
        try:
            data_vendita = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                      INSERT INTO venduti (negozio_id, cliente, quantita, prezzo_totale, prezzo_unitario, note, nome,
                                           immagine_percorso, data_vendita)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                      """, (
                          progetto_id,  # negozio_id, ma in questo caso lo usi per identificare il progetto
                          cliente,
                          quantita,
                          prezzo_totale,
                          prezzo_unitario,
                          note,
                          nome_progetto,
                          immagine_percorso,
                          data_vendita
                      ))
            conn.commit()
            return c.lastrowid
        except Exception as e:
            conn.rollback()
            raise Exception(f"Errore durante l'inserimento della vendita: {e}")
        finally:
            conn.close()