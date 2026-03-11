from contextlib import contextmanager
from db.database import get_connection
import tkinter.messagebox as messagebox


@contextmanager
def db_cursor(commit=False, show_errors=True, parent=None):
    """
    Context manager per operazioni database.

    Args:
        commit: Se True, fa commit automatico
        show_errors: Se True, mostra errori in messagebox (per GUI)
        parent: Widget parent per messagebox
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        if show_errors:
            messagebox.showerror("Errore Database", str(e), parent=parent)
        else:
            raise
    finally:
        if conn:
            conn.close()


# Decoratore per metodi che usano il database
def with_db(commit=False, show_errors=True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with db_cursor(commit=commit, show_errors=show_errors) as cur:
                return func(cur, *args, **kwargs)

        return wrapper

    return decorator