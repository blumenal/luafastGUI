# config_manager.py
import json
from pathlib import Path

CONFIG_FILE = Path("log") / "steam_config.json"
DEFAULT_STEAM_PATH = Path("C:/Program Files (x86)/Steam")

def get_steam_path():
    """Retorna o caminho configurado da Steam ou o padrão se não existir configuração"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return Path(config.get("steam_path", DEFAULT_STEAM_PATH))
        return DEFAULT_STEAM_PATH
    except Exception:
        return DEFAULT_STEAM_PATH

def set_steam_path(new_path):
    """Define um novo caminho para a Steam"""
    try:
        CONFIG_FILE.parent.mkdir(exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"steam_path": str(new_path)}, f)
        return True
    except Exception:
        return False

def get_steam_subpath(subpath):
    """Retorna o caminho completo combinando o caminho da Steam com um subpath"""
    steam_path = get_steam_path()
    return steam_path / subpath