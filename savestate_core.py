import os
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

class GameProfile:
    """Representa um perfil de jogo para backup"""
    
    def __init__(self, name: str, game_name: str, appid: str, save_paths: List[str]):
        self.name = name
        self.game_name = game_name
        self.appid = appid
        self.save_paths = save_paths
        self.created_at = time.time()
        self.last_backup = None

class SaveStateManager:
    """Gerenciador principal do SaveState simplificado"""
    
    def __init__(self, backup_root: Path = None):
        self.backup_root = backup_root or Path("log/savestate_backups")
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.config_file = self.backup_root.parent / "savestate_config.json"
        self.profiles: Dict[str, GameProfile] = {}
        self.load_profiles()
    
    def load_profiles(self):
        """Carrega perfis do arquivo de configuração"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for profile_id, profile_data in data.items():
                        profile = GameProfile(
                            name=profile_data['name'],
                            game_name=profile_data['game_name'],
                            appid=profile_data['appid'],
                            save_paths=profile_data['save_paths']
                        )
                        profile.created_at = profile_data.get('created_at', time.time())
                        profile.last_backup = profile_data.get('last_backup')
                        self.profiles[profile_id] = profile
        except Exception as e:
            print(f"Erro ao carregar perfis: {e}")
    
    def save_profiles(self):
        """Salva perfis no arquivo de configuração"""
        try:
            data = {}
            for profile_id, profile in self.profiles.items():
                data[profile_id] = {
                    'name': profile.name,
                    'game_name': profile.game_name,
                    'appid': profile.appid,
                    'save_paths': profile.save_paths,
                    'created_at': profile.created_at,
                    'last_backup': profile.last_backup
                }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar perfis: {e}")