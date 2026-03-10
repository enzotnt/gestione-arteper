import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '../database/gestione.db')



# -------------------------------------------------
# CONNESSIONE
# -------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(cursor, table_name):
    cursor.execute("""
                   SELECT name
                   FROM sqlite_master
                   WHERE type = 'table'
                     AND name = ?
                   """, (table_name,))
    return cursor.fetchone() is not None


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def add_column_if_missing(cursor, table, column_def):
    column_name = column_def.split()[0]
    if not column_exists(cursor, table, column_name):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
        print(f"✅ Colonna '{column_name}' aggiunta a '{table}'")


# -------------------------------------------------
# RECORD SPECIALI PER ORDINI
# -------------------------------------------------



# -------------------------------------------------
# INIZIALIZZAZIONE DATABASE
# -------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # ==============================
        # TABELLE BASE
        # ==============================

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS magazzino
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           nome
                           TEXT
                           NOT
                           NULL,
                           unita
                           TEXT
                           NOT
                           NULL,
                           quantita
                           REAL
                           NOT
                           NULL
                           DEFAULT
                           0,
                           costo_unitario
                           REAL
                           NOT
                           NULL
                           DEFAULT
                           0,
                           ultimo_acquisto
                           TEXT,
                           fornitore
                           TEXT,
                           immagine_percorso
                           TEXT,
                           note
                           TEXT
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS movimenti_magazzino
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           componente_id
                           INTEGER
                           NOT
                           NULL,
                           data
                           TEXT
                           NOT
                           NULL,
                           quantita
                           REAL
                           NOT
                           NULL,
                           costo_totale
                           REAL
                           NOT
                           NULL,
                           fornitore
                           TEXT,
                           note
                           TEXT,
                           nome
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           componente_id
                       ) REFERENCES magazzino
                       (
                           id
                       )
                           );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS progetti
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           nome
                           TEXT
                           NOT
                           NULL,
                           data_creazione
                           TEXT
                           NOT
                           NULL,
                           moltiplicatore
                           REAL
                           NOT
                           NULL
                           DEFAULT
                           3.0,
                           stato_vendita
                           TEXT
                           DEFAULT
                           '',
                           immagine_percorso
                           TEXT,
                           note
                           TEXT,
                           percorso
                           TEXT
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS componenti_progetto
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           progetto_id
                           INTEGER
                           NOT
                           NULL,
                           componente_id
                           INTEGER
                           NOT
                           NULL,
                           quantita
                           REAL
                           NOT
                           NULL,
                           moltiplicatore
                           REAL
                           NOT
                           NULL
                           DEFAULT
                           1.0,
                           FOREIGN
                           KEY
                       (
                           progetto_id
                       ) REFERENCES progetti
                       (
                           id
                       ),
                           FOREIGN KEY
                       (
                           componente_id
                       ) REFERENCES magazzino
                       (
                           id
                       )
                           );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS storico_progetti
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY,
                           nome
                           TEXT
                           NOT
                           NULL,
                           data_creazione
                           TEXT
                           NOT
                           NULL,
                           moltiplicatore
                           REAL
                           NOT
                           NULL,
                           stato_vendita
                           TEXT,
                           immagine_percorso
                           TEXT,
                           note
                           TEXT
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS storico_note_progetti
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           progetto_id
                           INTEGER
                           NOT
                           NULL,
                           data
                           TEXT
                           NOT
                           NULL,
                           nota
                           TEXT
                           NOT
                           NULL,
                           FOREIGN
                           KEY
                       (
                           progetto_id
                       ) REFERENCES progetti
                       (
                           id
                       )
                           );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS negozio
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           progetto_id
                           INTEGER
                           NOT
                           NULL,
                           nome_progetto_negozio
                           TEXT
                           NOT
                           NULL,
                           data_inserimento
                           TEXT
                           NOT
                           NULL,
                           prezzo_vendita
                           REAL
                           NOT
                           NULL,
                           disponibili
                           INTEGER
                           NOT
                           NULL,
                           venduti
                           INTEGER
                           NOT
                           NULL
                           DEFAULT
                           0,
                           FOREIGN
                           KEY
                       (
                           progetto_id
                       ) REFERENCES progetti
                       (
                           id
                       )
                           );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS venduti
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           negozio_id
                           INTEGER
                           NOT
                           NULL,
                           data_vendita
                           TEXT
                           NOT
                           NULL,
                           cliente
                           TEXT
                           NOT
                           NULL,
                           quantita
                           INTEGER
                           NOT
                           NULL,
                           prezzo_totale
                           REAL
                           NOT
                           NULL,
                           prezzo_unitario
                           REAL
                           NOT
                           NULL,
                           costo_unitario
                           REAL,
                           costo_totale
                           REAL,
                           ricavo
                           REAL,
                           note
                           TEXT,
                           immagine_percorso
                           TEXT,
                           nome
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           negozio_id
                       ) REFERENCES negozio
                       (
                           id
                       )
                           );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS spese_gestione
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           data
                           TEXT
                           NOT
                           NULL,
                           categoria
                           TEXT
                           NOT
                           NULL,
                           descrizione
                           TEXT,
                           importo
                           REAL
                           NOT
                           NULL,
                           metodo_pagamento
                           TEXT,
                           note
                           TEXT
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS bilanci
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           periodo
                           TEXT
                           NOT
                           NULL,
                           spese_magazzino
                           REAL
                           NOT
                           NULL,
                           spese_gestione
                           REAL
                           NOT
                           NULL,
                           ricavi
                           REAL
                           NOT
                           NULL,
                           utile_netto
                           REAL
                           NOT
                           NULL,
                           data_creazione
                           TEXT
                           NOT
                           NULL
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS ordini
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           data_inserimento
                           TEXT
                           NOT
                           NULL,
                           data_consegna
                           TEXT,
                           cliente
                           TEXT
                           NOT
                           NULL,
                           consegnato
                           INTEGER
                           DEFAULT
                           0,
                           note
                           TEXT,
                           data_in_lavorazione
                           TEXT
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS progetti_ordinati
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           ordine_id
                           INTEGER
                           NOT
                           NULL,
                           progetto_id
                           INTEGER
                           NOT
                           NULL,
                           quantita
                           INTEGER
                           NOT
                           NULL
                           DEFAULT
                           1,
                           disponibile
                           INTEGER
                           DEFAULT
                           1,
                           quantita_disponibile
                           INTEGER
                           DEFAULT
                           0,
                           assemblato
                           INTEGER
                           DEFAULT
                           0,
                           data_lavorazione
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           ordine_id
                       ) REFERENCES ordini
                       (
                           id
                       ),
                           FOREIGN KEY
                       (
                           progetto_id
                       ) REFERENCES progetti
                       (
                           id
                       )
                           );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS componenti_mancanti
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           progetto_id
                           INTEGER
                           NOT
                           NULL,
                           componente_id
                           INTEGER
                           NOT
                           NULL,
                           quantita_mancante
                           INTEGER
                           NOT
                           NULL,
                           data_rilevamento
                           TEXT
                           NOT
                           NULL,
                           FOREIGN
                           KEY
                       (
                           progetto_id
                       ) REFERENCES progetti
                       (
                           id
                       ),
                           FOREIGN KEY
                       (
                           componente_id
                       ) REFERENCES magazzino
                       (
                           id
                       )
                           );
                       """)

        # ==============================
        # NUOVE TABELLE PER BUONI REGALO/SCONTO
        # ==============================

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS buoni
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           codice
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           tipo
                           TEXT
                           NOT
                           NULL,
                           valore_originale
                           REAL
                           NOT
                           NULL,
                           valore_residuo
                           REAL
                           NOT
                           NULL,
                           data_creazione
                           TEXT
                           NOT
                           NULL,
                           data_scadenza
                           TEXT,
                           cliente_acquirente
                           TEXT
                           NOT
                           NULL,
                           cliente_beneficiario
                           TEXT,
                           note
                           TEXT,
                           stato
                           TEXT
                           DEFAULT
                           'ATTIVO'
                       );
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS utilizzi_buoni
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           buono_id
                           INTEGER
                           NOT
                           NULL,
                           vendita_id
                           INTEGER,
                           data_utilizzo
                           TEXT
                           NOT
                           NULL,
                           importo_utilizzato
                           REAL
                           NOT
                           NULL,
                           note
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           buono_id
                       ) REFERENCES buoni
                       (
                           id
                       ),
                           FOREIGN KEY
                       (
                           vendita_id
                       ) REFERENCES venduti
                       (
                           id
                       )
                           );
                       """)

        # ==============================
        # INDICI PER OTTIMIZZARE LE RICERCHE
        # ==============================

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_buoni_codice ON buoni(codice);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_buoni_stato ON buoni(stato);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_buoni_scadenza ON buoni(data_scadenza);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_utilizzi_buono ON utilizzi_buoni(buono_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_utilizzi_vendita ON utilizzi_buoni(vendita_id);")

        # -------------------------------------------------
        # MIGRAZIONI (COLONNE AGGIUNTIVE)
        # -------------------------------------------------

        # Migrazioni per ordini
        add_column_if_missing(cursor, "ordini", "data_in_lavorazione TEXT")
        add_column_if_missing(cursor, "ordini", "prezzo_totale REAL DEFAULT 0")
        add_column_if_missing(cursor, "ordini", "acconto REAL DEFAULT 0")
        add_column_if_missing(cursor, "ordini", "stato_pagamento TEXT DEFAULT 'DA PAGARE'")

        # Migrazioni per progetti
        add_column_if_missing(cursor, "progetti", "stato_vendita TEXT DEFAULT ''")

        # Migrazioni per venduti
        add_column_if_missing(cursor, "venduti", "immagine_percorso TEXT")

        # Migrazioni per progetti_ordinati
        add_column_if_missing(cursor, "progetti_ordinati", "assemblato INTEGER DEFAULT 0")
        add_column_if_missing(cursor, "progetti_ordinati", "data_lavorazione TEXT")
        add_column_if_missing(cursor, "progetti_ordinati", "disponibile INTEGER DEFAULT 1")
        add_column_if_missing(cursor, "progetti_ordinati", "quantita_disponibile INTEGER DEFAULT 0")
        add_column_if_missing(cursor, "progetti_ordinati", "prezzo_unitario REAL DEFAULT 0")
        add_column_if_missing(cursor, "progetti_ordinati", "prezzo_totale REAL DEFAULT 0")

        # Migrazioni per buoni
        add_column_if_missing(cursor, "buoni", "incassato REAL DEFAULT 0")
        add_column_if_missing(cursor, "buoni", "data_incasso TEXT")
        add_column_if_missing(cursor, "buoni", "metodo_pagamento TEXT")

        conn.commit()
        print("✅ Database inizializzato correttamente")

        # NUOVA MODIFICA


    except Exception as e:
        print(f"❌ Errore durante l'inizializzazione del database: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()
        print("🔒 Connessione al database chiusa")


# -------------------------------------------------
# UTILITÀ AGGIUNTIVE
# -------------------------------------------------

def get_db_path():
    """Restituisce il percorso del database."""
    return DB_PATH


def backup_database(destinazione=None):
    """Crea un backup del database."""
    if not destinazione:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destinazione = os.path.join(os.path.dirname(DB_PATH), f"backup_{timestamp}.db")

    import shutil
    shutil.copy2(DB_PATH, destinazione)
    return destinazione


if __name__ == "__main__":
    init_db()

    print(f"📁 Database: {DB_PATH}")
    print("🏁 Inizializzazione completata!")
