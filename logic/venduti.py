# logic/venduti.py
import sqlite3
from datetime import datetime
from db.database import get_connection
from typing import List, Dict, Any, Optional, Tuple


class VendutiManager:
    """Gestisce la logica di business per le vendite."""

    @staticmethod
    def get_vendite_dettaglio() -> List[Dict]:
        """
        Recupera tutte le vendite in formato dettaglio (una riga per vendita).
        PER LA VISUALIZZAZIONE: calcola costo e ricavo usando le funzioni di Progetto
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        print("\n" + "=" * 60)
        print("🔍 DEBUG - get_vendite_dettaglio()")
        print("=" * 60)

        # Query principale con JOIN per gli sconti
        c.execute("""
                  SELECT v.id,
                         v.data_vendita               AS data,
                         v.cliente,
                         v.quantita,
                         v.prezzo_totale              AS prezzo_vendita,
                         o.prezzo_totale              AS prezzo_ordine,
                         v.prezzo_unitario,
                         v.note,
                         v.immagine_percorso,
                         v.nome                       AS nome_vendita,
                         v.ordine_id,
                         n.progetto_id, -- 🔥 Progetto_id per calcolare costo e ricavo
                         COALESCE(p.nome, v.nome)     AS progetto_nome,
                         p.percorso                   AS percorso_progetto,
                         COALESCE(u.sconto_totale, 0) AS sconto_applicato
                  FROM venduti v
                           LEFT JOIN negozio n ON v.negozio_id = n.id
                           LEFT JOIN progetti p ON n.progetto_id = p.id
                           LEFT JOIN ordini o ON v.ordine_id = o.id
                           LEFT JOIN (SELECT vendita_id, SUM(importo_utilizzato) as sconto_totale
                                      FROM utilizzi_buoni
                                      GROUP BY vendita_id) u ON v.id = u.vendita_id
                  ORDER BY v.data_vendita DESC
                  """)

        righe = c.fetchall()
        print(f"\nTotale vendite trovate: {len(righe)}")

        risultati = []
        for r in righe:
            # 🔥 Calcola prezzo originale (prezzo_vendita + sconto)
            prezzo_originale = r["prezzo_vendita"] + r["sconto_applicato"]

            # 🔥 Calcola costo e ricavo usando il progetto
            costo_totale = None
            ricavo = None

            if r["progetto_id"]:
                from logic.progetti import Progetto
                try:
                    progetto = Progetto(carica_da_id=r["progetto_id"])
                    costo_unitario = progetto.calcola_costo()
                    costo_totale = costo_unitario * r["quantita"]
                    ricavo = prezzo_originale - costo_totale
                except Exception as e:
                    print(f"   ⚠️ Errore nel calcolo costo per progetto {r['progetto_id']}: {e}")

            print(f"\n--- Vendita ID: {r['id']} ---")
            print(f"  ordine_id: {r['ordine_id']}")
            print(f"  progetto_id: {r['progetto_id']}")
            print(f"  prezzo_vendita: {r['prezzo_vendita']}")
            print(f"  sconto_applicato: {r['sconto_applicato']}")
            print(f"  prezzo_originale: {prezzo_originale}")
            print(f"  costo_totale: {costo_totale}")
            print(f"  ricavo: {ricavo}")

            risultati.append({
                "id": r["id"],
                "data": r["data"],
                "cliente": r["cliente"],
                "quantita": r["quantita"],
                "prezzo_totale": prezzo_originale,
                "prezzo_unitario": prezzo_originale / r["quantita"] if r["quantita"] else 0,
                "costo_totale": costo_totale,
                "ricavo": ricavo,
                "note": r["note"],
                "immagine_percorso": r["immagine_percorso"],
                "progetto_nome": r["progetto_nome"] or r["nome_vendita"] or "[Sconosciuto]",
                "percorso_progetto": r["percorso_progetto"],
                "sconto_applicato": r["sconto_applicato"]
            })

        conn.close()
        print("=" * 60)
        return risultati

    @staticmethod
    def get_vendite_aggregate() -> List[Dict]:
        """
        Recupera TUTTE le vendite e le raggruppa per cliente.
        PER LA VISUALIZZAZIONE: usa i prezzi originali (prezzo_vendita + sconto)
        Esclude le vendite che hanno ordine_id (già rappresentate come ordini)
        """
        print("\n" + "=" * 60)
        print("🔍 DEBUG - get_vendite_aggregate()")
        print("=" * 60)

        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 🔥 PARTE 1: VENDITE DAL NEGOZIO (che NON hanno ordine_id)
        c.execute("""
                  SELECT v.cliente                    AS cliente,
                         COALESCE(p.nome, v.nome)     AS progetto_nome,
                         v.quantita                   AS quantita,
                         v.prezzo_totale              AS prezzo_vendita,
                         v.data_vendita               AS data_vendita,
                         'vendita'                    AS tipo,
                         v.id                         AS source_id,
                         n.progetto_id,
                         COALESCE(u.sconto_totale, 0) AS sconto_applicato,
                         v.ordine_id
                  FROM venduti v
                           LEFT JOIN negozio n ON v.negozio_id = n.id
                           LEFT JOIN progetti p ON n.progetto_id = p.id
                           LEFT JOIN (SELECT vendita_id, SUM(importo_utilizzato) as sconto_totale
                                      FROM utilizzi_buoni
                                      GROUP BY vendita_id) u ON v.id = u.vendita_id
                  WHERE v.cliente IS NOT NULL
                    AND v.cliente != ''
                    AND v.ordine_id IS NULL -- 🔥 Solo vendite NON da ordini
                  """)

        vendite_negozio = c.fetchall()
        print(f"   Vendite da negozio trovate (senza ordine_id): {len(vendite_negozio)}")

        # 🔥 PARTE 2: ORDINI CONSEGNATI
        c.execute("""
                  SELECT o.cliente                  AS cliente,
                         GROUP_CONCAT(p.nome, ', ') AS progetto_nome,
                         SUM(po.quantita)           AS quantita,
                         o.prezzo_totale            AS prezzo_originale,
                         o.data_consegna            AS data_vendita,
                         'ordine'                   AS tipo,
                         o.id                       AS source_id,
                         NULL                       AS progetto_id,
                         0                          AS sconto_applicado,
                         NULL                       AS ordine_id
                  FROM ordini o
                           LEFT JOIN progetti_ordinati po ON o.id = po.ordine_id
                           LEFT JOIN progetti p ON po.progetto_id = p.id
                  WHERE o.consegnato = 1
                    AND o.cliente IS NOT NULL
                    AND o.cliente != ''
                  GROUP BY o.id
                  """)

        ordini_consegnati = c.fetchall()
        print(f"   Ordini consegnati trovati: {len(ordini_consegnati)}")

        conn.close()

        # 🔥 COMBINA I DATI (usando i prezzi originali)
        tutte_le_vendite = []

        # Aggiungi solo vendite dal negozio (che NON hanno ordine_id)
        for v in vendite_negozio:
            prezzo_originale = v["prezzo_vendita"] + v["sconto_applicato"]

            tutte_le_vendite.append({
                "cliente": v["cliente"],
                "progetto": v["progetto_nome"],
                "quantita": v["quantita"],
                "prezzo_totale": prezzo_originale,
                "sconto": v["sconto_applicato"],
                "data": v["data_vendita"],
                "tipo": v["tipo"],
                "source_id": v["source_id"]
            })

        # Aggiungi ordini consegnati
        for o in ordini_consegnati:
            tutte_le_vendite.append({
                "cliente": o["cliente"],
                "progetto": f"ORDINE #{o['source_id']}: {o['progetto_nome']}",
                "quantita": o["quantita"],
                "prezzo_totale": o["prezzo_originale"],
                "sconto": 0,
                "data": o["data_vendita"],
                "tipo": o["tipo"],
                "source_id": o["source_id"]
            })

        print(f"\n   TOTALE record combinati (senza duplicati): {len(tutte_le_vendite)}")

        # 🔥 RAGGRUPPA PER CLIENTE
        clienti = {}
        for v in tutte_le_vendite:
            cliente = v["cliente"].strip() or "[Cliente non specificato]"
            proj = v["progetto"] or "[Sconosciuto]"
            qta = int(v["quantita"] or 0)
            tot = float(v["prezzo_totale"] or 0.0)
            data = v["data"]

            if cliente not in clienti:
                clienti[cliente] = {
                    "items": [],
                    "quantita_tot": 0,
                    "totale": 0.0,
                    "ultima_data": data,
                    "vendite_count": 0,
                    "ordini_count": 0
                }

            # Aggiungi l'item
            clienti[cliente]["items"].append({
                "progetto": proj,
                "quantita": qta,
                "prezzo_unitario": tot / qta if qta > 0 else 0,
                "totale": tot,
                "tipo": v["tipo"]
            })

            # Aggiorna totali
            clienti[cliente]["quantita_tot"] += qta
            clienti[cliente]["totale"] += tot

            if v["tipo"] == "vendita":
                clienti[cliente]["vendite_count"] += 1
            else:
                clienti[cliente]["ordini_count"] += 1

            try:
                if data and (not clienti[cliente]["ultima_data"] or data > clienti[cliente]["ultima_data"]):
                    clienti[cliente]["ultima_data"] = data
            except Exception:
                pass

        # 🔥 TRASFORMA IN LISTA ORDINATA
        risultati = []
        for cliente, info in sorted(clienti.items(), key=lambda t: t[0].lower()):
            risultati.append({
                "cliente": cliente,
                "items": info["items"],
                "quantita_totale": info["quantita_tot"],
                "totale": info["totale"],
                "ultima_data": info["ultima_data"],
                "vendite_count": info["vendite_count"],
                "ordini_count": info["ordini_count"]
            })

        print("\n🔍 RIEPILOGO AGGREGATO (SENZA DUPLICATI):")
        for i, r in enumerate(risultati[:5]):
            print(f"   Cliente {i + 1}: {r['cliente']}")
            print(f"      Totale: €{r['totale']:.2f}")
            print(f"      Quantità totale: {r['quantita_totale']}")
            print(f"      Composizione: {r['vendite_count']} vendite, {r['ordini_count']} ordini")

        print("=" * 60)
        return risultati

    @staticmethod
    def get_ordini_aggregati() -> List[Dict]:
        """
        Recupera tutti gli ordini completati e li raggruppa per cliente.
        Legge direttamente dalla tabella ordini.
        """
        print("\n" + "=" * 60)
        print("🔍 DEBUG - get_ordini_aggregati()")
        print("=" * 60)

        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Query che legge direttamente da ordini
        c.execute("""
                  SELECT o.cliente,
                         o.id                       AS ordine_id,
                         o.prezzo_totale,
                         o.data_inserimento,
                         o.consegnato,
                         GROUP_CONCAT(p.nome, ', ') AS progetti,
                         SUM(po.quantita)           AS quantita_totale
                  FROM ordini o
                           LEFT JOIN progetti_ordinati po ON o.id = po.ordine_id
                           LEFT JOIN progetti p ON po.progetto_id = p.id
                  WHERE o.consegnato = 1 -- Solo ordini consegnati
                  GROUP BY o.id
                  ORDER BY o.cliente COLLATE NOCASE, o.data_inserimento DESC
                  """)

        righe = c.fetchall()
        print(f"Totale ordini consegnati: {len(righe)}")

        # Raggruppa per cliente in Python
        clienti = {}
        for r in righe:
            cliente = r["cliente"] or "Cliente non specificato"
            ordine_id = r["ordine_id"]
            prezzo = r["prezzo_totale"] or 0
            progetti = r["progetti"] or "-"
            quantita = r["quantita_totale"] or 0
            data = r["data_inserimento"]

            if cliente not in clienti:
                clienti[cliente] = {
                    "items": [],
                    "quantita_tot": 0,
                    "totale": 0.0,
                    "ultima_data": data,
                    "ordini": []
                }

            clienti[cliente]["items"].append({
                "ordine_id": ordine_id,
                "progetti": progetti,
                "quantita": quantita,
                "prezzo": prezzo
            })

            clienti[cliente]["quantita_tot"] += quantita
            clienti[cliente]["totale"] += prezzo
            clienti[cliente]["ordini"].append(ordine_id)

            if data and (not clienti[cliente]["ultima_data"] or data > clienti[cliente]["ultima_data"]):
                clienti[cliente]["ultima_data"] = data

        # Trasforma in lista ordinata
        risultati = []
        for cliente, info in sorted(clienti.items(), key=lambda t: t[0].lower()):
            # Formatta gli items per la visualizzazione
            items_str = ", ".join([f"Ordine #{o['ordine_id']}: {o['progetti']} (x{o['quantita']})"
                                   for o in info["items"]])

            risultati.append({
                "cliente": cliente,
                "items_str": items_str,
                "items_list": info["items"],
                "quantita_totale": info["quantita_tot"],
                "totale": info["totale"],
                "ultima_data": info["ultima_data"],
                "numero_ordini": len(info["ordini"])
            })

        print("\n🔍 RIEPILOGO ORDINI AGGREGATI:")
        for i, r in enumerate(risultati[:3]):
            print(f"   Cliente {i + 1}: {r['cliente']}")
            print(f"      Totale: {r['totale']}")
            print(f"      Quantità totale: {r['quantita_totale']}")
            print(f"      Numero ordini: {r['numero_ordini']}")

        print("=" * 60)
        return risultati

    @staticmethod
    def get_vendite_cliente(cliente_nome: str) -> List[Dict]:
        """
        Recupera tutte le vendite di un cliente specifico.
        Il prezzo totale viene preso dalla tabella ordini se disponibile.
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
                             WHEN v.nome IS NOT NULL AND v.nome != '' AND v.nome != 'ORDINI CLIENTI' AND v.nome != '🔹 ORDINI CLIENTI' 
                             THEN v.nome
                             WHEN p.nome IS NOT NULL AND p.nome != '' AND p.nome != 'ORDINI CLIENTI' AND p.nome != '🔹 ORDINI CLIENTI' 
                             THEN p.nome
                             ELSE 'Progetto sconosciuto'
                         END AS progetto,
                         v.quantita,
                         v.prezzo_unitario,
                         -- 🔥 PREZZO TOTALE: se c'è ordine, prendi il valore originale dell'ordine
                         CASE 
                             WHEN o.id IS NOT NULL THEN o.prezzo_totale
                             ELSE v.prezzo_totale
                         END AS prezzo_totale
                  FROM venduti v
                  LEFT JOIN negozio n ON v.negozio_id = n.id
                  LEFT JOIN progetti p ON n.progetto_id = p.id
                  LEFT JOIN ordini o ON v.ordine_id = o.id
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
        Calcola il prezzo originale come prezzo_totale + sconto_applicato
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
                         COALESCE(p.nome, v.nome)     AS progetto_nome,
                         p.percorso                   AS percorso_progetto,
                         v.ordine_id,
                         -- 🔥 SCONTO
                         COALESCE(u.sconto_totale, 0) AS sconto_applicato,
                         b.codice                     AS codice_buono
                  FROM venduti v
                           LEFT JOIN negozio n ON v.negozio_id = n.id
                           LEFT JOIN progetti p ON n.progetto_id = p.id
                           LEFT JOIN (SELECT vendita_id, SUM(importo_utilizzato) as sconto_totale, buono_id
                                      FROM utilizzi_buoni
                                      GROUP BY vendita_id) u ON v.id = u.vendita_id
                           LEFT JOIN buoni b ON u.buono_id = b.id
                  WHERE v.id = ?
                  """, (vendita_id,))

        row = c.fetchone()
        conn.close()

        if not row:
            return None

        # 🔥 Calcola il prezzo originale (prezzo_totale + sconto_applicato)
        prezzo_originale = row["prezzo_totale"] + row["sconto_applicato"]

        return {
            "id": row["id"],
            "data": row["data_vendita"],
            "cliente": row["cliente"],
            "quantita": row["quantita"],
            "prezzo_totale": prezzo_originale,  # 🔥 Questo è il prezzo originale (6.00)
            "prezzo_scontato": row["prezzo_totale"],  # Prezzo effettivamente pagato (1.00)
            "prezzo_unitario": row["prezzo_unitario"],
            "costo_totale": row["costo_totale"],
            "ricavo": row["ricavo"],
            "note": row["note"],
            "immagine_percorso": row["immagine_percorso"],
            "progetto_nome": row["progetto_nome"],
            "percorso_progetto": row["percorso_progetto"],
            "sconto_applicato": row["sconto_applicato"],
            "codice_buono": row["codice_buono"]
        }

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