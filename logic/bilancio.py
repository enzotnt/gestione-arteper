# logic/bilancio.py
from datetime import datetime
from typing import Dict, List, Tuple
from utils.helpers import db_cursor


class BilancioManager:
    """Gestisce la logica di business per il bilancio."""

    @staticmethod
    def get_dati_totali(da: str, a: str) -> Dict[str, float]:
        """
        Calcola i dati totali del bilancio per il periodo specificato.
        """
        spese_magazzino = BilancioManager._get_totale_spese_magazzino(da, a)
        spese_gestione = BilancioManager._get_totale_spese_gestione(da, a)

        # 🔥 MODIFICATO: Ricavi includono:
        # - Vendite dirette (da venduti)
        # - Utilizzo buoni (quando vengono spesi)
        # - Acconti ricevuti (da ordini con acconto)
        ricavi_diretti = BilancioManager._get_totale_ricavi_diretti(da, a)
        utilizzo_buoni = BilancioManager._get_totale_utilizzo_buoni(da, a)
        acconti = BilancioManager._get_totale_acconti(da, a)  # <-- DA AGGIUNGERE!

        ricavi = ricavi_diretti + utilizzo_buoni + acconti  # <-- INCLUSO!

        totale_spese = spese_magazzino + spese_gestione
        utile = ricavi - totale_spese

        return {
            "spese_magazzino": spese_magazzino,
            "spese_gestione": spese_gestione,
            "totale_spese": totale_spese,
            "ricavi": ricavi,
            "utile": utile,
            "ricavi_diretti": ricavi_diretti,
            "ricavi_da_buoni": utilizzo_buoni,
            "ricavi_da_acconti": acconti  # <-- AGGIUNTO (opzionale)
        }

    @staticmethod
    def _get_totale_acconti(da: str, a: str) -> float:
        """Calcola il totale degli acconti ricevuti nel periodo."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT COALESCE(SUM(acconto), 0) as totale
                        FROM ordini
                        WHERE data_inserimento BETWEEN ? AND ?
                          AND acconto > 0
                        """, (da, a))
            row = cur.fetchone()
            return row[0] if row else 0.0

    @staticmethod
    def _get_totale_ricavi_diretti(da: str, a: str) -> float:
        """Calcola il totale dei ricavi dalle vendite dirette."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT COALESCE(SUM(prezzo_totale), 0) as totale
                        FROM venduti
                        WHERE data_vendita BETWEEN ? AND ?
                        """, (da, a))
            row = cur.fetchone()
            return row[0] if row else 0.0

    @staticmethod
    def _get_totale_utilizzo_buoni(da: str, a: str) -> float:
        """Calcola il totale degli utilizzi dei buoni (ricavi)."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT COALESCE(SUM(importo_utilizzato), 0) as totale
                        FROM utilizzi_buoni
                        WHERE data_utilizzo BETWEEN ? AND ?
                        """, (da, a))
            row = cur.fetchone()
            return row[0] if row else 0.0

    @staticmethod
    def _get_totale_spese_magazzino(da: str, a: str) -> float:
        """Calcola il totale delle spese di magazzino nel periodo."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT SUM(costo_totale) AS totale
                        FROM movimenti_magazzino
                        WHERE data BETWEEN ? AND ?
                        """, (da, a))
            row = cur.fetchone()
            return row[0] if row and row[0] else 0.0

    @staticmethod
    def _get_totale_spese_gestione(da: str, a: str) -> float:
        """Calcola il totale delle spese di gestione nel periodo."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT SUM(importo) AS totale
                        FROM spese_gestione
                        WHERE data BETWEEN ? AND ?
                        """, (da, a))
            row = cur.fetchone()
            return row[0] if row and row[0] else 0.0

    @staticmethod
    def _get_totale_ricavi(da: str, a: str) -> float:
        """Calcola il totale dei ricavi nel periodo."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT SUM(prezzo_totale) AS totale
                        FROM venduti
                        WHERE data_vendita BETWEEN ? AND ?
                        """, (da, a))
            row = cur.fetchone()
            return row[0] if row and row[0] else 0.0

    # =========================================================================
    # DATI MENSILI PER GRAFICI
    # =========================================================================

    @staticmethod
    def get_spese_magazzino_mensili(da: str, a: str) -> Dict[str, float]:
        """
        Restituisce un dizionario {mese: totale_spese_magazzino}
        per il periodo specificato.
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT strftime('%Y-%m', data) AS mese, SUM(costo_totale) AS totale
                        FROM movimenti_magazzino
                        WHERE data BETWEEN ? AND ?
                        GROUP BY mese
                        ORDER BY mese
                        """, (da, a))

            return {row[0]: row[1] for row in cur.fetchall()}

    @staticmethod
    def get_spese_gestione_mensili(da: str, a: str) -> Dict[str, float]:
        """
        Restituisce un dizionario {mese: totale_spese_gestione}
        per il periodo specificato.
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT strftime('%Y-%m', data) AS mese, SUM(importo) AS totale
                        FROM spese_gestione
                        WHERE data BETWEEN ? AND ?
                        GROUP BY mese
                        ORDER BY mese
                        """, (da, a))

            return {row[0]: row[1] for row in cur.fetchall()}

    @staticmethod
    def get_ricavi_mensili(da: str, a: str) -> Dict[str, float]:
        """
        Restituisce un dizionario {mese: totale_ricavi}
        per il periodo specificato.
        I ricavi includono:
        - Vendite dirette (da venduti)
        - Utilizzo dei buoni (quando vengono spesi)
        """
        with db_cursor() as cur:
            # Ricavi dalle vendite dirette
            cur.execute("""
                        SELECT strftime('%Y-%m', data_vendita) AS mese,
                               COALESCE(SUM(prezzo_totale), 0) as totale
                        FROM venduti
                        WHERE data_vendita BETWEEN ? AND ?
                        GROUP BY mese
                        ORDER BY mese
                        """, (da, a))

            ricavi_diretti = {row[0]: row[1] for row in cur.fetchall()}

            # 🔥 NUOVO: Utilizzo dei buoni (questi sono ricavi!)
            cur.execute("""
                        SELECT strftime('%Y-%m', data_utilizzo)     AS mese,
                               COALESCE(SUM(importo_utilizzato), 0) as totale
                        FROM utilizzi_buoni
                        WHERE data_utilizzo BETWEEN ? AND ?
                        GROUP BY mese
                        ORDER BY mese
                        """, (da, a))

            ricavi_da_buoni = {row[0]: row[1] for row in cur.fetchall()}

            # Combina i due dizionari
            tutti_mesi = set(ricavi_diretti.keys()) | set(ricavi_da_buoni.keys())
            ricavi_totali = {}
            for mese in tutti_mesi:
                ricavi_totali[mese] = ricavi_diretti.get(mese, 0) + ricavi_da_buoni.get(mese, 0)

            return ricavi_totali

    # =========================================================================
    # METODI AGGIUNTIVI PER ANALISI PIÙ DETTAGLIATE
    # =========================================================================

    @staticmethod
    def get_ripartizione_spese(da: str, a: str) -> Dict[str, float]:
        """
        Restituisce la ripartizione delle spese per categoria.
        Utile per grafici a torta.
        """
        with db_cursor() as cur:
            # Spese magazzino (non abbiamo categorie, le raggruppiamo tutte insieme)
            cur.execute("""
                        SELECT 'Acquisti Magazzino' as categoria, SUM(costo_totale) as totale
                        FROM movimenti_magazzino
                        WHERE data BETWEEN ? AND ?
                        """, (da, a))
            magazzino = cur.fetchone()

            # Spese gestione per categoria
            cur.execute("""
                        SELECT categoria, SUM(importo) as totale
                        FROM spese_gestione
                        WHERE data BETWEEN ? AND ?
                        GROUP BY categoria
                        ORDER BY totale DESC
                        """, (da, a))
            spese_gestione = cur.fetchall()

        risultato = {}
        if magazzino and magazzino[1]:
            risultato["Acquisti Magazzino"] = magazzino[1]

        for cat, tot in spese_gestione:
            risultato[cat] = tot

        return risultato

    @staticmethod
    def get_andamento_utile_mensile(da: str, a: str) -> List[Tuple[str, float]]:
        """
        Restituisce l'andamento dell'utile mese per mese.
        Utile per grafici a linee dell'utile mensile (non cumulativo).
        """
        spese_magazzino = BilancioManager.get_spese_magazzino_mensili(da, a)
        spese_gestione = BilancioManager.get_spese_gestione_mensili(da, a)
        ricavi = BilancioManager.get_ricavi_mensili(da, a)

        # Unisci tutti i mesi
        tutti_mesi = set(spese_magazzino.keys()) | set(spese_gestione.keys()) | set(ricavi.keys())

        risultati = []
        for mese in sorted(tutti_mesi):
            spese_m = spese_magazzino.get(mese, 0)
            spese_g = spese_gestione.get(mese, 0)
            ricavi_m = ricavi.get(mese, 0)

            utile_mensile = ricavi_m - (spese_m + spese_g)
            risultati.append((mese, utile_mensile))

        return risultati

    @staticmethod
    def get_best_seller(da: str, a: str, limite: int = 5) -> List[Tuple[str, int, float]]:
        """
        Restituisce i progetti più venduti nel periodo.
        Utile per analisi aggiuntive.

        Returns:
            Lista di tuple (nome_progetto, quantita_totale, ricavo_totale)
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT v.nome               as progetto,
                               SUM(v.quantita)      as tot_quantita,
                               SUM(v.prezzo_totale) as tot_ricavo
                        FROM venduti v
                        WHERE v.data_vendita BETWEEN ? AND ?
                        GROUP BY v.nome
                        ORDER BY tot_ricavo DESC LIMIT ?
                        """, (da, a, limite))

            return [(row[0], row[1], row[2]) for row in cur.fetchall()]

    @staticmethod
    def get_riepilogo_acconti(da: str, a: str) -> Dict:
        """
        Restituisce il riepilogo degli acconti nel periodo.
        """
        with db_cursor() as cur:
            # Acconti ricevuti nel periodo (nuovi acconti)
            cur.execute("""
                        SELECT COUNT(*)                  as numero_ordini_con_acconto,
                               COALESCE(SUM(acconto), 0) as totale_acconti
                        FROM ordini
                        WHERE data_inserimento BETWEEN ? AND ?
                          AND acconto > 0
                        """, (da, a))
            nuovi_acconti = cur.fetchone()

            # Totale acconti ancora attivi (ordini non ancora consegnati con acconto > 0)
            cur.execute("""
                        SELECT COALESCE(SUM(acconto), 0) as acconti_attivi
                        FROM ordini
                        WHERE consegnato = 0
                          AND acconto > 0
                        """)
            acconti_attivi = cur.fetchone()

        return {
            "numero_acconti": nuovi_acconti[0] if nuovi_acconti else 0,
            "totale_acconti": nuovi_acconti[1] if nuovi_acconti else 0.0,
            "acconti_attivi": acconti_attivi[0] if acconti_attivi else 0.0
        }

    @staticmethod
    def get_dettaglio_acconti(da: str, a: str) -> List[Dict]:
        """
        Restituisce il dettaglio degli ordini con acconto nel periodo.
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT o.id                       as ordine_id,
                               o.data_inserimento,
                               o.cliente,
                               o.acconto,
                               o.prezzo_totale,
                               o.stato_pagamento,
                               o.consegnato,
                               GROUP_CONCAT(p.nome, ', ') as progetti
                        FROM ordini o
                                 LEFT JOIN progetti_ordinati po ON o.id = po.ordine_id
                                 LEFT JOIN progetti p ON po.progetto_id = p.id
                        WHERE o.data_inserimento BETWEEN ? AND ?
                          AND o.acconto > 0
                        GROUP BY o.id
                        ORDER BY o.data_inserimento DESC
                        """, (da, a))

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    @staticmethod
    def get_dati_buoni(da: str, a: str) -> Dict[str, float]:
        """
        Calcola i dati relativi ai buoni per il periodo specificato.
        """
        print("\n" + "🔥" * 50)
        print(f"🔥 FUNZIONE get_dati_buoni CHIAMATA con periodo: {da} → {a}")
        print("🔥" * 50)

        with db_cursor() as cur:
            # 1. VEDIAMO TUTTI I BUONI
            print("\n📋 TUTTI I BUONI NEL DB:")
            cur.execute("SELECT id, codice, data_creazione, incassato, stato FROM buoni")
            for row in cur.fetchall():
                print(f"   ID:{row[0]} | {row[1]} | data:{row[2]} | incassato:{row[3]} | stato:{row[4]}")

            # 2. ESECUZIONE QUERY PRINCIPALE
            print(
                f"\n🔍 ESEGUO QUERY: SELECT COUNT(*), SUM(incassato), SUM(valore_originale) FROM buoni WHERE data_creazione BETWEEN '{da}' AND '{a}'")
            cur.execute("""
                        SELECT COUNT(*)                           as numero_buoni,
                               COALESCE(SUM(incassato), 0)        as totale_incassato,
                               COALESCE(SUM(valore_originale), 0) as valore_nominale_totale
                        FROM buoni
                        WHERE data_creazione BETWEEN ? AND ?
                        """, (da, a))
            vendite = cur.fetchone()
            print(f"📊 RISULTATO: numero={vendite[0]}, incassato={vendite[1]}, valore={vendite[2]}")

            # 3. VEDIAMO TUTTI GLI UTILIZZI
            print("\n📋 TUTTI GLI UTILIZZI NEL DB:")
            cur.execute(
                "SELECT id, buono_id, data_utilizzo, importo_utilizzato FROM utilizzi_buoni ORDER BY data_utilizzo")
            for row in cur.fetchall():
                print(f"   ID:{row[0]} | buono:{row[1]} | data:{row[2]} | importo:{row[3]}")

            # 4. ESECUZIONE QUERY UTILIZZI
            print(
                f"\n🔍 ESEGUO QUERY: SELECT COUNT(*), SUM(importo_utilizzato) FROM utilizzi_buoni WHERE data_utilizzo BETWEEN '{da}' AND '{a}'")
            cur.execute("""
                        SELECT COUNT(*)                             as numero_utilizzi,
                               COALESCE(SUM(importo_utilizzato), 0) as totale_utilizzato
                        FROM utilizzi_buoni
                        WHERE data_utilizzo BETWEEN ? AND ?
                        """, (da, a))
            utilizzi = cur.fetchone()
            print(f"📊 RISULTATO: numero={utilizzi[0]}, utilizzato={utilizzi[1]}")

            # 5. RESIDUO
            cur.execute("""
                        SELECT COALESCE(SUM(valore_residuo), 0) as valore_residuo_totale
                        FROM buoni
                        WHERE stato = 'ATTIVO'
                        """)
            residuo = cur.fetchone()
            print(f"\n📊 VALORE RESIDUO BUONI ATTIVI: {residuo[0]}")

        risultato = {
            "buoni_venduti": vendite[0] if vendite else 0,
            "totale_incassato": vendite[1] if vendite else 0.0,
            "valore_nominale_venduto": vendite[2] if vendite else 0.0,
            "utilizzi": utilizzi[0] if utilizzi else 0,
            "totale_utilizzato": utilizzi[1] if utilizzi else 0.0,
            "valore_residuo_totale": residuo[0] if residuo else 0.0,
        }

        print(f"\n🎯 RISULTATO FINALE: {risultato}")
        print("🔥" * 50)

        return risultato

    @staticmethod
    def get_dati_buoni_mensili(da: str, a: str) -> Dict[str, Dict]:
        """
        Restituisce i dati mensili dei buoni per il grafico.
        """
        with db_cursor() as cur:
            # 🔥 CREAZIONI buoni per mese (usa data_creazione)
            cur.execute("""
                        SELECT strftime('%Y-%m', data_creazione)  AS mese,
                               COUNT(*)                           as numero_buoni,
                               COALESCE(SUM(valore_originale), 0) as valore_totale
                        FROM buoni
                        WHERE data_creazione BETWEEN ? AND ?
                        GROUP BY mese
                        ORDER BY mese
                        """, (da, a))
            creazioni_mensili = {row[0]: row[2] for row in cur.fetchall()}  # valore_totale

            # 🔥 UTILIZZI buoni per mese
            cur.execute("""
                        SELECT strftime('%Y-%m', data_utilizzo)     AS mese,
                               COUNT(*)                             as numero_utilizzi,
                               COALESCE(SUM(importo_utilizzato), 0) as utilizzo
                        FROM utilizzi_buoni
                        WHERE data_utilizzo BETWEEN ? AND ?
                        GROUP BY mese
                        ORDER BY mese
                        """, (da, a))
            utilizzi_mensili = {row[0]: row[2] for row in cur.fetchall()}  # utilizzo

        return {
            "creazioni": creazioni_mensili,
            "utilizzi": utilizzi_mensili
        }

    @staticmethod
    def get_bilancio_completo(da: str, a: str) -> Dict:
        """
        Restituisce il bilancio completo includendo i buoni.
        """
        # Dati tradizionali (ora includono già gli utilizzi buoni nei ricavi)
        dati_base = BilancioManager.get_dati_totali(da, a)

        # Dati buoni (vendite e incassi)
        dati_buoni = BilancioManager.get_dati_buoni(da, a)

        return {
            **dati_base,
            "buoni": dati_buoni,
            "incassi_da_buoni": dati_buoni['totale_incassato'],  # Questi NON sono ricavi!
            "utilizzo_buoni": dati_buoni['totale_utilizzato'],  # Questi SONO ricavi!
            "passivita_buoni": dati_buoni['valore_residuo_totale']
        }