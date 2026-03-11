# logic/magazzino.py
# Gestione del magazzino: componenti, movimenti, scorte - VERSIONE OTTIMIZZATA

from datetime import date
from utils.helpers import db_cursor


# =============================================================================
# FUNZIONI HELPER PRIVATE (non chiamabili direttamente dall'esterno)
# =============================================================================

def _get_componente_by_id(componente_id):
    """Recupera i dati di un componente dal database (uso interno)."""
    with db_cursor(show_errors=False) as cur:
        cur.execute("SELECT quantita, costo_unitario FROM magazzino WHERE id = ?", (componente_id,))
        return cur.fetchone()


def _calcola_nuovo_costo_unitario(q_attuale, costo_attuale, q_aggiunta, costo_totale_aggiunta):
    """
    Calcola il nuovo costo unitario medio dopo un acquisto.
    Formula: (valore_attuale + valore_aggiunto) / quantità_totale
    """
    if q_attuale + q_aggiunta == 0:
        return 0
    return ((q_attuale * costo_attuale) + costo_totale_aggiunta) / (q_attuale + q_aggiunta)


def _registra_movimento(cur, componente_id, data, nome, quantita, costo_totale, fornitore, note):
    """Registra un movimento nello storico (usa il cursor esistente)."""
    cur.execute("""
                INSERT INTO movimenti_magazzino
                    (componente_id, data, nome, quantita, costo_totale, fornitore, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (componente_id, data, nome, quantita, costo_totale, fornitore, note))


# =============================================================================
# FUNZIONI PUBBLICHE (API del modulo)
# =============================================================================

def aggiorna_note(id_componente, nuova_nota):
    """Aggiorna le note di un componente esistente."""
    with db_cursor(commit=True, show_errors=False) as cur:
        cur.execute("UPDATE magazzino SET note = ? WHERE id = ?", (nuova_nota, id_componente))


def aggiungi_componente(nome, unita, quantita, costo_totale, note=None, fornitore=None, immagine_percorso=None):
    """
    Aggiunge un nuovo componente al magazzino e registra il movimento iniziale.
    Restituisce l'ID del nuovo componente.
    """
    if quantita <= 0:
        raise ValueError("La quantità deve essere maggiore di zero")

    costo_unitario = costo_totale / quantita
    oggi = date.today().isoformat()

    with db_cursor(commit=True, show_errors=False) as cur:
        # Inserimento nella tabella magazzino
        cur.execute("""
                    INSERT INTO magazzino
                    (nome, unita, quantita, costo_unitario, ultimo_acquisto, fornitore, immagine_percorso, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (nome, unita, quantita, costo_unitario, oggi, fornitore, immagine_percorso, note))

        componente_id = cur.lastrowid

        # Registrazione nel movimento storico
        _registra_movimento(
            cur, componente_id, oggi, nome, quantita,
            costo_totale, fornitore, note
        )

        return componente_id


@staticmethod
def aggiungi_scorte(componente_id, quantita, costo_totale, fornitore="", note=""):
    """
    Aggiunge scorte a un componente esistente.
    Le nuove scorte coprono prima i componenti mancanti,
    poi l'eccedenza aumenta il magazzino.
    """
    with db_cursor(commit=True, show_errors=False) as cur:
        # Recupera i dati attuali del componente
        cur.execute("SELECT nome, quantita, costo_unitario FROM magazzino WHERE id = ?", (componente_id,))
        riga = cur.fetchone()
        if not riga:
            raise ValueError(f"Componente con ID {componente_id} non trovato.")

        nome, q_attuale, costo_attuale = riga

        # 🔥 PASSO 1: Verifica se ci sono componenti mancanti da coprire
        cur.execute("""
            SELECT id, quantita_mancante
            FROM componenti_mancanti
            WHERE componente_id = ?
            ORDER BY data_rilevamento ASC
        """, (componente_id,))
        mancanti = cur.fetchall()

        q_rimasta = quantita
        costo_totale_originale = costo_totale
        costo_unitario_acquisto = costo_totale / quantita if quantita > 0 else 0

        # Se ci sono mancanti, coprili prima
        if mancanti:
            for mancante_id, q_mancante in mancanti:
                if q_rimasta <= 0:
                    break

                if q_rimasta >= q_mancante:
                    # Copre completamente questo mancante
                    cur.execute("DELETE FROM componenti_mancanti WHERE id = ?", (mancante_id,))
                    q_rimasta -= q_mancante
                    # Il costo per coprire il mancante viene assorbito (non aumenta il magazzino)
                else:
                    # Copre parzialmente questo mancante
                    nuovo_mancante = q_mancante - q_rimasta
                    cur.execute("""
                        UPDATE componenti_mancanti
                        SET quantita_mancante = ?
                        WHERE id = ?
                    """, (nuovo_mancante, mancante_id))
                    q_rimasta = 0
                    break

        # 🔥 PASSO 2: Calcola il nuovo costo unitario SOLO per la parte che va in magazzino
        if q_rimasta > 0:
            # C'è eccedenza che va in magazzino
            costo_eccedenza = q_rimasta * costo_unitario_acquisto
            nuovo_costo_unitario = _calcola_nuovo_costo_unitario(
                q_attuale, costo_attuale, q_rimasta, costo_eccedenza
            )
            nuova_quantita = q_attuale + q_rimasta
        else:
            # Tutto è andato a coprire mancanti, il magazzino non aumenta
            nuovo_costo_unitario = costo_attuale  # invariato
            nuova_quantita = q_attuale

        # 🔥 PASSO 3: Aggiorna il magazzino
        cur.execute("""
            UPDATE magazzino
            SET quantita = ?, costo_unitario = ?, ultimo_acquisto = ?, fornitore = ?
            WHERE id = ?
        """, (nuova_quantita, nuovo_costo_unitario, date.today().isoformat(), fornitore, componente_id))

        # 🔥 PASSO 4: Registra il movimento (solo la parte effettivamente aggiunta al magazzino)
        if q_rimasta > 0:
            _registra_movimento(
                cur, componente_id, date.today().isoformat(), nome,
                q_rimasta, costo_eccedenza, fornitore, note
            )
        else:
            # Se tutto è andato a coprire mancanti, registra comunque un movimento con costo 0
            _registra_movimento(
                cur, componente_id, date.today().isoformat(), nome,
                0, 0, fornitore, f"[COPERTO MANCANTI] {note}"
            )


def elimina_componente(componente_id):
    """Elimina un componente dal magazzino."""
    with db_cursor(commit=True, show_errors=False) as cur:
        cur.execute("DELETE FROM magazzino WHERE id = ?", (componente_id,))
        # Opzionale: eliminare anche lo storico?
        # cur.execute("DELETE FROM movimenti_magazzino WHERE componente_id = ?", (componente_id,))


def get_lista_componenti():
    """Restituisce tutti i componenti del magazzino."""
    with db_cursor(show_errors=False) as cur:
        cur.execute("""
                    SELECT id,
                           nome,
                           unita,
                           quantita,
                           costo_unitario,
                           ultimo_acquisto,
                           fornitore,
                           immagine_percorso,
                           note
                    FROM magazzino
                    ORDER BY nome
                    """)
        return cur.fetchall()


def get_storico_acquisti(componente_id):
    """Restituisce lo storico degli acquisti per un componente."""
    with db_cursor(show_errors=False) as cur:
        cur.execute("""
                    SELECT data, quantita, costo_totale, fornitore, note
                    FROM movimenti_magazzino
                    WHERE componente_id = ?
                    ORDER BY data DESC
                    """, (componente_id,))
        return cur.fetchall()


def get_percorso_immagine(componente_id):
    """Restituisce il percorso dell'immagine di un componente."""
    with db_cursor(show_errors=False) as cur:
        cur.execute("SELECT immagine_percorso FROM magazzino WHERE id = ?", (componente_id,))
        row = cur.fetchone()
        return row[0] if row else None


@staticmethod
def sincronizza_componenti_mancanti(componente_id, quantita_aggiunta, cur=None):
    """
    Aggiorna la tabella componenti_mancanti in base alle nuove scorte aggiunte.
    - Se la quantità aggiunta copre tutti i mancanti → elimina il record.
    - Se copre solo in parte → scala la quantità mancante.

    Args:
        componente_id: ID del componente
        quantita_aggiunta: quantità aggiunta al magazzino
        cur: cursor opzionale (se fornito, usa quello invece di crearne uno nuovo)
    """

    def esegui_sincronizzazione(cursor):
        cursor.execute("""
                       SELECT id, quantita_mancante
                       FROM componenti_mancanti
                       WHERE componente_id = ?
                       ORDER BY data_rilevamento ASC
                       """, (componente_id,))
        records = cursor.fetchall()

        q_rimasta = quantita_aggiunta

        for mancante_id, q_mancante in records:
            if q_rimasta >= q_mancante:
                # Coperto interamente → elimino record
                cursor.execute("DELETE FROM componenti_mancanti WHERE id = ?", (mancante_id,))
                q_rimasta -= q_mancante
            else:
                # Coperto solo parzialmente → aggiorno quantità mancante
                nuovo_mancante = q_mancante - q_rimasta
                cursor.execute("""
                               UPDATE componenti_mancanti
                               SET quantita_mancante = ?
                               WHERE id = ?
                               """, (nuovo_mancante, mancante_id))
                q_rimasta = 0
                break  # finito

    if cur:
        # Se abbiamo un cursor, usiamo quello
        esegui_sincronizzazione(cur)
    else:
        # Altrimenti creiamo un nuovo context manager
        with db_cursor(commit=True, show_errors=False) as new_cur:
            esegui_sincronizzazione(new_cur)


def aggiorna_componente(componente_id, nome, unita, fornitore, note, immagine_percorso=None):
    """
    Aggiorna i dati di un componente esistente.
    """
    with db_cursor(commit=True, show_errors=False) as cur:
        cur.execute("""
                    UPDATE magazzino
                    SET nome              = ?,
                        unita             = ?,
                        fornitore         = ?,
                        note              = ?,
                        immagine_percorso = ?
                    WHERE id = ?
                    """, (nome, unita, fornitore, note, immagine_percorso, componente_id))


# logic/magazzino.py - Aggiungi questo metodo alla classe Magazzino

@staticmethod
def get_componente_by_id(componente_id):
    """Recupera un componente dal database tramite ID."""
    with db_cursor() as cur:
        cur.execute("""
                    SELECT id,
                           nome,
                           unita,
                           quantita,
                           costo_unitario,
                           ultimo_acquisto,
                           fornitore,
                           immagine_percorso,
                           note
                    FROM magazzino
                    WHERE id = ?
                    """, (componente_id,))
        row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "nome": row[1],
            "unita": row[2],
            "quantita": row[3],
            "costo_unitario": row[4],
            "ultimo_acquisto": row[5],
            "fornitore": row[6],
            "immagine_percorso": row[7],
            "note": row[8]
        }

