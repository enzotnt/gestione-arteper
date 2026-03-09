# config/config.py
import json
import os
from typing import Any, Dict, Optional

CONFIG_FILE = "config.json"

# Valori di default
DEFAULT_CONFIG = {
    "anagrafica": {
        "nome_cognome": "Nome Cognome",
        "tessera": "12345678",
        "rilasciato_il": "09/07/2024",
        "comune": "Comune di Comune-Nome"
    },
    "app": {
        "theme": "clam",
        "font_size": 12,
        "backup_automatico": True,
        "backup_giorni": 7
    },
    "mercati": {
        "ultimo_luogo": "",
        "ultima_data": "",
        "cartella_pdf_default": ""
    },

    "ordini": {
        "cartella_sorgente": "FILE_ORDINI",  # <-- Sorgente (default: FILE_ORDINI)
        "cartella_destinazione": "",  # <-- Destinazione base
        "copia_file_ordini": True,
        "apri_cartella_dopo_salvataggio": False
    }
}


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config = self._carica_config()

    def _carica_config(self) -> Dict[str, Any]:
        """Carica la configurazione dal file JSON."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Assicura che tutti i campi default esistano
                    return self._merge_with_default(config)
            except Exception as e:
                print(f"Errore nel caricamento del config: {e}")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def _merge_with_default(self, config: Dict) -> Dict:
        """Unisce la configurazione caricata con i valori di default."""
        merged = DEFAULT_CONFIG.copy()

        # Ricorsivamente unisce i dizionari
        def merge_dict(default, custom):
            for key, value in custom.items():
                if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                    merge_dict(default[key], value)
                else:
                    default[key] = value
            return default

        return merge_dict(merged, config)

    def salva_config(self):
        """Salva la configurazione su file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Errore nel salvataggio del config: {e}")

    def get(self, *keys, default=None):
        """Ottiene un valore dal config usando chiavi annidate."""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, *args):
        """Imposta un valore nel config."""
        if len(args) < 2:
            return

        value = args[-1]
        keys = args[:-1]

        current = self.config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
        self.salva_config()


# Istanza singleton
config = Config()