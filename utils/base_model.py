from utils.db_utils import with_db


class BaseModel:
    """Classe base per tutti i modelli (progetti, magazzino, etc.)"""

    table_name = None  # Da overrideare

    @classmethod
    @with_db(commit=False)
    def get_by_id(cls, cur, id):
        cur.execute(f"SELECT * FROM {cls.table_name} WHERE id = ?", (id,))
        row = cur.fetchone()
        if row:
            return cls._from_row(row)
        return None

    @with_db(commit=True)
    def delete(self, cur):
        cur.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (self.id,))

    @with_db(commit=True)
    def save(self, cur):
        # Implementazione base, da overrideare
        pass