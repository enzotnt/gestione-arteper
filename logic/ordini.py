# logic/ordini.py
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from utils.helpers import db_cursor


class OrdineManager:
    """Gestisce tutta la logica degli ordini."""

    @staticmethod
    def get_progetti_lista() -> List[Dict]:
        """
        Restituisce la lista di tutti i progetti con stato_vendita = 'IN VENDITA'.
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT id, nome
                        FROM progetti
                        WHERE stato_vendita = 'IN VENDITA'
                        ORDER BY nome COLLATE NOCASE
                        """)
            return [{"id": row[0], "nome": row[1]} for row in cur.fetchall()]

    @staticmethod
    def get_ordini() -> List[Dict]:
        """
        Restituisce tutti gli ordini.
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT id, cliente, data_consegna, data_inserimento, consegnato, note, stato_pagamento
                        FROM ordini
                        ORDER BY data_inserimento DESC
                        """)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    @staticmethod
    def get_ordine_dettaglio(ordine_id: int) -> Optional[Dict]:
        """
        Restituisce i dettagli di un ordine specifico.
        """
        with db_cursor() as cur:
            cur.execute("SELECT * FROM ordini WHERE id = ?", (ordine_id,))
            row = cur.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, row))

    @staticmethod
    def get_progetti_ordinati(ordine_id: int) -> List[Dict]:
        """
        Restituisce i progetti associati a un ordine con i relativi prezzi.
        I prezzi vengono presi dalla tabella ordini (valori originali).
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT p.nome,
                               po.quantita,
                               po.prezzo_unitario,
                               po.prezzo_totale,
                               po.assemblato,
                               po.data_lavorazione,
                               -- 🔥 AGGIUNGIAMO ANCHE IL PREZZO TOTALE DELL'ORDINE PER VERIFICA
                               o.prezzo_totale AS ordine_totale
                        FROM progetti_ordinati po
                                 JOIN progetti p ON po.progetto_id = p.id
                                 JOIN ordini o ON po.ordine_id = o.id -- 🔥 JOIN CON ORDINI
                        WHERE po.ordine_id = ?
                        """, (ordine_id,))

            columns = [desc[0] for desc in cur.description]
            risultati = []
            for row in cur.fetchall():
                dati = dict(zip(columns, row))
                # Assicurati che i prezzi siano float
                if dati["prezzo_unitario"] is None:
                    dati["prezzo_unitario"] = 0.0
                if dati["prezzo_totale"] is None:
                    dati["prezzo_totale"] = 0.0
                risultati.append(dati)

                # 🔍 DEBUG PRINT
                print(f"DEBUG - Ordine {ordine_id}, Progetto {dati['nome']}:")
                print(f"   prezzo_unitario: {dati['prezzo_unitario']}")
                print(f"   prezzo_totale: {dati['prezzo_totale']}")
                print(f"   ordine_totale: {dati.get('ordine_totale')}")

            return risultati

    @staticmethod
    def toggle_consegnato(ordine_id: int) -> Tuple[bool, int, str]:
        """
        Cambia lo stato di consegna di un ordine.
        Restituisce (successo, nuovo_stato, messaggio)
        """
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT consegnato FROM ordini WHERE id = ?", (ordine_id,))
            row = cur.fetchone()
            if not row:
                return False, 0, "Ordine non trovato"

            nuovo_stato = 0 if row[0] == 1 else 1
            cur.execute("UPDATE ordini SET consegnato = ? WHERE id = ?", (nuovo_stato, ordine_id))
            return True, nuovo_stato, "Stato aggiornato"

    @staticmethod
    def elimina_ordini(ordine_ids: List[int]) -> Tuple[bool, str]:
        """
        Elimina uno o più ordini.
        """
        with db_cursor(commit=True) as cur:
            try:
                for ordine_id in ordine_ids:
                    cur.execute("DELETE FROM progetti_ordinati WHERE ordine_id = ?", (ordine_id,))
                    cur.execute("DELETE FROM ordini WHERE id = ?", (ordine_id,))
                return True, f"{len(ordine_ids)} ordini eliminati"
            except Exception as e:
                return False, str(e)

    @staticmethod
    def aggiorna_ordine(ordine_id: int, cliente: str, data_consegna: str, note: str) -> Tuple[bool, str]:
        """
        Aggiorna i dati di un ordine.
        """
        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE ordini
                SET cliente = ?, data_consegna = ?, note = ?
                WHERE id = ?
            """, (cliente, data_consegna, note, ordine_id))
            return True, "Ordine aggiornato"

    @staticmethod
    def verifica_disponibilita_progetto(progetto_id: int, quantita_richiesta: int) -> Dict:
        """
        Verifica la disponibilità di un progetto.
        Restituisce un dizionario con prelevati_negozio, da_assemblare, mancanti.
        """
        with db_cursor() as cur:
            # Preleva dal negozio
            cur.execute("SELECT id, disponibili FROM negozio WHERE progetto_id = ?", (progetto_id,))
            row_negozio = cur.fetchone()
            disponibili_negozio = row_negozio[1] if row_negozio else 0
            prelevati_negozio = min(quantita_richiesta, disponibili_negozio)
            da_assemblare = quantita_richiesta - prelevati_negozio

            risultato = {
                "prelevati_negozio": prelevati_negozio,
                "da_assemblare": da_assemblare,
                "assemblabile": True,
                "mancanti": []
            }

            if da_assemblare > 0:
                # Preleva componenti dal magazzino
                cur.execute("""
                    SELECT cp.componente_id,
                           cp.quantita * ? AS richiesta,
                           IFNULL(m.quantita, 0) AS disponibile,
                           m.nome
                    FROM componenti_progetto cp
                    JOIN magazzino m ON m.id = cp.componente_id
                    WHERE cp.progetto_id = ?
                """, (da_assemblare, progetto_id))
                componenti = cur.fetchall()

                for comp in componenti:
                    if comp[2] < comp[1]:  # disponibile < richiesta
                        manca = comp[1] - comp[2]
                        risultato["mancanti"].append(f"{comp[3]} (manca: {manca})")
                        risultato["assemblabile"] = False

            return risultato

    @staticmethod
    def calcola_progetti_assemblabili(progetto_id: int) -> Dict:
        """
        Calcola quanti progetti possono essere assemblati con i componenti disponibili.
        Restituisce un dizionario con:
        - assemblabili: numero di progetti completamente assemblabili
        - componenti_mancanti: lista di componenti mancanti con quantità
        """
        with db_cursor() as cur:
            # Preleva i componenti necessari per un singolo progetto
            cur.execute("""
                SELECT cp.componente_id,
                       cp.quantita AS quantita_per_progetto,
                       IFNULL(m.quantita, 0) AS disponibile,
                       m.nome
                FROM componenti_progetto cp
                LEFT JOIN magazzino m ON m.id = cp.componente_id
                WHERE cp.progetto_id = ?
            """, (progetto_id,))
            componenti = cur.fetchall()

            if not componenti:
                return {"assemblabili": 0, "componenti_mancanti": []}

            # Calcola quanti progetti possono essere assemblati
            # = il minimo tra i rapporti (disponibile / quantita_per_progetto) per ogni componente
            assemblabili = float('inf')
            componenti_mancanti = []

            for comp_id, qta_per_prog, disponibile, nome_comp in componenti:
                if qta_per_prog <= 0:
                    continue
                
                qta_assemblabili = disponibile // qta_per_prog
                assemblabili = min(assemblabili, qta_assemblabili)

            if assemblabili == float('inf'):
                assemblabili = 0

            # Calcola i componenti mancanti per un singolo progetto
            for comp_id, qta_per_prog, disponibile, nome_comp in componenti:
                if disponibile < qta_per_prog:
                    manca = qta_per_prog - disponibile
                    componenti_mancanti.append({
                        "nome": nome_comp,
                        "manca": manca,
                        "disponibile": disponibile,
                        "richiesto": qta_per_prog
                    })

            return {
                "assemblabili": max(0, int(assemblabili)),
                "componenti_mancanti": componenti_mancanti
            }

    @staticmethod
    def verifica_disponibilita_completa(progetto_id: int, quantita_richiesta: int) -> Dict:
        """
        Verifica la disponibilità completa di un progetto per l'ordine.
        Restituisce un dizionario con tutte le informazioni necessarie:
        - disponibili_negozio: progetti completi disponibili in negozio
        - assemblabili_magazzino: progetti che possono essere assemblati dal magazzino
        - richiesti: quantità totale richiesta
        - componenti_mancanti: lista dei componenti mancanti se supera le disponibilità
        """
        with db_cursor() as cur:
            # Disponibilità in negozio
            cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?", (progetto_id,))
            row_negozio = cur.fetchone()
            disponibili_negozio = row_negozio[0] if row_negozio else 0

            # Quanti si possono assemblare
            info_assembly = OrdineManager.calcola_progetti_assemblabili(progetto_id)
            assemblabili_magazzino = info_assembly["assemblabili"]

            # Totale disponibile
            totale_disponibile = disponibili_negozio + assemblabili_magazzino

            # Componenti mancanti solo se supera il totale disponibile
            componenti_mancanti = []
            if quantita_richiesta > totale_disponibile:
                # Calcola quanti progetti mancano da assemblare oltre quello che si può fare
                progetti_mancanti = quantita_richiesta - totale_disponibile
                
                for comp in info_assembly["componenti_mancanti"]:
                    # Scala la quantità mancante per la quantità di progetti che non si possono assemblare
                    manca_totale = comp["manca"] * progetti_mancanti
                    componenti_mancanti.append({
                        "nome": comp["nome"],
                        "manca": manca_totale,
                        "disponibile": comp["disponibile"],
                        "richiesto_per_progetto": comp["richiesto"]
                    })

            return {
                "disponibili_negozio": disponibili_negozio,
                "assemblabili_magazzino": assemblabili_magazzino,
                "totale_disponibile": totale_disponibile,
                "richiesti": quantita_richiesta,
                "componenti_mancanti": componenti_mancanti,
                "surplus_ordine": max(0, quantita_richiesta - totale_disponibile)
            }

    @staticmethod
    def verifica_ordine_completo(progetti_quantita: Dict[int, int]) -> Dict:
        """
        Verifica la disponibilità per un INTERO ORDINE con più progetti.
        
        Args:
            progetti_quantita: {progetto_id: quantita_richiesta}
        
        Returns:
            Dizionario con:
            - componenti_necessari: {nome_componente: quantita_totale_richiesta}
            - componenti_disponibili: {nome_componente: quantita_disponibile}
            - componenti_mancanti: {nome_componente: quantita_mancante}
            - ordine_completabile: bool
        """
        with db_cursor() as cur:
            # Calcola i componenti necessari per l'intero ordine
            componenti_necessari = {}
            
            for progetto_id, quantita in progetti_quantita.items():
                if quantita <= 0:
                    continue
                    
                # Ottieni i componenti di questo progetto
                cur.execute("""
                    SELECT cp.componente_id, m.nome, cp.quantita
                    FROM componenti_progetto cp
                    JOIN magazzino m ON m.id = cp.componente_id
                    WHERE cp.progetto_id = ?
                """, (progetto_id,))
                
                componenti = cur.fetchall()
                
                # Prima sottrai dalla disponibilità in negozio
                cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?", (progetto_id,))
                row_negozio = cur.fetchone()
                disponibili_negozio = row_negozio[0] if row_negozio else 0
                
                da_assemblare = max(0, quantita - disponibili_negozio)
                
                # Aggiungi i componenti necessari per quelli DA ASSEMBLARE
                for comp_id, nome_comp, qta_per_prog in componenti:
                    qta_necessaria = qta_per_prog * da_assemblare
                    
                    if nome_comp not in componenti_necessari:
                        componenti_necessari[nome_comp] = 0
                    componenti_necessari[nome_comp] += qta_necessaria
            
            # Ottieni le disponibilità in magazzino
            componenti_disponibili = {}
            for nome_comp in componenti_necessari.keys():
                cur.execute("SELECT quantita FROM magazzino WHERE nome = ?", (nome_comp,))
                row = cur.fetchone()
                disponibili = row[0] if row else 0
                componenti_disponibili[nome_comp] = disponibili
            
            # Calcola i mancanti
            componenti_mancanti = {}
            ordine_completabile = True
            
            for nome_comp, quantita_necessaria in componenti_necessari.items():
                disponibile = componenti_disponibili.get(nome_comp, 0)
                if disponibile < quantita_necessaria:
                    manca = quantita_necessaria - disponibile
                    componenti_mancanti[nome_comp] = manca
                    ordine_completabile = False
            
            return {
                "componenti_necessari": componenti_necessari,
                "componenti_disponibili": componenti_disponibili,
                "componenti_mancanti": componenti_mancanti,
                "ordine_completabile": ordine_completabile
            }

    @staticmethod
    def calcola_assemblabili_per_progetto(progetti_quantita: Dict[int, int], progetto_id: int) -> int:
        """
        Calcola quanti progetti del tipo `progetto_id` potrebbero essere assemblati,
        considerando che gli altri progetti nell'ordine consumeranno già dei componenti.
        
        Questo risolve il problema: se hai 3 progetti che usano "XX" e ne hai solo 2,
        allora il primo ne avrà 1, il secondo 1, il terzo 0.
        
        Args:
            progetti_quantita: {progetto_id: quantita_richiesta}
            progetto_id: id del progetto per cui calcolare
        
        Returns:
            Numero di progetti di questo tipo che possono essere assemblati
        """
        with db_cursor() as cur:
            # Se la quantità richiesta è 0 o non esiste, non assemblabili
            if progetti_quantita.get(progetto_id, 0) <= 0:
                return 0
            
            # PASSO 1: Calcola i componenti necessari dagli ALTRI progetti (che hanno priority)
            componenti_prenotati_altri = {}
            
            for pid, qty in progetti_quantita.items():
                if pid == progetto_id or qty <= 0:
                    continue
                
                # Disponibilità in negozio per questo altro progetto
                cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?", (pid,))
                row = cur.fetchone()
                disp_negozio = row[0] if row else 0
                
                # Quanti da assemblare per questo altro progetto
                da_assemblare_altri = max(0, qty - disp_negozio)
                
                # Se ne deve assemblare alcuni, calcola il consumo di componenti
                if da_assemblare_altri > 0:
                    cur.execute("""
                        SELECT cp.componente_id, m.nome, cp.quantita
                        FROM componenti_progetto cp
                        JOIN magazzino m ON m.id = cp.componente_id
                        WHERE cp.progetto_id = ?
                    """, (pid,))
                    
                    for comp_id, nome_comp, qta_per_prog in cur.fetchall():
                        qta_consumata = qta_per_prog * da_assemblare_altri
                        if nome_comp not in componenti_prenotati_altri:
                            componenti_prenotati_altri[nome_comp] = 0
                        componenti_prenotati_altri[nome_comp] += qta_consumata
            
            # PASSO 2: Calcola disponibilità residua per THIS progetto
            qty_richiesta = progetti_quantita[progetto_id]
            
            # Disponibilità in negozio
            cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?", (progetto_id,))
            row = cur.fetchone()
            disp_negozio = row[0] if row else 0
            
            # Quanti da assemblare per questo progetto (minimo)
            da_assemblare_questo = max(0, qty_richiesta - disp_negozio)
            
            if da_assemblare_questo <= 0:
                # Tutti disponibili in negozio, nessuno da assemblare
                return 0
            
            # PASSO 3: Per ogni componente, calcola quanti progetti puoi assemblare
            cur.execute("""
                SELECT cp.componente_id, m.nome, cp.quantita
                FROM componenti_progetto cp
                JOIN magazzino m ON m.id = cp.componente_id
                WHERE cp.progetto_id = ?
            """, (progetto_id,))
            
            componenti_questo = cur.fetchall()
            assemblabili = float('inf')
            
            for comp_id, nome_comp, qta_per_prog in componenti_questo:
                if qta_per_prog <= 0:
                    continue
                
                # Disponibilità totale in magazzino
                cur.execute("SELECT quantita FROM magazzino WHERE id = ?", (comp_id,))
                row = cur.fetchone()
                disp_tot = row[0] if row else 0
                
                # Quanto è già prenotato dagli altri
                già_prenotato = componenti_prenotati_altri.get(nome_comp, 0)
                
                # Quanto rimane per questo progetto
                rimane = disp_tot - già_prenotato
                
                # Quanti progetti di questo tipo si possono assemblare con ciò che rimane
                se_solo_questo = rimane // qta_per_prog if qta_per_prog > 0 else 0
                assemblabili = min(assemblabili, se_solo_questo)
            
            if assemblabili == float('inf'):
                assemblabili = 0
            
            return max(0, int(assemblabili))

    @staticmethod
    def crea_ordine(cliente: str, data_consegna: str, note: str,
                    progetti_quantita: Dict[int, Tuple[str, int]]) -> Tuple[bool, str, Optional[int]]:
        """
        Crea un nuovo ordine.
        progetti_quantita: {progetto_id: (nome, quantita)}
        """
        with db_cursor(commit=True) as cur:
            data_ora_completa = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Inserisci ordine
            cur.execute("""
                INSERT INTO ordini (data_inserimento, data_consegna, cliente, note)
                VALUES (?, ?, ?, ?)
            """, (data_inserimento, data_consegna, cliente, note))
            ordine_id = cur.lastrowid

            riepilogo = {
                "disponibili_subito": [],
                "assemblati": [],
                "mancanti": {}
            }

            # Processa ogni progetto
            for progetto_id, (nome, quantita) in progetti_quantita.items():
                # Verifica disponibilità
                info = OrdineManager.verifica_disponibilita_progetto(progetto_id, quantita)

                if info["prelevati_negozio"] > 0:
                    riepilogo["disponibili_subito"].append(f"{nome} (x{info['prelevati_negozio']})")
                    cur.execute("""
                        UPDATE negozio
                        SET disponibili = disponibili - ?, venduti = venduti + ?
                        WHERE progetto_id = ?
                    """, (info["prelevati_negozio"], info["prelevati_negozio"], progetto_id))

                if info["da_assemblare"] > 0:
                    # Aggiorna magazzino per componenti da assemblare
                    cur.execute("""
                        SELECT cp.componente_id, cp.quantita
                        FROM componenti_progetto cp
                        WHERE cp.progetto_id = ?
                    """, (progetto_id,))
                    componenti = cur.fetchall()

                    for comp_id, qta_comp in componenti:
                        richiesta = qta_comp * info["da_assemblare"]
                        cur.execute("""
                            UPDATE magazzino 
                            SET quantita = quantita - ? 
                            WHERE id = ?
                        """, (richiesta, comp_id))

                        # Registra componenti mancanti se negativi
                        cur.execute("SELECT quantita FROM magazzino WHERE id = ?", (comp_id,))
                        nuova_qta = cur.fetchone()[0]
                        if nuova_qta < 0:
                            cur.execute("""
                                INSERT OR IGNORE INTO componenti_mancanti 
                                (progetto_id, componente_id, quantita_mancante, data_rilevamento)
                                VALUES (?, ?, ?, ?)
                            """, (progetto_id, comp_id, -nuova_qta, data_ora_completa))
                            # Se il record esiste, aggiorna la quantità se aumentata
                            cur.execute("""
                                UPDATE componenti_mancanti
                                SET quantita_mancante = MAX(quantita_mancante, ?)
                                WHERE progetto_id = ? AND componente_id = ?
                            """, (-nuova_qta, progetto_id, comp_id))

                    if info["mancanti"]:
                        riepilogo["mancanti"][nome] = info["mancanti"]
                        riepilogo["assemblati"].append(f"{nome} (x{info['da_assemblare']}, ❗ componenti sotto zero)")
                    else:
                        riepilogo["assemblati"].append(f"{nome} (x{info['da_assemblare']})")

                # Salva progetto ordinato
                stato_disp = 1 if info["prelevati_negozio"] > 0 else 0
                cur.execute("""
                    INSERT INTO progetti_ordinati (ordine_id, progetto_id, quantita, disponibile)
                    VALUES (?, ?, ?, ?)
                """, (ordine_id, progetto_id, quantita, stato_disp))

            return True, "Ordine creato con successo", ordine_id

    @staticmethod
    def calcola_prezzi_progetto(progetto_id: int, quantita: int) -> Dict:
        """Calcola i prezzi di un progetto per l'ordine."""
        from logic.progetti import Progetto
        progetto = Progetto(carica_da_id=progetto_id)
        prezzo_unitario = progetto.calcola_prezzo()
        prezzo_totale = prezzo_unitario * quantita

        return {
            "prezzo_unitario": prezzo_unitario,
            "prezzo_totale": prezzo_totale
        }

    @staticmethod
    def crea_ordine_con_prezzi(
            cliente: str,
            data_consegna: str,
            note: str,
            progetti_con_prezzi: Dict[int, Dict],  # Nome chiaro: contiene i prezzi modificati
            acconto: float = 0
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Crea un nuovo ordine con prezzi e acconto.

        Args:
            progetti_con_prezzi: Dict {
                progetto_id: {
                    "nome": nome_progetto,
                    "quantita": quantita,
                    "prezzo_unitario": prezzo_unitario_modificato,
                    "prezzo_totale": prezzo_totale_modificato
                }
            }
        """
        try:
            # 🔥 DEBUG: verifica i dati ricevuti
            print("\n" + "🔧" * 40)
            print("🔧 DATI RICEVUTI DAL MANAGER:")
            print(f"Cliente: {cliente}")
            print(f"Data consegna: {data_consegna}")
            print(f"Acconto: {acconto} €")
            print("\nProgetti con prezzi MODIFICATI (da salvare):")
            for pid, dati in progetti_con_prezzi.items():
                print(f"  Progetto ID: {pid}")
                print(f"    Nome: {dati['nome']}")
                print(f"    Quantità: {dati['quantita']}")
                print(f"    Prezzo unitario: {dati['prezzo_unitario']:.2f} €")
                print(f"    Prezzo totale: {dati['prezzo_totale']:.2f} €")
            print("🔧" * 40 + "\n")

            with db_cursor(commit=True) as cur:
                data_inserimento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Calcola prezzo totale ordine dai prezzi modificati
                prezzo_totale_ordine = sum(p["prezzo_totale"] for p in progetti_con_prezzi.values())

                # Determina stato pagamento in base all'acconto
                if acconto >= prezzo_totale_ordine:
                    stato_pagamento = "PAGATO"
                elif acconto > 0:
                    stato_pagamento = "PARZIALE"
                else:
                    stato_pagamento = "DA PAGARE"

                # Inserisci ordine
                cur.execute("""
                            INSERT INTO ordini (data_inserimento, data_consegna, cliente, note,
                                                prezzo_totale, acconto, stato_pagamento)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                data_inserimento, data_consegna, cliente, note,
                                prezzo_totale_ordine, acconto, stato_pagamento
                            ))
                ordine_id = cur.lastrowid

                print(f"📝 Ordine inserito con ID: {ordine_id}, Totale: {prezzo_totale_ordine} €")

                # Processa ogni progetto con i prezzi modificati
                for progetto_id, dati in progetti_con_prezzi.items():
                    quantita = dati["quantita"]
                    prezzo_unitario = dati["prezzo_unitario"]
                    prezzo_totale = dati["prezzo_totale"]

                    print(
                        f"  📦 Salvo progetto {dati['nome']}: {quantita} pz x {prezzo_unitario:.2f}€ = {prezzo_totale:.2f}€")

                    # Verifica disponibilità in negozio
                    cur.execute("SELECT disponibili FROM negozio WHERE progetto_id = ?", (progetto_id,))
                    row_negozio = cur.fetchone()
                    disponibili_negozio = row_negozio[0] if row_negozio else 0

                    prelevati_negozio = min(quantita, disponibili_negozio)
                    da_assemblare = quantita - prelevati_negozio

                    print(
                        f"     Disponibili in negozio: {disponibili_negozio}, Prelevati: {prelevati_negozio}, Da assemblare: {da_assemblare}")

                    # Aggiorna negozio se necessario
                    if prelevati_negozio > 0:
                        cur.execute("""
                                    UPDATE negozio
                                    SET disponibili = disponibili - ?
                                    WHERE progetto_id = ?
                                    """, (prelevati_negozio, progetto_id))

                    # Gestione componenti da assemblare
                    if da_assemblare > 0:
                        # Preleva componenti dal magazzino
                        cur.execute("""
                                    SELECT cp.componente_id,
                                           cp.quantita * ? AS richiesta,
                                           m.quantita      AS disponibile,
                                           m.nome
                                    FROM componenti_progetto cp
                                             JOIN magazzino m ON m.id = cp.componente_id
                                    WHERE cp.progetto_id = ?
                                    """, (da_assemblare, progetto_id))
                        componenti = cur.fetchall()

                        for comp_id, richiesta, disponibile, nome_comp in componenti:
                            nuovo_valore = disponibile - richiesta
                            cur.execute("UPDATE magazzino SET quantita = ? WHERE id = ?",
                                        (nuovo_valore, comp_id))

                            if nuovo_valore < 0:
                                manca = -nuovo_valore
                                data_ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                cur.execute("""
                                            INSERT OR IGNORE INTO componenti_mancanti
                                                (progetto_id, componente_id, quantita_mancante, data_rilevamento)
                                            VALUES (?, ?, ?, ?)
                                            """, (progetto_id, comp_id, manca, data_ora))
                                # Se il record esiste, aggiorna la quantità se aumentata
                                cur.execute("""
                                            UPDATE componenti_mancanti
                                            SET quantita_mancante = MAX(quantita_mancante, ?)
                                            WHERE progetto_id = ? AND componente_id = ?
                                            """, (manca, progetto_id, comp_id))
                                cur.execute("UPDATE magazzino SET quantita = 0 WHERE id = ?", (comp_id,))
                                print(f"     ⚠️ Componente mancante: {nome_comp} (-{manca})")

                    # Inserisci progetto ordinato con i PREZZI MODIFICATI
                    cur.execute("""
                                INSERT INTO progetti_ordinati (ordine_id, progetto_id, quantita,
                                                               prezzo_unitario, prezzo_totale)
                                VALUES (?, ?, ?, ?, ?)
                                """, (
                                    ordine_id, progetto_id, quantita,
                                    prezzo_unitario, prezzo_totale
                                ))

                    print(f"     ✅ Progetto salvato in progetti_ordinati con prezzi modificati")

                print(f"✅ Ordine {ordine_id} creato con successo!")
                return True, "Ordine creato con successo", ordine_id

        except Exception as e:
            print(f"❌ ERRORE in crea_ordine_con_prezzi: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Errore nella creazione dell'ordine: {str(e)}", None

    @staticmethod
    def get_riepilogo_ordine(ordine_id: int) -> Dict:
        """
        Genera un riepilogo testuale dell'ordine.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT o.cliente, o.data_inserimento, o.data_consegna, o.note,
                       p.nome as progetto, po.quantita,
                       CASE WHEN po.disponibile = 1 THEN '✅' ELSE '🛠️' END as stato
                FROM ordini o
                JOIN progetti_ordinati po ON o.id = po.ordine_id
                JOIN progetti p ON po.progetto_id = p.id
                WHERE o.id = ?
            """, (ordine_id,))
            rows = cur.fetchall()

            if not rows:
                return {}

            cliente = rows[0][0]
            data_ins = rows[0][1]
            data_cons = rows[0][2]
            note = rows[0][3]

            progetti = []
            for row in rows:
                progetti.append({
                    "nome": row[4],
                    "quantita": row[5],
                    "stato": row[6]
                })

            return {
                "cliente": cliente,
                "data_inserimento": data_ins,
                "data_consegna": data_cons,
                "note": note,
                "progetti": progetti
            }


class ComponentiMancantiManager:
    """Gestisce la logica dei componenti mancanti."""

    @staticmethod
    def get_lista_completa() -> List[Dict]:
        """
        Restituisce la lista completa dei componenti mancanti con tutti i dettagli.
        """
        with db_cursor() as cur:
            cur.execute("""
                        SELECT cm.id,
                               cm.progetto_id,
                               p.nome AS progetto_nome,
                               cm.componente_id,
                               m.nome AS componente_nome,
                               cm.quantita_mancante,
                               cm.data_rilevamento
                        FROM componenti_mancanti cm
                                 JOIN progetti p ON cm.progetto_id = p.id
                                 JOIN magazzino m ON cm.componente_id = m.id
                        ORDER BY cm.data_rilevamento DESC
                        """)

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    @staticmethod
    def get_lista() -> List[Dict]:
        """Restituisce la lista di tutti i componenti mancanti."""
        with db_cursor() as cur:
            cur.execute("""
                        SELECT cm.id,
                               cm.progetto_id,
                               cm.componente_id,
                               p.nome AS progetto,
                               m.nome AS componente,
                               cm.quantita_mancante,
                               cm.data_rilevamento
                        FROM componenti_mancanti cm
                                 JOIN progetti p ON cm.progetto_id = p.id
                                 JOIN magazzino m ON cm.componente_id = m.id
                        ORDER BY cm.data_rilevamento DESC
                        """)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    @staticmethod
    def elimina(id_mancante: int) -> Tuple[bool, str]:
        """
        Elimina un componente dalla lista mancanti.
        """
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM componenti_mancanti WHERE id = ?", (id_mancante,))
            if cur.rowcount > 0:
                return True, "Componente rimosso dalla lista mancanti"
            return False, "Componente non trovato"

    @staticmethod
    def get_info_componente(id_mancante: int) -> Optional[Dict]:
        """
        Recupera le informazioni di un componente mancante.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT progetto_id, componente_id, quantita_mancante
                FROM componenti_mancanti 
                WHERE id = ?
            """, (id_mancante,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "progetto_id": row[0],
                "componente_id": row[1],
                "quantita_mancante": row[2]
            }

    @staticmethod
    def get_ultimo_movimento(componente_id: int) -> Optional[Dict]:
        """
        Recupera l'ultimo movimento di magazzino per un componente.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT fornitore, note
                FROM movimenti_magazzino
                WHERE componente_id = ?
                ORDER BY data DESC, id DESC
                LIMIT 1
            """, (componente_id,))
            row = cur.fetchone()
            if not row:
                return {"fornitore": "", "note": ""}
            return {"fornitore": row[0] or "", "note": row[1] or ""}