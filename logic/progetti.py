# logic/progetti.py
# Gestione dei progetti: creazione, duplicazione, componenti - VERSIONE OTTIMIZZATA

from datetime import datetime
from utils.helpers import db_cursor  # Riutilizziamo il context manager


class Progetto:
    """Rappresenta un progetto con i suoi componenti e calcoli."""

    def __init__(self, id=None, data_creazione=None, nome="", stato="",
                 moltiplicatore=3.0, note="", immagine_percorso=None,
                 carica_da_id=None, percorso=None):
        """
        Inizializza un progetto. Se carica_da_id è specificato,
        carica i dati dal database.
        """
        if carica_da_id:
            self.carica_da_db(carica_da_id)
        else:
            self.id = id
            self.data_creazione = data_creazione
            self.nome = nome
            self.stato = stato
            self.moltiplicatore = moltiplicatore
            self.note = note
            self.immagine_percorso = immagine_percorso
            self.percorso = percorso

    # =========================================================================
    # METODI DI CARICAMENTO DATI
    # =========================================================================

    def carica_da_db(self, progetto_id):
        """Carica i dati del progetto dal database."""
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                        SELECT id,
                               data_creazione,
                               nome,
                               stato_vendita,
                               moltiplicatore,
                               note,
                               immagine_percorso,
                               percorso
                        FROM progetti
                        WHERE id = ?
                        """, (progetto_id,))
            row = cur.fetchone()

            if not row:
                raise ValueError(f"Progetto con ID {progetto_id} non trovato.")

            self.id = row[0]
            self.data_creazione = row[1]
            self.nome = row[2]
            self.stato = row[3]
            self.moltiplicatore = row[4]
            self.note = row[5]
            self.immagine_percorso = row[6]
            self.percorso = row[7]

    @classmethod
    def crea_progetto(cls, nome, componenti, moltiplicatore=3.0, immagine=None, percorso=None):
        from datetime import datetime
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        from db.database import get_connection
        conn = get_connection()
        cur = conn.cursor()

        # Inserisci il progetto
        cur.execute("""
                    INSERT INTO progetti (data_creazione, nome, stato_vendita, moltiplicatore, immagine_percorso, note,
                                          percorso)
                    VALUES (?, ?, '', ?, ?, '', ?)
                    """, (data, nome, moltiplicatore, immagine, percorso))
        progetto_id = cur.lastrowid

        # Inserisci i componenti prelevati con moltiplicatore individuale
        for comp_id, quantita, moltiplicatore_comp in componenti:
            # Scala il magazzino
            cur.execute("UPDATE magazzino SET quantita = quantita - ? WHERE id = ?", (quantita, comp_id))

            # Inserisci nel progetto
            cur.execute("""
                        INSERT INTO componenti_progetto (progetto_id, componente_id, quantita, moltiplicatore)
                        VALUES (?, ?, ?, ?)
                        """, (progetto_id, comp_id, quantita, moltiplicatore_comp))

        # 🔥 AGGIUNGI STORICO PROGETTO (con la stessa data di creazione)
        cur.execute("""
                    INSERT INTO storico_progetti (id, nome, data_creazione, moltiplicatore,
                                                  stato_vendita, immagine_percorso, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (progetto_id, nome, data, moltiplicatore, '', immagine, ''))

        conn.commit()
        conn.close()

        return cls(carica_da_id=progetto_id)


    # =========================================================================
    # METODI DI LETTURA
    # =========================================================================

    def get_componenti(self):
        """Restituisce la lista dei componenti del progetto."""
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                        SELECT c.nome, cp.quantita, c.costo_unitario, cp.moltiplicatore, c.id
                        FROM componenti_progetto cp
                                 JOIN magazzino c ON cp.componente_id = c.id
                        WHERE cp.progetto_id = ?
                        """, (self.id,))

            return [
                {
                    "id": r[4],
                    "nome": r[0],
                    "quantita": r[1],
                    "costo_unitario": r[2],
                    "moltiplicatore": r[3]
                }
                for r in cur.fetchall()
            ]

    def calcola_costo(self):
        """Calcola il costo totale dei componenti."""
        return sum(c['quantita'] * c['costo_unitario'] for c in self.get_componenti())

    def calcola_prezzo(self):
        """Calcola il prezzo totale del progetto basato sui componenti."""
        return sum(c['quantita'] * c['costo_unitario'] * c['moltiplicatore']
                   for c in self.get_componenti())

    def calcola_ricavo(self):
        """Calcola il ricavo (prezzo - costo)."""
        return self.calcola_prezzo() - self.calcola_costo()

    def get_percorso_immagine(self):
        """Restituisce il percorso dell'immagine."""
        return self.immagine_percorso

    # =========================================================================
    # METODI DI MODIFICA
    # =========================================================================

    def aggiorna_note(self, nuove_note):
        """Aggiorna le note del progetto e registra nello storico note."""
        with db_cursor(commit=True, show_errors=False) as cur:
            # Aggiorna le note nel progetto
            cur.execute("UPDATE progetti SET note = ? WHERE id = ?", (nuove_note, self.id))

            # 🔥 REGISTRA NELLO STORICO NOTE
            cur.execute("""
                        INSERT INTO storico_note_progetti (progetto_id, data, nota)
                        VALUES (?, ?, ?)
                        """, (self.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nuove_note))

            self.note = nuove_note

    def aggiorna_nome(self, nuovo_nome):
        """Aggiorna il nome del progetto."""
        self._esegui_update("nome", nuovo_nome, "nome = ?")
        self.nome = nuovo_nome

    def aggiorna_moltiplicatore(self, nuovo_m):
        """Aggiorna il moltiplicatore del progetto."""
        self._esegui_update("moltiplicatore", nuovo_m, "moltiplicatore = ?")
        self.moltiplicatore = nuovo_m

    def _esegui_update(self, campo, valore, clausola_update):
        """Metodo helper per eseguire update generici."""
        with db_cursor(commit=True, show_errors=False) as cur:
            cur.execute(f"UPDATE progetti SET {clausola_update} WHERE id = ?",
                        (valore, self.id))

    def salva_su_db(self):
        """Salva le modifiche correnti del progetto e registra nello storico."""
        from datetime import datetime
        from db.database import get_connection
        data_modifica = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_connection()
        cur = conn.cursor()

        # Aggiorna il progetto
        cur.execute("""
                    UPDATE progetti
                    SET nome              = ?,
                        moltiplicatore    = ?,
                        immagine_percorso = ?,
                        percorso          = ?
                    WHERE id = ?
                    """, (self.nome, self.moltiplicatore, self.immagine_percorso, self.percorso, self.id))

        # 🔥 CORREZIONE: Non usare INSERT, ma UPDATE nella tabella storico
        # Oppure usa INSERT con AUTOINCREMENT (ma la tabella non ce l'ha)
        # Per ora, facciamo UPDATE se esiste, altrimenti INSERT
        cur.execute("SELECT COUNT(*) FROM storico_progetti WHERE id = ?", (self.id,))
        esiste = cur.fetchone()[0] > 0

        if esiste:
            cur.execute("""
                        UPDATE storico_progetti
                        SET nome              = ?,
                            data_creazione    = ?,
                            moltiplicatore    = ?,
                            stato_vendita     = ?,
                            immagine_percorso = ?,
                            note              = ?
                        WHERE id = ?
                        """, (self.nome, data_modifica, self.moltiplicatore,
                              self.stato, self.immagine_percorso, self.note, self.id))
        else:
            cur.execute("""
                        INSERT INTO storico_progetti (id, nome, data_creazione, moltiplicatore,
                                                      stato_vendita, immagine_percorso, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (self.id, self.nome, data_modifica, self.moltiplicatore,
                              self.stato, self.immagine_percorso, self.note))

        conn.commit()
        conn.close()

    # =========================================================================
    # GESTIONE COMPONENTI DEL PROGETTO
    # =========================================================================

    def _verifica_disponibilita(self, componente_id, quantita_richiesta):
        """
        Verifica se un componente è disponibile in magazzino.
        Restituisce (disponibile, nome, quantita_disponibile)
        """
        with db_cursor(show_errors=False) as cur:
            cur.execute("SELECT nome, quantita FROM magazzino WHERE id = ?", (componente_id,))
            row = cur.fetchone()

            if not row:
                raise ValueError(f"Componente ID {componente_id} non trovato.")

            nome, disponibile = row
            if quantita_richiesta > disponibile:
                return False, nome, disponibile
            return True, nome, disponibile

    def _modifica_magazzino(self, componente_id, quantita, operazione="sottrai"):
        """Modifica la quantità in magazzino (sottrai o aggiungi)."""
        with db_cursor(commit=True, show_errors=False) as cur:
            segno = "-" if operazione == "sottrai" else "+"
            cur.execute(f"UPDATE magazzino SET quantita = quantita {segno} ? WHERE id = ?",
                        (quantita, componente_id))

    def aggiungi_componente(self, nome_comp, quantita):
        """Aggiunge un componente al progetto cercandolo per nome."""
        with db_cursor(commit=True, show_errors=False) as cur:
            # Trova il componente per nome
            cur.execute("SELECT id, quantita FROM magazzino WHERE nome = ?", (nome_comp,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Componente '{nome_comp}' non trovato.")

            comp_id, disponibilita = row
            if disponibilita < quantita:
                raise ValueError(f"Quantità insufficiente per '{nome_comp}'. Disponibile: {disponibilita}")

            # Scala magazzino e aggiungi al progetto
            cur.execute("UPDATE magazzino SET quantita = quantita - ? WHERE id = ?", (quantita, comp_id))
            cur.execute("""
                        INSERT INTO componenti_progetto (progetto_id, componente_id, quantita, moltiplicatore)
                        VALUES (?, ?, ?, ?)
                        """, (self.id, comp_id, quantita, self.moltiplicatore))

    def aggiungi_componente_da_id(self, componente_id, quantita, moltiplicatore=None):
        """
        Aggiunge un componente al progetto usando il suo ID.
        Se moltiplicatore non è specificato, usa quello del progetto.
        """
        if moltiplicatore is None:
            moltiplicatore = self.moltiplicatore

        # Verifica disponibilità
        ok, nome, disp = self._verifica_disponibilita(componente_id, quantita)
        if not ok:
            raise ValueError(
                f"Quantità insufficiente per '{nome}'. "
                f"Disponibile: {disp}, richiesto: {quantita}"
            )

        with db_cursor(commit=True, show_errors=False) as cur:
            # Scala il magazzino
            cur.execute("UPDATE magazzino SET quantita = quantita - ? WHERE id = ?",
                        (quantita, componente_id))

            # Inserisce nel progetto
            cur.execute("""
                        INSERT INTO componenti_progetto (progetto_id, componente_id, quantita, moltiplicatore)
                        VALUES (?, ?, ?, ?)
                        """, (self.id, componente_id, quantita, moltiplicatore))

    def rimuovi_componente(self, nome_comp):
        """Rimuove un componente dal progetto e lo restituisce al magazzino."""
        with db_cursor(commit=True, show_errors=False) as cur:
            # Trova componente_id e quantità
            cur.execute("""
                        SELECT c.id, cp.quantita
                        FROM componenti_progetto cp
                                 JOIN magazzino c ON cp.componente_id = c.id
                        WHERE cp.progetto_id = ?
                          AND c.nome = ?
                        """, (self.id, nome_comp))
            row = cur.fetchone()

            if not row:
                raise ValueError(f"Componente '{nome_comp}' non trovato nel progetto.")

            comp_id, qta = row

            # Rimuovi dal progetto
            cur.execute("""
                        DELETE
                        FROM componenti_progetto
                        WHERE progetto_id = ?
                          AND componente_id = ?
                        """, (self.id, comp_id))

            # Restituisci al magazzino
            cur.execute("UPDATE magazzino SET quantita = quantita + ? WHERE id = ?",
                        (qta, comp_id))

    # =========================================================================
    # DUPLICAZIONE ED ELIMINAZIONE
    # =========================================================================

    def duplica(self, nuovo_nome):
        """
        Crea una copia del progetto con un nuovo nome.
        I componenti vengono nuovamente prelevati dal magazzino.
        """
        componenti = self.get_componenti()
        componenti_id_qta_molt = []

        with db_cursor(show_errors=False) as cur:
            for comp in componenti:
                cur.execute("SELECT id FROM magazzino WHERE nome = ?", (comp['nome'],))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Componente '{comp['nome']}' non trovato in magazzino.")
                comp_id = row[0]
                componenti_id_qta_molt.append((comp_id, comp['quantita'], comp['moltiplicatore']))

        return Progetto.crea_progetto(
            nuovo_nome,
            componenti_id_qta_molt,
            self.moltiplicatore,
            self.immagine_percorso,
            self.percorso
        )

    def elimina(self):
        """
        Elimina il progetto e i suoi componenti associati.
        NOTA: NON restituisce i componenti al magazzino.
        """
        with db_cursor(commit=True, show_errors=False) as cur:
            # Elimina prima i componenti associati (FK)
            cur.execute("DELETE FROM componenti_progetto WHERE progetto_id = ?", (self.id,))
            # Poi il progetto
            cur.execute("DELETE FROM progetti WHERE id = ?", (self.id,))

    # In logic/progetti.py - da aggiungere alla classe Progetto
    def get_storico(self):
        """
        Restituisce lo storico completo delle modifiche del progetto.
        """
        with db_cursor(show_errors=False) as cur:
            cur.execute("""
                        SELECT data, tipo, descrizione
                        FROM (
                                 -- Storico modifiche progetto
                                 SELECT data_creazione                                              as data,
                                        'Modifica progetto'                                         as tipo,
                                        'Nome: ' || nome || ' | Moltiplicatore: ' || moltiplicatore as descrizione
                                 FROM storico_progetti
                                 WHERE id = ?

                                 UNION ALL

                                 -- Storico note
                                 SELECT data,
                                        'Nota' as tipo,
                                        nota   as descrizione
                                 FROM storico_note_progetti
                                 WHERE progetto_id = ?

                                 UNION ALL

                                 -- Vendite (se vuoi includerle)
                                 SELECT n.data_inserimento                                              as data,
                                        'Vendita'                                                       as tipo,
                                        'Vendute ' || n.disponibili || ' copie a €' || n.prezzo_vendita as descrizione
                                 FROM negozio n
                                 WHERE n.progetto_id = ?)
                        ORDER BY data DESC
                        """, (self.id, self.id, self.id))

            return cur.fetchall()