
import subprocess
import signal
import customtkinter
import threading
import sys
import os
import asyncio
import queue
import time
import requests
from PIL import Image, ImageTk
import io
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from install import pesquisar_jogo_por_nome, verificar_drm, formatar_data_brasil
from config_manager import get_steam_path, set_steam_path

from install import (
    baixar_do_bruhhub,
    desbloquear_jogo,
    formatar_data_brasil,
    apply_versionlock_decision,
    atualizar_do_bruhhub
)
from fecharsteam import encerrar_steam_processos, reiniciar_steam as reiniciar_steam_fechar
import ctypes
from ctypes import wintypes, create_unicode_buffer
from pathlib import Path
from remove import extrair_appids_do_lua, remover_manifests_por_ids, remover_manifests_agressivo
import shutil
import re
import httplib2
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_httplib2 import AuthorizedHttp


# ================= CONFIGURAÇÕES SAVELUA =================
SAVELUA_BACKUP_DIR = Path("log/savelua_backups")
SAVELUA_CONFIG_FILE = Path("log/savelua_config.json")

# Adicione esta constante para Windows
if os.name == 'nt':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0
    
# ================= FUNÇÕES AUXILIARES PARA SAVELUA =================

def parse_libraryfolders_vdf(steam_path):
    """Faz parsing correto do libraryfolders.vdf baseado no SaveState original"""
    libraryfolders_path = steam_path / "steamapps" / "libraryfolders.vdf"
    libraries = [steam_path / "steamapps"]
    
    if not libraryfolders_path.exists():
        return libraries
        
    try:
        with open(libraryfolders_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Método do SaveState original para extrair paths
        path_matches = re.findall(r'"path"\s+"([^"]+)"', content)
        
        for path in path_matches:
            try:
                # Converte para Path e normaliza
                library_path = Path(path.replace('\\\\', '\\'))
                library_apps = library_path / "steamapps"
                if library_apps.exists():
                    libraries.append(library_apps)
            except Exception as e:
                print(f"Erro ao processar biblioteca {path}: {e}")
                continue
                
    except Exception as e:
        print(f"Erro ao ler libraryfolders.vdf: {e}")
    
    return libraries
    
# ================= FUNÇÕES ADICIONADAS PARA DOWNLOAD =================
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def download_hid_rar():
    """Faz o download do hid.rar usando a API do Google Drive"""
    try:
        steam_path = get_steam_path()
        steamall_path = steam_path / "SteamAll"
        os.makedirs(steamall_path, exist_ok=True)
        rar_path = steamall_path / "hid.rar"
        
        # Se o arquivo já existe, não baixa novamente
        if rar_path.exists() and rar_path.stat().st_size > 0:
            return True, "Arquivo já existe"
        
        # Cria o serviço do Google Drive
        creds = service_account.Credentials.from_service_account_info(
            SERVICE_ACCOUNT_INFO, scopes=SCOPES
        )
        http = httplib2.Http(timeout=300)
        authed_http = AuthorizedHttp(creds, http=http)
        service = build('drive', 'v3', http=authed_http)

        # Busca o arquivo no Google Drive
        results = service.files().list(
            q="name='hid.rar'",
            pageSize=1,
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        if not items:
            return False, "Arquivo hid.rar não encontrado no Google Drive"
        
        file_id = items[0]['id']
        request = service.files().get_media(fileId=file_id)

        # Faz o download
        with open(rar_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        return True, "Download completo"
    except Exception as e:
        return False, f"Erro no download: {str(e)}"

# ================= VERIFICAÇÃO DE ACORDO =================
CAMINHO_LOG_ACORDO = os.path.join("log", "acordo.json")

def verificar_acordo_aceito():
    """Verifica se o acordo já foi aceito"""
    try:
        if os.path.exists(CAMINHO_LOG_ACORDO):
            with open(CAMINHO_LOG_ACORDO, "r", encoding='utf-8') as f:
                dados = json.load(f)
                return dados.get("acordo_aceito")
        return None
    except:
        return None

def salvar_acordo(aceito: bool):
    """Salva o acordo do usuário"""
    try:
        os.makedirs(os.path.dirname(CAMINHO_LOG_ACORDO), exist_ok=True)
        with open(CAMINHO_LOG_ACORDO, "w", encoding='utf-8') as f:
            json.dump({"acordo_aceito": aceito}, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar acordo: {str(e)}")

def exibir_tela_acordo():
    """Exibe a tela de termos de uso e retorna True se aceito"""
    root = customtkinter.CTk()
    root.title("Termos de Licença e Utilização")
    root.geometry("900x600")
    root.resizable(False, False)
    
    # Variável para armazenar o resultado
    resultado = [None]
    
    # Frame principal
    frame = customtkinter.CTkFrame(root)
    frame.pack(expand=True, fill="both", padx=20, pady=20)
    
    # Título
    label_titulo = customtkinter.CTkLabel(
        frame,
        text="Termos de Licença e Utilização",
        font=customtkinter.CTkFont(size=20, weight="bold")
    )
    label_titulo.pack(pady=10)
    
    # Texto dos termos (mesmo conteúdo do main.py)
    texto_termos = (
        "Este projeto é distribuído sob a licença GPL-3.0. As diretrizes a seguir são complementares à licença GPL-3.0; "
        "em caso de conflito, prevalecem sobre a mesma.\n\n"
        "Durante o uso deste programa, podem ser gerados dados protegidos por direitos autorais. "
        "O usuário deverá excluir quaisquer dados protegidos no prazo máximo de 24 horas.\n\n"
        "Este projeto é completamente gratuito, mas você pode contribuir fazendo uma doação caso queira ajudar o projeto.\n\n"
        "É proibido utilizar este projeto para fins comerciais.\n"
        "Modificações no projeto só serão permitidas mediante a publicação conjunta do código-fonte correspondente e menções aos criadores.\n\n"
        "Ao utilizar este programa, você declara estar de acordo com todos os termos acima."
    )
    
    textbox = customtkinter.CTkTextbox(
        frame,
        width=800,
        height=400,
        wrap="word",
        font=customtkinter.CTkFont(size=14)
    )
    textbox.pack(pady=10, padx=10, fill="both", expand=True)
    textbox.insert("1.0", texto_termos)
    textbox.configure(state="disabled")  # Somente leitura
    
    def set_resposta(aceito):
        resultado[0] = aceito
        # Destruir a janela após um pequeno atraso
        root.after(300, root.destroy)
    
    # Frame dos botões
    frame_botoes = customtkinter.CTkFrame(frame, fg_color="transparent")
    frame_botoes.pack(pady=10)
    
    btn_aceitar = customtkinter.CTkButton(
        frame_botoes,
        text="Aceitar",
        command=lambda: set_resposta(True),
        width=100,
        fg_color="green"
    )
    btn_aceitar.grid(row=0, column=0, padx=20)
    
    btn_rejeitar = customtkinter.CTkButton(
        frame_botoes,
        text="Rejeitar",
        command=lambda: set_resposta(False),
        width=100,
        fg_color="red"
    )
    btn_rejeitar.grid(row=0, column=1, padx=20)
    
    # Centralizar os botões
    frame_botoes.grid_columnconfigure(0, weight=1)
    frame_botoes.grid_columnconfigure(1, weight=1)
    
    # Forçar o foco na janela
    root.focus_force()
    root.grab_set()
    
    # Trata o fechamento da janela pelo sistema (clicar no X)
    root.protocol("WM_DELETE_WINDOW", lambda: set_resposta(False))
    
    root.mainloop()
    return resultado[0]

# ================= CONFIGURAÇÕES =================
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")  # Tema de cores fixo

# Versão do aplicativo
VERSAO_APP = "5.1.0"
DEV_INFO = "@blumenal86"
STEAMDB_URL = "https://steamdb.info/"

# Nome do arquivo de configuração
CONFIG_DIR = "log"
CONFIG_FILE = os.path.join(CONFIG_DIR, "visual_config.json")

# Caminho para backup
BACKUP_ROOT = Path("log/backup")

class ProgressManager:
    """Gerencia a exibição de barras de progresso em uma única linha"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.progress_tag = "progress_line"
        self.last_progress = ""
        self.progress_index = None  # Armazena a posição da barra de progresso
        
    def update_progress(self, text):
        """Atualiza a linha de progresso, substituindo a anterior"""
        # Se é uma nova linha de progresso
        if text.strip().startswith('[') and text.strip().endswith('%'):
            # Remove quebra de linha extra
            text = text.rstrip('\n')
            # Se já existe uma barra de progresso, substitui
            if self.progress_index:
                self.text_widget.delete(self.progress_index, "end-1c")
            
            # Insere a nova barra de progresso
            self.text_widget.insert(customtkinter.END, text, self.progress_tag)
            self.last_progress = text
            
            # Marca o início da linha de progresso
            self.progress_index = f"end-1c linestart"
            
            # Retorna True para indicar que foi uma atualização de progresso
            return True
        return False

class ThreadSafeText:
    """Classe para redirecionamento thread-safe de saída para um widget de texto"""
    def __init__(self, text_widget, tag=None):
        self.text_widget = text_widget
        self.tag = tag
        self.queue = queue.Queue()
        self.running = True
        self.progress_manager = ProgressManager(text_widget)
        # Adicionar regex para remover códigos ANSI
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
    def write(self, text):
        # Remove códigos ANSI antes de adicionar à fila
        text = self.ansi_escape.sub('', text)
        # Remove quebras de linha extras das barras de progresso
        if text.strip().startswith('[') and text.strip().endswith('%'):
            text = text.rstrip('\n')
        self.queue.put(text)
        
    def flush(self):
        pass
        
    def start(self):
        def update():
            while self.running:
                try:
                    # Coleta todo o texto disponível na fila
                    accumulated = ""
                    while True:
                        try:
                            text = self.queue.get_nowait()
                            # Tenta atualizar como progresso
                            if not self.progress_manager.update_progress(text):
                                accumulated += text
                        except queue.Empty:
                            break
                    
                    # Atualiza o widget se houver novo texto
                    if accumulated:
                        self.text_widget.insert(customtkinter.END, accumulated, self.tag)
                        self.force_scroll()
                
                except Exception as e:
                    print(f"Erro na atualização de texto: {e}")
                
                time.sleep(0.1)  # Intervalo entre verificações
            
        threading.Thread(target=update, daemon=True).start()
        
    def force_scroll(self):
        """Força a rolagem para o final do texto"""
        self.text_widget.see(customtkinter.END)
        # Atualização extra para garantir a rolagem
        self.text_widget.update_idletasks()
        
    def stop(self):
        self.running = False

# ================= CLASSE SaveLua SIMPLIFICADA =================
class SimpleSaveLuaManager:
    """Versão melhorada do SaveLua integrado ao LuaFast"""
    
    def __init__(self, master):
        self.master = master
        self.backup_dir = SAVELUA_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = SAVELUA_CONFIG_FILE
        self.profiles = self.load_profiles()
        
    def get_steam_libraries(self):
        """Obtém todas as bibliotecas Steam (incluindo bibliotecas adicionais)"""
        return parse_libraryfolders_vdf(get_steam_path())
    
    def load_profiles(self):
        """Carrega os perfis salvos"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_profiles(self):
        """Salva os perfis - VERSÃO COM DEBUG"""
        try:
            # Garantir que o diretório existe
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=4, ensure_ascii=False)
            
            print(f"DEBUG save_profiles: Perfis salvos em {self.config_file}")
            print(f"DEBUG save_profiles: {len(self.profiles)} perfis salvos")
            
        except Exception as e:
            print(f"DEBUG save_profiles: ERRO ao salvar perfis: {e}")
    
    def get_installed_steam_games(self):
        """Obtém lista de jogos Steam instalados em TODAS as bibliotecas - VERSÃO MELHORADA"""
        games = []
        libraries = self.get_steam_libraries()
        
        for library in libraries:
            try:
                # Busca por arquivos .acf em todas as bibliotecas
                for acf_file in library.glob("appmanifest_*.acf"):
                    try:
                        game_data = self.parse_acf_file(acf_file, library)
                        if game_data and not any(g['appid'] == game_data['appid'] for g in games):
                            games.append(game_data)
                            
                    except Exception as e:
                        print(f"Erro ao processar {acf_file}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Erro ao acessar biblioteca {library}: {e}")
                continue
                    
        return sorted(games, key=lambda x: x['name'].lower())
        
    def debug_save_profiles(self):
        """Debug: verifica se o arquivo está sendo salvo"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"DEBUG - Arquivo de perfis existe, tamanho: {len(content)} bytes")
                return True
            else:
                print("DEBUG - Arquivo de perfis NÃO existe")
                return False
        except Exception as e:
            print(f"DEBUG - Erro ao verificar arquivo: {e}")
            return False
        
    def parse_acf_file(self, acf_file, library):
        """Faz parsing correto do arquivo .acf"""
        try:
            with open(acf_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extrai informações usando regex mais robustos
            name_match = re.search(r'"name"\s+"([^"]+)"', content)
            appid_match = re.search(r'"appid"\s+"(\d+)"', content)
            installdir_match = re.search(r'"installdir"\s+"([^"]+)"', content)
            
            if name_match and appid_match and installdir_match:
                return {
                    'name': name_match.group(1),
                    'appid': appid_match.group(1),
                    'install_dir': installdir_match.group(1),
                    'path': library / "common" / installdir_match.group(1),
                    'acf_file': acf_file
                }
        except Exception as e:
            print(f"Erro no parsing de {acf_file}: {e}")
        
        return None

    def find_save_paths(self, game_info):
        """Busca de saves melhorada baseada no SaveState"""
        save_paths = []
        game_path = game_info['path']
        
        # Diretórios comuns de save do SaveState
        common_save_dirs = [
            "saves", "save", "savegames", "savegame",
            "Save", "Saves", "SaveGames", "SaveGame",
            "data", "Data", "profile", "Profile",
            "profiles", "game", "games", "user", "users",
            "backup", "backups", "storage", "states"
        ]
        
        # 1. Busca em diretórios comuns dentro da pasta do jogo
        for save_dir in common_save_dirs:
            save_path = game_path / save_dir
            if save_path.exists() and save_path.is_dir():
                save_paths.append(str(save_path))
        
        # 2. Busca recursiva por diretórios que contenham "save"
        try:
            for item in game_path.rglob('*'):
                if item.is_dir() and any(keyword in item.name.lower() for keyword in 
                                       ['save', 'backup', 'profile', 'data', 'game']):
                    save_paths.append(str(item))
        except Exception as e:
            print(f"Erro na busca recursiva: {e}")
        
        # 3. Busca em AppData (Windows) - Método do SaveState
        if os.name == 'nt':
            appdata_paths = [
                os.environ.get('APPDATA', ''),
                os.environ.get('LOCALAPPDATA', ''),
                os.path.expanduser('~/Documents/My Games'),
                os.path.expanduser('~/Saved Games')
            ]
            
            for appdata_path in appdata_paths:
                if appdata_path and os.path.exists(appdata_path):
                    appdata_dir = Path(appdata_path)
                    
                    # Busca por pastas com nome do jogo, desenvolvedor ou publisher
                    search_terms = [
                        game_info['name'].lower(),
                        game_info.get('install_dir', '').lower(),
                        self.extract_developer_name(game_info)
                    ]
                    
                    for search_term in search_terms:
                        if search_term:
                            for item in appdata_dir.iterdir():
                                if item.is_dir() and search_term in item.name.lower():
                                    save_paths.append(str(item))
        
        # Remove duplicatas e paths inválidos
        unique_paths = []
        for path in save_paths:
            if (os.path.exists(path) and path not in unique_paths and 
                any(os.listdir(path)) if os.path.isdir(path) else True):
                unique_paths.append(path)
        
        return unique_paths

    def extract_developer_name(self, game_info):
        """Tenta extrair nome do desenvolvedor para busca melhorada"""
        try:
            # Tenta obter informações adicionais da Steam
            import requests
            url = f"https://store.steampowered.com/api/appdetails?appids={game_info['appid']}"
            response = requests.get(url)
            data = response.json()
            
            if data and str(game_info['appid']) in data:
                game_data = data[str(game_info['appid'])].get('data', {})
                developers = game_data.get('developers', [])
                if developers:
                    return developers[0].lower()
        except:
            pass
        
        return ""

    def add_profile(self, game_info, save_paths, profile_name=None):
        """Adiciona um perfil de backup - VERSÃO COM DEBUG"""
        if not profile_name:
            profile_name = game_info['name']
            
        profile_id = f"{game_info['appid']}_{int(time.time())}"  # ID único
        
        self.profiles[profile_id] = {
            'name': profile_name,
            'game_name': game_info['name'],
            'appid': game_info['appid'],
            'install_dir': game_info.get('install_dir', game_info['name'].replace(' ', '')),
            'save_paths': save_paths,
            'created_at': time.time(),
            'last_backup': None
        }
        
        # DEBUG: Verificar antes de salvar
        print(f"DEBUG add_profile: Adicionando perfil {profile_id}")
        print(f"DEBUG add_profile: Total de perfis antes do save: {len(self.profiles)}")
        
        self.save_profiles()
        
        # DEBUG: Verificar após salvar
        print(f"DEBUG add_profile: Total de perfis após save: {len(self.profiles)}")
        print(f"DEBUG add_profile: Perfil salvo com sucesso")
        
        return profile_id
        
        
        # ================= FUNÇÕES DE BACKUP E REMOÇÃO =================
    def create_backup(self, profile_id):
        """Cria um backup dos arquivos de save do perfil"""
        try:
            profile = self.profiles.get(profile_id)
            if not profile:
                return False, "Perfil não encontrado."

            backup_path = self.backup_dir / profile["game_name"]
            os.makedirs(backup_path, exist_ok=True)

            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            backup_subdir = backup_path / f"backup_{timestamp}"
            os.makedirs(backup_subdir, exist_ok=True)

            for save_path in profile["save_paths"]:
                if os.path.exists(save_path):
                    dest = backup_subdir / os.path.basename(save_path)
                    if os.path.isdir(save_path):
                        shutil.copytree(save_path, dest)
                    else:
                        shutil.copy2(save_path, dest)

            profile["last_backup"] = time.time()
            self.save_profiles()

            return True, f"Backup criado em: {backup_subdir}"

        except Exception as e:
            return False, f"Erro ao criar backup: {str(e)}"

    def get_backups(self, profile_id):
        """Lista todos os backups disponíveis para o perfil"""
        profile = self.profiles.get(profile_id)
        if not profile:
            return []

        backup_path = self.backup_dir / profile["game_name"]
        if not backup_path.exists():
            return []

        backups = [d.name for d in backup_path.iterdir() if d.is_dir()]
        backups.sort(reverse=True)
        return backups

    def restore_backup(self, profile_id, backup_name):
        """Restaura um backup para o local original"""
        try:
            profile = self.profiles.get(profile_id)
            if not profile:
                return False, "Perfil não encontrado."

            backup_folder = self.backup_dir / profile["game_name"] / backup_name
            if not backup_folder.exists():
                return False, "Backup não encontrado."

            for item in backup_folder.iterdir():
                for save_path in profile["save_paths"]:
                    if os.path.exists(save_path):
                        dest = Path(save_path) / item.name
                        if item.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)

            return True, f"Backup '{backup_name}' restaurado com sucesso!"

        except Exception as e:
            return False, f"Erro ao restaurar backup: {str(e)}"

    def delete_backup(self, profile_id, backup_name):
        """Exclui um backup específico"""
        try:
            profile = self.profiles.get(profile_id)
            if not profile:
                return False

            backup_folder = self.backup_dir / profile["game_name"] / backup_name
            if backup_folder.exists():
                shutil.rmtree(backup_folder)
                return True
            return False
        except Exception as e:
            print(f"Erro ao excluir backup: {e}")
            return False

    def remove_profile(self, profile_id):
        """Remove o perfil e seus backups"""
        try:
            profile = self.profiles.get(profile_id)
            if not profile:
                return False, "Perfil não encontrado."

            # Exclui backups
            backup_folder = self.backup_dir / profile["game_name"]
            if backup_folder.exists():
                shutil.rmtree(backup_folder)

            # Remove perfil do arquivo
            del self.profiles[profile_id]
            self.save_profiles()
            return True, f"Perfil '{profile['name']}' removido com sucesso."
        except Exception as e:
            return False, f"Erro ao remover perfil: {str(e)}"


class SaveLuaWindow(customtkinter.CTkToplevel):  # ← MUDAR NOME
    def configure_profile_with_confirmation(self):
        """Configura perfil com confirmação de save paths (como no SaveState)"""
        if not self.selected_game:
            messagebox.showwarning("Aviso", "Selecione um jogo primeiro!")
            return
        
        # Encontrar caminhos de save
        save_paths = self.save_lua_manager.find_save_paths(self.selected_game)
        
        if not save_paths:
            messagebox.showinfo("Info", f"Nenhum caminho de save encontrado para {self.selected_game['name']}")
            return
        
        # Mostrar janela de confirmação como no SaveState
        confirmation_window = customtkinter.CTkToplevel(self)
        confirmation_window.title("Confirmar Save Paths")
        confirmation_window.geometry("600x400")
        confirmation_window.resizable(True, True)
        confirmation_window.transient(self)
        confirmation_window.grab_set()
        
        confirmation_window.grid_rowconfigure(1, weight=1)
        confirmation_window.grid_columnconfigure(0, weight=1)
        
        # Título
        title_label = customtkinter.CTkLabel(
            confirmation_window,
            text=f"Save Paths Encontrados para {self.selected_game['name']}",
            font=customtkinter.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        # Lista de save paths com checkboxes
        scroll_frame = customtkinter.CTkScrollableFrame(confirmation_window)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        selected_paths = []
        check_vars = []
        check_widgets = []
        
        for idx, path in enumerate(save_paths):
            var = tk.BooleanVar(value=True)  # Selecionado por padrão
            check_vars.append(var)
            
            chk = customtkinter.CTkCheckBox(
                scroll_frame,
                text=path,
                variable=var,
                command=lambda p=path, v=var: self.toggle_save_path(p, v, selected_paths)
            )
            chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            selected_paths.append(path)
            check_widgets.append(chk)
        
        # Botão para adicionar caminho manualmente
        def add_manual_path():
            manual_path = filedialog.askdirectory(title="Selecionar pasta de save manualmente")
            if manual_path and manual_path not in selected_paths:
                var = tk.BooleanVar(value=True)
                check_vars.append(var)
                
                chk = customtkinter.CTkCheckBox(
                    scroll_frame,
                    text=manual_path,
                    variable=var,
                    command=lambda p=manual_path, v=var: self.toggle_save_path(p, v, selected_paths)
                )
                current_row = len(selected_paths)
                chk.grid(row=current_row, column=0, sticky="w", padx=5, pady=2)
                selected_paths.append(manual_path)
                check_widgets.append(chk)
        
        # Frame de botões
        button_frame = customtkinter.CTkFrame(confirmation_window)
        button_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)  # ADICIONAR ESTA LINHA
        
        add_manual_btn = customtkinter.CTkButton(
            button_frame,
            text="Adicionar Caminho Manual",
            command=add_manual_path,
            width=150
        )
        add_manual_btn.grid(row=0, column=0, padx=10, pady=5)
        
        # === BOTÃO CONFIRMAR ADICIONADO AQUI ===
        def confirm_selection():
            # Filtra apenas os paths selecionados
            final_paths = []
            for path, var in zip(selected_paths, check_vars):
                if var.get():
                    final_paths.append(path)
            
            if not final_paths:
                messagebox.showwarning("Aviso", "Selecione pelo menos um caminho de save!")
                return
            
            # Cria o perfil
            try:
                profile_id = self.save_lua_manager.add_profile(self.selected_game, final_paths)
                
                messagebox.showinfo("Sucesso", 
                                  f"Perfil criado para {self.selected_game['name']}!\n"
                                  f"Caminhos de save configurados: {len(final_paths)}")
                
                confirmation_window.destroy()
                
                # ATUALIZAR A LISTA DE PERFIS
                print("DEBUG: Recarregando lista de perfis após criação...")
                self.force_refresh_profiles()

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar perfil: {str(e)}")
                print(f"DEBUG - Erro ao criar perfil: {e}")
        
        confirm_btn = customtkinter.CTkButton(
            button_frame,
            text="Confirmar",
            command=confirm_selection,
            width=150,
            fg_color="green"
        )
        confirm_btn.grid(row=0, column=1, padx=10, pady=5)
        
        # Botão Cancelar
        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Cancelar",
            command=confirmation_window.destroy,
            width=150,
            fg_color="red"
        )
        cancel_btn.grid(row=0, column=2, padx=10, pady=5)
        
    def force_refresh_profiles(self):
        """Força atualização completa da lista de perfis"""
        print("DEBUG: Forçando refresh dos perfis...")
        
        # Recarregar perfis do arquivo para garantir que está sincronizado
        self.save_lua_manager.profiles = self.save_lua_manager.load_profiles()
        
        # Recarregar interface
        self.load_profiles()
        
        # Forçar redesenho
        self.update_idletasks()
    
    def confirm_selection():
        # Filtra apenas os paths selecionados
        final_paths = []
        for path, var in zip(selected_paths, check_vars):
            if var.get():
                final_paths.append(path)
        
        if not final_paths:
            messagebox.showwarning("Aviso", "Selecione pelo menos um caminho de save!")
            return
        
        # Cria o perfil
        try:
            profile_id = self.save_lua_manager.add_profile(self.selected_game, final_paths)
            
            messagebox.showinfo("Sucesso", 
                              f"Perfil criado para {self.selected_game['name']}!\n"
                              f"Caminhos de save configurados: {len(final_paths)}")
            
            confirmation_window.destroy()
            
            # ATUALIZAR A LISTA DE PERFIS - CORREÇÃO CRÍTICA
            print("DEBUG: Recarregando lista de perfis após criação...")
            self.force_refresh_profiles()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar perfil: {str(e)}")
            print(f"DEBUG - Erro ao criar perfil: {e}")


    def toggle_save_path(self, path, var, selected_paths):
        """Controla a seleção/deseleção de save paths"""
        if not var.get() and path in selected_paths:
            selected_paths.remove(path)
        elif var.get() and path not in selected_paths:
            selected_paths.append(path)
        
    def __init__(self, master):
        super().__init__(master)
        self.title("Gerenciador de Saves")  # ← MUDAR TÍTULO
        self.geometry("500x800")
        self.resizable(True, True)
        
        self.save_lua_manager = SimpleSaveLuaManager(self)  # ← MUDAR NOME
        
        # Configurar grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Frame de controle
        control_frame = customtkinter.CTkFrame(self)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        control_frame.grid_columnconfigure(1, weight=1)
        
        # Botão Refresh
        self.refresh_btn = customtkinter.CTkButton(
            control_frame,
            text="Atualizar Lista",
            command=self.refresh_games,
            width=100
        )
        self.refresh_btn.grid(row=0, column=0, padx=5, pady=5)
        
        # No frame de controle, após os outros botões:
        self.remove_profile_btn = customtkinter.CTkButton(
            control_frame,
            text="Remover Perfil Selecionado",
            command=self.remove_selected_profile,
            width=180,
            fg_color="red",
            hover_color="darkred"
        )
        self.remove_profile_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # Botão Configure Selected Profile
        self.configure_btn = customtkinter.CTkButton(
            control_frame,
            text="Criar Perfil",
            command=self.configure_profile,
            width=150
        )
        self.configure_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Botão Manage Backups
        #self.manage_backups_btn = customtkinter.CTkButton(
        #    control_frame,
        #    text="Manage Backups",
        #    command=self.manage_backups,
        #    width=120
        #)
        #self.manage_backups_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Frame principal
        main_frame = customtkinter.CTkFrame(self)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Lista de jogos
        self.games_list = customtkinter.CTkScrollableFrame(main_frame)
        self.games_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.games_list.grid_columnconfigure(0, weight=1)
        
        # Frame de perfis
        profiles_frame = customtkinter.CTkFrame(self)
        profiles_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        profiles_frame.grid_columnconfigure(0, weight=1)
        
        self.profiles_label = customtkinter.CTkLabel(
            profiles_frame,
            text="Perfis Configurados:",
            font=customtkinter.CTkFont(weight="bold")
        )
        self.profiles_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.profiles_list = customtkinter.CTkScrollableFrame(profiles_frame, height=100)
        self.profiles_list.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.profiles_list.grid_columnconfigure(0, weight=1)
        
        # Frame de ações
        actions_frame = customtkinter.CTkFrame(self)
        actions_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        actions_frame.grid_columnconfigure(0, weight=1)
        actions_frame.grid_columnconfigure(1, weight=1)
        actions_frame.grid_columnconfigure(2, weight=1)
        
        self.backup_btn = customtkinter.CTkButton(
            actions_frame,
            text="Backup",
            command=self.do_backup,
            fg_color="green"
        )
        self.backup_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.restore_btn = customtkinter.CTkButton(
            actions_frame,
            text="Restore",
            command=self.do_restore,
            fg_color="blue"
        )
        self.restore_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.open_folder_btn = customtkinter.CTkButton(
            actions_frame,
            text="Open Backup Folder",
            command=self.open_backup_folder
        )
        self.open_folder_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Variáveis de estado
        self.selected_game = None
        self.selected_profile = None
        self.games = []
        self.game_widgets = {}
        self.profile_widgets = {}
        
        # Carregar dados iniciais
        self.refresh_games()
        self.load_profiles()
        # Garante que a janela fique no topo
        self.transient(master)
        self.grab_set()
        self.focus_force()
    
    def refresh_games(self):
        """Atualiza a lista de jogos"""
        # Limpar lista anterior
        for widget in self.games_list.winfo_children():
            widget.destroy()
        
        self.game_widgets = {}
        self.games = self.save_lua_manager.get_installed_steam_games()  # ← CORRIGIR AQUI
        
        if not self.games:
            no_games_label = customtkinter.CTkLabel(
                self.games_list,
                text="Nenhum jogo Steam instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        # Adicionar jogos à lista
        for idx, game in enumerate(self.games):
            btn = customtkinter.CTkButton(
                self.games_list,
                text=f"{game['name']} (ID: {game['appid']})",
                command=lambda g=game: self.select_game(g),
                anchor="w",
                height=30
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=2)
            self.game_widgets[game['appid']] = btn
    
    def select_game(self, game):
        """Seleciona um jogo da lista"""
        # Desselecionar jogo anterior
        if self.selected_game and self.selected_game['appid'] in self.game_widgets:
            self.game_widgets[self.selected_game['appid']].configure(fg_color=["#3B8ED0", "#1F6AA5"])
        
        # Selecionar novo jogo
        self.selected_game = game
        self.game_widgets[game['appid']].configure(fg_color="green")
    
    def configure_profile(self):
        """Configura um perfil para o jogo selecionado (com confirmação)"""
        if not self.selected_game:
            messagebox.showwarning("Aviso", "Selecione um jogo primeiro!")
            return
        
        print(f"DEBUG: Configurando perfil para {self.selected_game['name']}")  # ← DEBUG
        self.configure_profile_with_confirmation()
    
    def load_profiles(self):
        """Carrega a lista de perfis - VERSÃO COMPLETAMENTE CORRIGIDA"""
        # Limpar lista anterior COMPLETAMENTE
        for widget in self.profiles_list.winfo_children():
            try:
                widget.destroy()
            except:
                pass
        
        self.profile_widgets = {}
        self.selected_profile = None  # Resetar seleção
        
        # DEBUG: Verificar quantos perfis existem
        print(f"DEBUG load_profiles: {len(self.save_lua_manager.profiles)} perfis no manager")
        
        if not self.save_lua_manager.profiles:
            no_profiles_label = customtkinter.CTkLabel(
                self.profiles_list,
                text="Nenhum perfil configurado",
                font=customtkinter.CTkFont(size=12)
            )
            no_profiles_label.grid(row=0, column=0, padx=10, pady=10)
            print("DEBUG: Nenhum perfil para mostrar")
            return
        
        # Adicionar perfis à lista
        for idx, (profile_id, profile) in enumerate(self.save_lua_manager.profiles.items()):
            print(f"DEBUG: Adicionando perfil {idx}: {profile['name']} ({profile['game_name']})")
            
            btn = customtkinter.CTkButton(
                self.profiles_list,
                text=f"{profile['name']} ({profile['game_name']})",
                command=lambda pid=profile_id: self.select_profile(pid),
                anchor="w",
                height=25,
                fg_color=["#3B8ED0", "#1F6AA5"]
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=1)
            self.profile_widgets[profile_id] = btn
        
        # Forçar atualização visual
        self.profiles_list.update_idletasks()
        print("DEBUG: Lista de perfis atualizada")
        
    def debug_profiles(self):
        """Método de debug para verificar perfis"""
        print("=== DEBUG PERFIS ===")
        print(f"Total de perfis: {len(self.save_lua_manager.profiles)}")
        for profile_id, profile in self.save_lua_manager.profiles.items():
            print(f"  - {profile_id}: {profile['name']} ({profile['game_name']})")
        print("====================")
    
    def select_profile(self, profile_id):
        """Seleciona um perfil"""
        # Desselecionar perfil anterior
        if self.selected_profile and self.selected_profile in self.profile_widgets:
            self.profile_widgets[self.selected_profile].configure(fg_color=["#3B8ED0", "#1F6AA5"])
        
        # Selecionar novo perfil
        self.selected_profile = profile_id
        self.profile_widgets[profile_id].configure(fg_color="green")
    
    def do_backup(self):
        """Executa backup do perfil selecionado"""
        if not self.selected_profile:
            messagebox.showwarning("Aviso", "Selecione um perfil primeiro!")
            return
        
        success, message = self.save_lua_manager.create_backup(self.selected_profile)  # ← CORRIGIR
        
        if success:
            messagebox.showinfo("Sucesso", message)
        else:
            messagebox.showerror("Erro", message)
    
    def do_restore(self):
        """Executa restauração do perfil selecionado"""
        if not self.selected_profile:
            messagebox.showwarning("Aviso", "Selecione um perfil primeiro!")
            return
        
        backups = self.save_lua_manager.get_backups(self.selected_profile)  # ← CORRIGIR
        
        if not backups:
            messagebox.showinfo("Info", "Nenhum backup encontrado para este perfil")
            return
        
        # Criar janela de seleção de backup
        backup_window = customtkinter.CTkToplevel(self)
        backup_window.title("Selecionar Backup")
        backup_window.geometry("400x300")
        backup_window.transient(self)
        backup_window.grab_set()
        
        backup_window.grid_rowconfigure(0, weight=1)
        backup_window.grid_columnconfigure(0, weight=1)
        
        # Lista de backups
        backup_list = customtkinter.CTkScrollableFrame(backup_window)
        backup_list.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        backup_list.grid_columnconfigure(0, weight=1)
        
        selected_backup = [None]
        
        for idx, backup_name in enumerate(backups):
            btn = customtkinter.CTkButton(
                backup_list,
                text=backup_name,
                command=lambda bn=backup_name: selected_backup.__setitem__(0, bn),
                anchor="w",
                height=30
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=2)
        
        # Botão de restaurar
        def restore_selected():
            if selected_backup[0]:
                success, message = self.save_lua_manager.restore_backup(self.selected_profile, selected_backup[0])
                if success:
                    messagebox.showinfo("Sucesso", message)
                else:
                    messagebox.showerror("Erro", message)
                backup_window.destroy()
            else:
                messagebox.showwarning("Aviso", "Selecione um backup!")
        
        restore_btn = customtkinter.CTkButton(
            backup_window,
            text="Restaurar",
            command=restore_selected,
            fg_color="blue"
        )
        restore_btn.grid(row=1, column=0, padx=10, pady=10)
    
    def manage_backups(self):
        """Gerencia backups (lista e exclui)"""
        if not self.selected_profile:
            messagebox.showwarning("Aviso", "Selecione um perfil primeiro!")
            return
        
        backups = self.save_lua_manager.get_backups(self.selected_profile)  # ← CORRIGIR
        
        manage_window = customtkinter.CTkToplevel(self)
        manage_window.title("Gerenciar Backups")
        manage_window.update_idletasks()  # força o layout a carregar
        manage_window.geometry("400x550")  # aplica o tamanho real depois do layout
        #manage_window.transient(self)
        manage_window.grab_set()
        
        manage_window.grid_rowconfigure(0, weight=1)
        manage_window.grid_columnconfigure(0, weight=1)
        
        # Lista de backups
        backup_list = customtkinter.CTkScrollableFrame(manage_window)
        backup_list.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        backup_list.grid_columnconfigure(0, weight=1)
        
        selected_backup = [None]
        backup_widgets = {}
        
        for idx, backup_name in enumerate(backups):
            frame = customtkinter.CTkFrame(backup_list)
            frame.grid(row=idx, column=0, sticky="ew", padx=5, pady=2)
            frame.grid_columnconfigure(0, weight=1)
            
            lbl = customtkinter.CTkLabel(
                frame,
                text=backup_name,
                anchor="w"
            )
            lbl.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
            
            def select_backup(bn=backup_name):
                selected_backup[0] = bn
                for widget in backup_widgets.values():
                    widget.configure(fg_color=["#3B8ED0", "#1F6AA5"])
                frame.configure(fg_color="green")
            
            frame.bind("<Button-1>", lambda e, bn=backup_name: select_backup(bn))
            lbl.bind("<Button-1>", lambda e, bn=backup_name: select_backup(bn))
            
            backup_widgets[backup_name] = frame
        
        # Botões de ação
        button_frame = customtkinter.CTkFrame(manage_window)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        save_paths_btn = customtkinter.CTkButton(
            button_frame,
            text="Salvar Paths",
            command=save_paths_only,
            fg_color="blue",
            width=150
        )
        save_paths_btn.grid(row=0, column=2, padx=10, pady=5)

        def delete_selected():
            if selected_backup[0]:
                if messagebox.askyesno("Confirmar", f"Excluir backup '{selected_backup[0]}'?"):
                    if self.save_lua_manager.delete_backup(self.selected_profile, selected_backup[0]):  # ← CORRIGIR
                        messagebox.showinfo("Sucesso", "Backup excluído!")
                        manage_window.destroy()
                    else:
                        messagebox.showerror("Erro", "Erro ao excluir backup!")
        
        delete_btn = customtkinter.CTkButton(
            button_frame,
            text="Excluir Backup",
            command=delete_selected,
            fg_color="red"
        )
        delete_btn.grid(row=0, column=0, padx=5, pady=5)
        
        close_btn = customtkinter.CTkButton(
            button_frame,
            text="Fechar",
            command=manage_window.destroy
        )
        close_btn.grid(row=0, column=1, padx=5, pady=5)
    
    def open_backup_folder(self):
        """Abre a pasta de backups"""
        try:
            os.startfile(self.save_lua_manager.backup_dir)
        except:
            messagebox.showerror("Erro", "Não foi possível abrir a pasta de backups")
            
    def remove_selected_profile(self):
        """Remove o perfil selecionado"""
        if not self.selected_profile:
            messagebox.showwarning("Aviso", "Selecione um perfil primeiro!")
            return
        
        profile_name = self.save_lua_manager.profiles[self.selected_profile]['name']  # ← CORRIGIR
        game_name = self.save_lua_manager.profiles[self.selected_profile]['game_name']  # ← CORRIGIR
        
        if messagebox.askyesno("Confirmar Remoção", 
                              f"Tem certeza que deseja remover o perfil '{profile_name}' para {game_name}?\n\nTodos os backups associados também serão excluídos."):
            success, message = self.save_lua_manager.remove_profile(self.selected_profile)  # ← CORRIGIR
            if success:
                messagebox.showinfo("Sucesso", message)
                self.selected_profile = None
                self.load_profiles()
            else:
                messagebox.showerror("Erro", message)

# ================= CLASSE PRINCIPAL APP (ORIGINAL COMPLETA) =================
class App(customtkinter.CTk):
    def __init__(self):
        # Exibir cabeçalho de inicialização
        print("="*50)
        print(f"Inicializando LuaFast v{VERSAO_APP}")
        print("="*50)
        
        # Realizar verificações iniciais (agora usando a nova abordagem)
        if not self.realizar_verificacoes_iniciais():
            sys.exit(1)
        
        super().__init__()
        
        # Variável para controlar callbacks
        self.active_callbacks = set()
        
        # ===== CÓDIGO MODIFICADO PARA CARREGAR O ÍCONE =====
        try:
            # Carrega o ícone usando o caminho absoluto
            icon_path = resource_path('icone.ico')
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Erro ao carregar ícone: {str(e)}")
            try:
                # Fallback para PNG se necessário
                icon_path = resource_path('icone.png')
                icon = tk.PhotoImage(file=icon_path)
                self.tk.call('wm', 'iconphoto', self._w, icon)
            except:
                pass  # Ignora se não encontrar o ícone
        # ===================================================

        # Carregar configurações
        self.config = self.carregar_configuracoes()
        
        # Aplicar tema salvo
        customtkinter.set_appearance_mode(self.config["tema"])
        
        # Configurações da janela principal
        self.title("Gerenciador de Games STEAM LuaFast")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Configurar grid de layout (1 linha, 2 colunas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Frame de navegação (à esquerda, para os botões)
        self.navigation_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(10, weight=1)

        # Título do aplicativo
        self.navigation_frame_label = customtkinter.CTkLabel(
            self.navigation_frame,
            text="LuaFast",
            compound="left",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        # Botões de navegação - usando lambda para evitar referência prematura
        self.home_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Início",
            command=lambda: self.home_button_event()
        )
        self.home_button.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        self.install_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Instalar Jogos",
            command=lambda: self.install_button_event()
        )
        self.install_button.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        # NOVO BOTÃO: Instalar DLC's
        self.dlc_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Instalar DLC's",
            command=lambda: self.dlc_button_event()
        )
        self.dlc_button.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        # Nova aba: Atualizar keys Instaladas
        self.update_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Atualizar Keys Instaladas",
            command=lambda: self.update_button_event()
        )
        self.update_button.grid(row=4, column=0, sticky="ew", padx=20, pady=10)

        self.remove_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Remover Jogos",
            command=lambda: self.remove_button_event()
        )
        self.remove_button.grid(row=5, column=0, sticky="ew", padx=20, pady=10)
        
        self.backup_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Backup das Key's",
            command=lambda: self.backup_button_event()
        )
        self.backup_button.grid(row=6, column=0, sticky="ew", padx=20, pady=10)
        
        # NOVO BOTÃO: SAVELUA BACKUP
        self.savelua_button = customtkinter.CTkButton(  # ← MUDAR NOME
            self.navigation_frame,
            text="Save Games",  # ← MUDAR TEXTO
            command=lambda: self.savelua_button_event(),  # ← MUDAR NOME
            #fg_color="purple",
            #hover_color="#6a0dad"
        )
        self.savelua_button.grid(row=7, column=0, sticky="ew", padx=20, pady=10)
        
        # Alteração: Usar função de reinício do fecharsteam.py
        self.fechar_steam_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Reiniciar Steam",
            command=lambda: self.restart_steam()
        )
        self.fechar_steam_button.grid(row=8, column=0, sticky="ew", padx=20, pady=10)
        
        # Botão de configurações
        self.config_button = customtkinter.CTkButton(
            self.navigation_frame,
            text="Configurações",
            command=lambda: self.config_button_event()
        )
        self.config_button.grid(row=9, column=0, sticky="ew", padx=20, pady=10)
        
        # Frame principal (à direita)
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Frame para a tela inicial
        self.home_frame = customtkinter.CTkScrollableFrame(self.main_frame)
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.home_frame.grid_columnconfigure(0, weight=1)
        
        # Frame para instalação (inicialmente oculto)
        self.install_frame = customtkinter.CTkFrame(self.main_frame)
        self.install_frame.grid(row=0, column=0, sticky="nsew")
        self.install_frame.grid_columnconfigure(0, weight=1)
        self.install_frame.grid_rowconfigure(0, weight=1)
        self.install_frame.grid_remove()  # Oculta inicialmente
        
        # Frame para configurações (inicialmente oculto)
        self.config_frame = customtkinter.CTkFrame(self.main_frame)
        self.config_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.config_frame.grid_columnconfigure(0, weight=1)
        self.config_frame.grid_rowconfigure(0, weight=1)
        self.config_frame.grid_remove()  # Oculta inicialmente

        # Frame para remover jogos
        self.remove_frame = customtkinter.CTkFrame(self.main_frame)
        self.remove_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.remove_frame.grid_columnconfigure(0, weight=1)
        self.remove_frame.grid_rowconfigure(0, weight=1)
        self.remove_frame.grid_remove()  # Oculta inicialmente
        
        # Frame para backup
        self.backup_frame = customtkinter.CTkFrame(self.main_frame)
        self.backup_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.backup_frame.grid_columnconfigure(0, weight=1)
        self.backup_frame.grid_rowconfigure(0, weight=1)
        self.backup_frame.grid_remove()  # Oculta inicialmente
        
        # Frame para atualizar keys (nova aba)
        self.update_frame = customtkinter.CTkFrame(self.main_frame)
        self.update_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.update_frame.grid_columnconfigure(0, weight=1)
        self.update_frame.grid_rowconfigure(0, weight=1)
        self.update_frame.grid_remove()  # Oculta inicialmente
        
        # ===== NOVO FRAME PARA INSTALAR DLCS =====
        self.dlc_frame = customtkinter.CTkFrame(self.main_frame)
        self.dlc_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.dlc_frame.grid_columnconfigure(0, weight=1)
        self.dlc_frame.grid_rowconfigure(0, weight=1)
        self.dlc_frame.grid_remove()  # Oculta inicialmente
        
        # ===== CONTEÚDO DA TELA INICIAL =====
        # Banner do aplicativo
        self.app_banner = customtkinter.CTkLabel(
            self.home_frame,
            text="",
            font=customtkinter.CTkFont(size=16, weight="bold")
        )
        self.app_banner.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Informações básicas
        self.info_frame = customtkinter.CTkFrame(self.home_frame)
        self.info_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        
        # Versão e desenvolvedores
        self.version_label = customtkinter.CTkLabel(
            self.info_frame,
            text=f"Ver: {VERSAO_APP} | Dev's: {DEV_INFO}",
            font=customtkinter.CTkFont(size=14)
        )
        self.version_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Site para obter IDs
        self.steamdb_label = customtkinter.CTkLabel(
            self.info_frame,
            text=f"Use o site {STEAMDB_URL} para obter o ID do game desejado.",
            font=customtkinter.CTkFont(size=14)
        )
        self.steamdb_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        # Mensagem de doação
        self.donation_label = customtkinter.CTkLabel(
            self.info_frame,
            text="O LuaFast é totalmente gratuito, mas se você quiser ajudar o projeto.\nFaça uma doação de qualquer valor! Mas não é obrigatorio!\nChave Pix: appluafast@gmail.com",
            font=customtkinter.CTkFont(size=14)
        )
        self.donation_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        # Status da ativação e Steam
        #ativador = Ativador()
        #_, activation_info = ativador.verificar_status()
        #activation_code = activation_info.get("Código", "N/A")
        #activation_status = activation_info.get("Status", "N/A")
        
      
        # Terminal de informações
        self.home_terminal = customtkinter.CTkTextbox(self.home_frame, height=300)
        self.home_terminal.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.home_terminal.insert("1.0", "Configurações atuais:\n")
        self.home_terminal.insert("end", f"- Caminho da Steam: {get_steam_path()}\n")
        #self.home_terminal.insert("end", f"- https://steamdb.info/\n")
        self.home_terminal.configure(state="disabled")
        
        # ===== CONTEÚDO DA TELA DE INSTALAÇÃO =====
        # Configurar grid da tela de instalação
        self.install_frame.grid_rowconfigure(0, weight=0)  # Método
        self.install_frame.grid_rowconfigure(1, weight=0)  # Pesquisa
        self.install_frame.grid_rowconfigure(2, weight=1)  # Lista + Terminal
        self.install_frame.grid_rowconfigure(3, weight=0)  # Botões
        self.install_frame.grid_rowconfigure(4, weight=1)  # Banner
        
        # Frame para seleção de método
        self.method_frame = customtkinter.CTkFrame(self.install_frame)
        self.method_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.method_frame.grid_columnconfigure(0, weight=1)
        self.method_frame.grid_columnconfigure(1, weight=1)
        
        # Label de método
        self.method_label = customtkinter.CTkLabel(
            self.method_frame,
            text="Selecione o método de instalação:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.method_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        # Botões de opção para os métodos
        self.method_var = customtkinter.IntVar(value=1)
        
        self.method1_radio = customtkinter.CTkRadioButton(
            self.method_frame,
            text="Método 1 (Arquivos Prontos)",
            variable=self.method_var,
            value=1
        )
        self.method1_radio.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        
        self.method2_radio = customtkinter.CTkRadioButton(
            self.method_frame,
            text="Método 2 (Gerar Keys)",
            variable=self.method_var,
            value=2
        )
        self.method2_radio.grid(row=1, column=1, padx=20, pady=5, sticky="w")
        
        # Frame para pesquisa de jogos
        self.search_frame = customtkinter.CTkFrame(self.install_frame)
        self.search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.search_frame.grid_columnconfigure(0, weight=1)
        
        # Campo de pesquisa
        self.search_label = customtkinter.CTkLabel(
            self.search_frame,
            text="DIGITE O NOME DO JOGO OU O APP ID:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.search_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.search_entry = customtkinter.CTkEntry(
            self.search_frame,
            placeholder_text="Digite o nome ou ID do jogo..."
        )
        self.search_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search_keyrelease)
        
        # Frame para lista de resultados e terminal (40%/60%)
        self.results_terminal_frame = customtkinter.CTkFrame(self.install_frame)
        self.results_terminal_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.results_terminal_frame.grid_rowconfigure(0, weight=1)
        self.results_terminal_frame.grid_columnconfigure(0, weight=2)  # 40%
        self.results_terminal_frame.grid_columnconfigure(1, weight=3)  # 60%
        
        # Lista de resultados da pesquisa (40% do espaço)
        self.results_frame = customtkinter.CTkScrollableFrame(self.results_terminal_frame)
        self.results_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.results_frame.grid_columnconfigure(0, weight=1)
        
        # Área de log/terminal (60% do espaço)
        self.textbox = customtkinter.CTkTextbox(self.results_terminal_frame)
        self.textbox.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Configura tags para cores
        self.textbox.tag_config("info", foreground="gray")
        self.textbox.tag_config("success", foreground="green")
        self.textbox.tag_config("error", foreground="red")
        self.textbox.tag_config("warning", foreground="orange")
        self.textbox.tag_config("progress_line", foreground="blue")  # Cor especial para progresso
        
        # Sistema de redirecionamento de saída
        self.output_redirect = ThreadSafeText(self.textbox, "info")
        self.output_redirect.start()
        
        # Frame para botões dinâmicos
        self.dynamic_buttons_frame = customtkinter.CTkFrame(self.install_frame, height=50)
        self.dynamic_buttons_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.dynamic_buttons_frame.grid_columnconfigure(0, weight=1)
        
        # Banner do jogo (todo o espaço restante)
        self.banner_frame = customtkinter.CTkFrame(self.install_frame)
        self.banner_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        self.banner_frame.grid_columnconfigure(0, weight=1)
        self.banner_frame.grid_rowconfigure(0, weight=1)
        
        self.banner_label = customtkinter.CTkLabel(
            self.banner_frame, 
            text=" ",
            font=customtkinter.CTkFont(size=14),
            anchor="center"
        )
        self.banner_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # ===== CONTEÚDO DA TELA DE CONFIGURAÇÕES =====
        # Configurar grid da tela de configurações
        self.config_frame.grid_columnconfigure(0, weight=1)
        self.config_frame.grid_rowconfigure(0, weight=0)
        self.config_frame.grid_rowconfigure(1, weight=0)
        self.config_frame.grid_rowconfigure(2, weight=0)
        self.config_frame.grid_rowconfigure(3, weight=0)
        self.config_frame.grid_rowconfigure(4, weight=0)
        self.config_frame.grid_rowconfigure(5, weight=1)
        
        # Título
        self.config_title = customtkinter.CTkLabel(
            self.config_frame,
            text="Configurações",
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        self.config_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Frame para configurações do tema
        self.theme_frame = customtkinter.CTkFrame(self.config_frame, fg_color="transparent")
        self.theme_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.theme_frame.grid_columnconfigure(0, weight=1)
        
        # Seletor de tema
        self.theme_label = customtkinter.CTkLabel(
            self.theme_frame,
            text="Modo de Aparência:",
            font=customtkinter.CTkFont(size=14)
        )
        self.theme_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.theme_var = customtkinter.StringVar(value=self.config["tema"])
        self.theme_selector = customtkinter.CTkOptionMenu(
            self.theme_frame,
            values=["dark", "light"],
            variable=self.theme_var,
            command=self.alterar_tema,
            width=200
        )
        self.theme_selector.grid(row=1, column=0, sticky="w", pady=5)
        
        # Frame para configurações do caminho da Steam
        self.path_frame = customtkinter.CTkFrame(self.config_frame, fg_color="transparent")
        self.path_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.path_frame.grid_columnconfigure(0, weight=1)
        
        # Configuração do caminho da Steam
        self.path_label = customtkinter.CTkLabel(
            self.path_frame,
            text="Caminho da Steam:",
            font=customtkinter.CTkFont(size=14)
        )
        self.path_label.grid(row=0, column=0, sticky="w")
        
        self.steam_path_var = customtkinter.StringVar(value=str(get_steam_path()))
        self.path_entry = customtkinter.CTkEntry(
            self.path_frame,
            width=200
        )
        self.path_entry.grid(row=1, column=0, sticky="ew", pady=5)
        self.path_entry.configure(textvariable=self.steam_path_var)
        
        self.browse_button = customtkinter.CTkButton(
            self.path_frame,
            text="Procurar",
            command=self.selecionar_diretorio,
            width=100
        )
        self.browse_button.grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        # Botão para salvar configurações
        self.save_config_button = customtkinter.CTkButton(
            self.config_frame,
            text="Salvar Configurações",
            command=self.salvar_configuracoes,
            width=200
        )
        self.save_config_button.grid(row=4, column=0, pady=20)
        
        # ===== CONTEÚDO DA TELA DE REMOÇÃO =====
        # Configurar grid da tela de remoção
        self.remove_frame.grid_columnconfigure(0, weight=1)
        self.remove_frame.grid_rowconfigure(0, weight=0)  # Título
        self.remove_frame.grid_rowconfigure(1, weight=0)  # Pesquisa
        self.remove_frame.grid_rowconfigure(2, weight=1)  # Lista
        self.remove_frame.grid_rowconfigure(3, weight=0)  # Botões
        
        # Título
        self.remove_title = customtkinter.CTkLabel(
            self.remove_frame,
            text="Remover Jogos",
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        self.remove_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Frame para pesquisa de jogos instalados
        self.remove_search_frame = customtkinter.CTkFrame(self.remove_frame, fg_color="transparent")
        self.remove_search_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.remove_search_frame.grid_columnconfigure(0, weight=1)
        
        # Campo de pesquisa para remoção
        self.remove_search_label = customtkinter.CTkLabel(
            self.remove_search_frame,
            text="Pesquisar jogo instalado:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.remove_search_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.remove_search_entry = customtkinter.CTkEntry(
            self.remove_search_frame,
            placeholder_text="Digite o nome ou ID do jogo..."
        )
        self.remove_search_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.remove_search_entry.bind("<KeyRelease>", self.on_remove_search_keyrelease)
        
        # Frame para lista de jogos instalados
        self.remove_list_frame = customtkinter.CTkScrollableFrame(
            self.remove_frame,
            height=500
        )
        self.remove_list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.remove_list_frame.grid_columnconfigure(0, weight=1)
        
        # Frame para botões
        self.remove_buttons_frame = customtkinter.CTkFrame(self.remove_frame, fg_color="transparent")
        self.remove_buttons_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.remove_buttons_frame.grid_columnconfigure(0, weight=1)
        self.remove_buttons_frame.grid_columnconfigure(1, weight=1)
        
        self.remove_confirm_button = customtkinter.CTkButton(
            self.remove_buttons_frame,
            text="Remover Selecionados",
            command=self.remove_selected_games,
            fg_color="red",
            hover_color="darkred"
        )
        self.remove_confirm_button.grid(row=0, column=0, padx=10)
        
        self.remove_cancel_button = customtkinter.CTkButton(
            self.remove_buttons_frame,
            text="Cancelar",
            command=self.home_button_event
        )
        self.remove_cancel_button.grid(row=0, column=1, padx=10)
        
        # ===== CONTEÚDO DA TELA DE BACKUP =====
        self.backup_frame.grid_columnconfigure(0, weight=1)
        self.backup_frame.grid_rowconfigure(0, weight=0)
        self.backup_frame.grid_rowconfigure(1, weight=1)
        self.backup_frame.grid_rowconfigure(2, weight=0)
        
        # Título
        self.backup_title = customtkinter.CTkLabel(
            self.backup_frame,
            text="Backup e Restauração",
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        self.backup_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Frame principal dividido em duas colunas
        self.backup_main_frame = customtkinter.CTkFrame(self.backup_frame, fg_color="transparent")
        self.backup_main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.backup_main_frame.grid_columnconfigure(0, weight=1)
        self.backup_main_frame.grid_columnconfigure(1, weight=1)
        self.backup_main_frame.grid_rowconfigure(0, weight=1)
        
        # Frame esquerdo - Backup
        self.backup_left_frame = customtkinter.CTkFrame(self.backup_main_frame)
        self.backup_left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.backup_left_frame.grid_columnconfigure(0, weight=1)
        self.backup_left_frame.grid_rowconfigure(0, weight=0)
        self.backup_left_frame.grid_rowconfigure(1, weight=1)
        self.backup_left_frame.grid_rowconfigure(2, weight=0)
        
        self.backup_left_title = customtkinter.CTkLabel(
            self.backup_left_frame,
            text="Jogos Instalados",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.backup_left_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Lista de jogos para backup
        self.backup_list_frame = customtkinter.CTkScrollableFrame(
            self.backup_left_frame,
            height=400
        )
        self.backup_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.backup_list_frame.grid_columnconfigure(0, weight=1)
        
        # Botões de backup
        self.backup_buttons_frame = customtkinter.CTkFrame(self.backup_left_frame, fg_color="transparent")
        self.backup_buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.backup_buttons_frame.grid_columnconfigure(0, weight=1)
        self.backup_buttons_frame.grid_columnconfigure(1, weight=1)
        self.backup_buttons_frame.grid_columnconfigure(2, weight=1)

        self.backup_select_all_button = customtkinter.CTkButton(
            self.backup_buttons_frame,
            text="Selecionar Todos",
            command=self.select_all_backup,
            width=120
        )
        self.backup_select_all_button.grid(row=0, column=0, padx=5)

        self.backup_button = customtkinter.CTkButton(
            self.backup_buttons_frame,
            text="Fazer Backup",
            command=self.do_backup,
            fg_color="green",
            width=120
        )
        self.backup_button.grid(row=0, column=1, padx=5)

        self.backup_cancel_button = customtkinter.CTkButton(
            self.backup_buttons_frame,
            text="Cancelar",
            command=self.home_button_event,
            width=120
        )
        self.backup_cancel_button.grid(row=0, column=2, padx=5)
        
        # Frame direito - Restauração
        self.backup_right_frame = customtkinter.CTkFrame(self.backup_main_frame)
        self.backup_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.backup_right_frame.grid_columnconfigure(0, weight=1)
        self.backup_right_frame.grid_rowconfigure(0, weight=0)
        self.backup_right_frame.grid_rowconfigure(1, weight=1)
        self.backup_right_frame.grid_rowconfigure(2, weight=0)
        
        self.backup_right_title = customtkinter.CTkLabel(
            self.backup_right_frame,
            text="Backups Existentes",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.backup_right_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Lista de backups
        self.restore_list_frame = customtkinter.CTkScrollableFrame(
            self.backup_right_frame,
            height=400
        )
        self.restore_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.restore_list_frame.grid_columnconfigure(0, weight=1)
        
        # Botões de restauração
        self.restore_buttons_frame = customtkinter.CTkFrame(self.backup_right_frame, fg_color="transparent")
        self.restore_buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.restore_buttons_frame.grid_columnconfigure(0, weight=1)
        self.restore_buttons_frame.grid_columnconfigure(1, weight=1)
        self.restore_buttons_frame.grid_columnconfigure(2, weight=1)

        self.restore_select_all_button = customtkinter.CTkButton(
            self.restore_buttons_frame,
            text="Selecionar Todos",
            command=self.select_all_restore,
            width=120
        )
        self.restore_select_all_button.grid(row=0, column=0, padx=5)

        self.restore_button = customtkinter.CTkButton(
            self.restore_buttons_frame,
            text="Restaurar Backup",
            command=self.do_restore,
            fg_color="blue",
            width=120
        )
        self.restore_button.grid(row=0, column=1, padx=5)

        self.restore_cancel_button = customtkinter.CTkButton(
            self.restore_buttons_frame,
            text="Cancelar",
            command=self.home_button_event,
            width=120
        )
        self.restore_cancel_button.grid(row=0, column=2, padx=5)
        
        # ===== CONTEÚDO DA TELA DE ATUALIZAÇÃO =====
        self.update_frame.grid_columnconfigure(0, weight=1)
        self.update_frame.grid_rowconfigure(0, weight=0)
        self.update_frame.grid_rowconfigure(1, weight=0)
        self.update_frame.grid_rowconfigure(2, weight=1)
        self.update_frame.grid_rowconfigure(3, weight=0)
        
        # Título
        self.update_title = customtkinter.CTkLabel(
            self.update_frame,
            text="Update Keys",
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        self.update_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Frame para pesquisa de jogos instalados
        self.update_search_frame = customtkinter.CTkFrame(self.update_frame, fg_color="transparent")
        self.update_search_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.update_search_frame.grid_columnconfigure(0, weight=1)
        
        # Campo de pesquisa para atualização
        self.update_search_label = customtkinter.CTkLabel(
            self.update_search_frame,
            text="Pesquisar jogo instalado:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.update_search_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.update_search_entry = customtkinter.CTkEntry(
            self.update_search_frame,
            placeholder_text="Digite o nome ou ID do jogo..."
        )
        self.update_search_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.update_search_entry.bind("<KeyRelease>", self.on_update_search_keyrelease)
        
        # Frame para lista de jogos instalados e terminal
        self.update_results_terminal_frame = customtkinter.CTkFrame(self.update_frame)
        self.update_results_terminal_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.update_results_terminal_frame.grid_rowconfigure(0, weight=1)
        self.update_results_terminal_frame.grid_columnconfigure(0, weight=2)
        self.update_results_terminal_frame.grid_columnconfigure(1, weight=3)
        
        # Lista de jogos instalados
        self.update_list_frame = customtkinter.CTkScrollableFrame(self.update_results_terminal_frame)
        self.update_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.update_list_frame.grid_columnconfigure(0, weight=1)
        
        # Área de log/terminal
        self.update_textbox = customtkinter.CTkTextbox(self.update_results_terminal_frame)
        self.update_textbox.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Configura tags para cores
        self.update_textbox.tag_config("info", foreground="gray")
        self.update_textbox.tag_config("success", foreground="green")
        self.update_textbox.tag_config("error", foreground="red")
        self.update_textbox.tag_config("warning", foreground="orange")
        self.update_textbox.tag_config("progress_line", foreground="blue")
        
        # Sistema de redirecionamento de saída
        self.update_output_redirect = ThreadSafeText(self.update_textbox, "info")
        self.update_output_redirect.start()
        
        # Frame para botões
        self.update_buttons_frame = customtkinter.CTkFrame(self.update_frame, fg_color="transparent")
        self.update_buttons_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.update_buttons_frame.grid_columnconfigure(0, weight=1)
        self.update_buttons_frame.grid_columnconfigure(1, weight=1)
        
        self.update_button = customtkinter.CTkButton(
            self.update_buttons_frame,
            text="Atualizar Selecionado",
            command=self.update_selected_game,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.update_button.grid(row=0, column=0, padx=10)
        
        self.update_cancel_button = customtkinter.CTkButton(
            self.update_buttons_frame,
            text="Cancelar",
            command=self.home_button_event
        )
        self.update_cancel_button.grid(row=0, column=1, padx=10)
        
        # ===== CONTEÚDO DA TELA DE DLCS =====
        self.dlc_frame.grid_columnconfigure(0, weight=1)
        self.dlc_frame.grid_rowconfigure(0, weight=0)
        self.dlc_frame.grid_rowconfigure(1, weight=1)
        self.dlc_frame.grid_rowconfigure(2, weight=0)
        
        # Título
        self.dlc_title = customtkinter.CTkLabel(
            self.dlc_frame,
            text="Instalar DLC's",
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        self.dlc_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Frame principal dividido em duas colunas
        self.dlc_main_frame = customtkinter.CTkFrame(self.dlc_frame, fg_color="transparent")
        self.dlc_main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.dlc_main_frame.grid_columnconfigure(0, weight=1)
        self.dlc_main_frame.grid_columnconfigure(1, weight=1)
        self.dlc_main_frame.grid_rowconfigure(0, weight=1)
        
        # Frame esquerdo - Jogos Instalados
        self.dlc_left_frame = customtkinter.CTkFrame(self.dlc_main_frame)
        self.dlc_left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.dlc_left_frame.grid_columnconfigure(0, weight=1)
        self.dlc_left_frame.grid_rowconfigure(0, weight=0)
        self.dlc_left_frame.grid_rowconfigure(1, weight=1)
        
        self.dlc_left_title = customtkinter.CTkLabel(
            self.dlc_left_frame,
            text="Jogos Instalados",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.dlc_left_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Lista de jogos para DLCs
        self.dlc_games_frame = customtkinter.CTkScrollableFrame(
            self.dlc_left_frame,
            height=400
        )
        self.dlc_games_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.dlc_games_frame.grid_columnconfigure(0, weight=1)
        
        # Frame direito - DLCs disponíveis
        self.dlc_right_frame = customtkinter.CTkFrame(self.dlc_main_frame)
        self.dlc_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.dlc_right_frame.grid_columnconfigure(0, weight=1)
        self.dlc_right_frame.grid_rowconfigure(0, weight=0)
        self.dlc_right_frame.grid_rowconfigure(1, weight=1)
        self.dlc_right_frame.grid_rowconfigure(2, weight=0)
        
        self.dlc_right_title = customtkinter.CTkLabel(
            self.dlc_right_frame,
            text="DLCs Disponíveis",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.dlc_right_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Lista de DLCs
        self.dlc_list_frame = customtkinter.CTkScrollableFrame(
            self.dlc_right_frame,
            height=400
        )
        self.dlc_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.dlc_list_frame.grid_columnconfigure(0, weight=1)
        
        # Botão de instalar DLCs
        self.dlc_install_button = customtkinter.CTkButton(
            self.dlc_right_frame,
            text="Instalar Seleção",
            command=self.install_selected_dlcs,
            fg_color="green"
        )
        self.dlc_install_button.grid(row=2, column=0, padx=10, pady=10)
        
        # Frame para botões inferiores
        self.dlc_buttons_frame = customtkinter.CTkFrame(self.dlc_frame, fg_color="transparent")
        self.dlc_buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.dlc_buttons_frame.grid_columnconfigure(0, weight=1)
        self.dlc_buttons_frame.grid_columnconfigure(1, weight=1)
        
        self.dlc_cancel_button = customtkinter.CTkButton(
            self.dlc_buttons_frame,
            text="Cancelar",
            command=self.home_button_event
        )
        self.dlc_cancel_button.grid(row=0, column=1, padx=10)
        
        # Variáveis de estado
        self.selected_appid = None
        self.selected_game_name = None
        self.current_question = None
        self.results_cache = []
        self.install_data = {}
        self.selected_games = {}
        self.backup_selected_games = {}
        self.restore_selected_games = {}
        self.update_selected_game_id = None
        self.dlc_selected_game_id = None
        self.dlc_selected = {}
        
        # Exibe informações iniciais
        self.home_button_event()

    # ===== MÉTODOS DE NAVEGAÇÃO =====
    
    def home_button_event(self):
        """Mostra a tela inicial"""
        self.install_frame.grid_remove()
        self.config_frame.grid_remove()
        self.remove_frame.grid_remove()
        self.backup_frame.grid_remove()
        self.update_frame.grid_remove()
        self.dlc_frame.grid_remove()
        self.home_frame.grid()
        
        # Atualiza informações de status
        #ativador = Ativador()
        #_, activation_info = ativador.verificar_status()
        #activation_code = activation_info.get("Código", "N/A")
        #activation_status = activation_info.get("Status", "N/A")
        
        from dll_manager import check_and_install
        _, steam_status = check_and_install()
        

    def install_button_event(self):
        """Mostra a tela de instalação de jogos"""
        self.home_frame.grid_remove()
        self.config_frame.grid_remove()
        self.remove_frame.grid_remove()
        self.backup_frame.grid_remove()
        self.update_frame.grid_remove()
        self.dlc_frame.grid_remove()
        self.install_frame.grid()
        
        self.textbox.delete("1.0", "end")
        self.textbox.insert("end", " \n")
        self.output_redirect.force_scroll()
        
        # Limpa seleções anteriores
        self.selected_appid = None
        self.selected_game_name = None
        self.search_entry.delete(0, "end")
        
        # Limpa botões dinâmicos
        self.clear_dynamic_buttons()
        
        # Adiciona botão para iniciar instalação
        self.add_dynamic_button("Iniciar Instalação", self.start_installation)
    
    def config_button_event(self):
        """Mostra a tela de configurações"""
        self.home_frame.grid_remove()
        self.install_frame.grid_remove()
        self.remove_frame.grid_remove()
        self.backup_frame.grid_remove()
        self.update_frame.grid_remove()
        self.dlc_frame.grid_remove()
        self.config_frame.grid()
        
        # Atualiza o caminho da Steam no campo
        self.steam_path_var.set(str(get_steam_path()))

    def remove_button_event(self):
        """Mostra a tela de remoção de jogos"""
        self.home_frame.grid_remove()
        self.install_frame.grid_remove()
        self.config_frame.grid_remove()
        self.backup_frame.grid_remove()
        self.update_frame.grid_remove()
        self.dlc_frame.grid_remove()
        self.remove_frame.grid()
        
        self.load_installed_games()

    def backup_button_event(self):
        """Mostra a tela de backup e restauração"""
        self.home_frame.grid_remove()
        self.install_frame.grid_remove()
        self.config_frame.grid_remove()
        self.remove_frame.grid_remove()
        self.update_frame.grid_remove()
        self.dlc_frame.grid_remove()
        self.backup_frame.grid()
        
        # Carrega listas de jogos e backups
        self.load_installed_games_for_backup()
        self.load_existing_backups()

    def savelua_button_event(self):  # ← MUDAR NOME
        """Abre a janela do SaveLua"""
        save_lua_window = SaveLuaWindow(self)  # ← MUDAR NOME
        save_lua_window.focus()

    def update_button_event(self):
        """Mostra a tela de atualização de keys instaladas"""
        self.home_frame.grid_remove()
        self.install_frame.grid_remove()
        self.config_frame.grid_remove()
        self.remove_frame.grid_remove()
        self.backup_frame.grid_remove()
        self.dlc_frame.grid_remove()
        self.update_frame.grid()
        
        self.load_update_games()

    def dlc_button_event(self):
        """Mostra a tela de instalação de DLCs"""
        self.home_frame.grid_remove()
        self.install_frame.grid_remove()
        self.config_frame.grid_remove()
        self.remove_frame.grid_remove()
        self.backup_frame.grid_remove()
        self.update_frame.grid_remove()
        self.dlc_frame.grid()
        
        # Carrega a lista de jogos instalados
        self.load_installed_games_for_dlc()

    # ===== MÉTODOS ORIGINAIS DO visual.py =====
    
    def realizar_verificacoes_iniciais(self):
        """Realiza verificações iniciais"""
        print("[INICIALIZAÇÃO] Iniciando verificações...")
        
        def show_error_and_exit(title, message):
            print(f" ERRO - {title}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, message)
            root.destroy()
            sys.exit(1)
        
        def show_warning_and_continue(title, message):
            print(f" AVISO - {title}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(title, message)
            root.destroy()
        
        # 1. REMOVIDA: Verificação de licença
        print("[LICENÇA] Verificação desativada...", end="", flush=True)
        print(" OK - Verificação Desativada")
        
        # 2. Verificação de caminho da Steam
        print("[STEAM] Verificando caminho da Steam...", end="", flush=True)
        steam_path = get_steam_path()
        if not steam_path or not os.path.exists(steam_path):
            print(" NÃO ENCONTRADO")
            message = (
                "Não foi possível encontrar a pasta de instalação da Steam.\n\n"
                "Você precisa configurar manualmente o caminho onde a Steam está instalada.\n\n"
                "Vá em 'Configurações' → 'Caminho da Steam' e selecione a pasta correta."
            )
            show_warning_and_continue("Steam Não Encontrada", message)
        else:
            print(" OK")
            print(f"    Caminho válido: {steam_path}")
        
        # 3. Verificação de componentes (DLL + arquivos necessários)
        print("[COMPONENTES] Verificando componentes necessários...", end="", flush=True)
        try:
            from dll_manager import check_all_components
            status_components, components_msg = check_all_components()
            
            if not status_components:
                print(" AVISO - Alguns componentes necessitam atenção")
                print(f"    {components_msg}")
                # Não bloqueia a execução, apenas avisa
            else:
                print(" OK")
                print(f"    {components_msg}")
        except Exception as e:
            print(" AVISO - Erro na verificação de componentes")
            print(f"    Erro: {str(e)}")
        
        # 4. Verificação de dependências
        print("[DEPENDÊNCIAS] Verificando módulos...", end="", flush=True)
        try:
            import requests
            import PIL
            import customtkinter
            print(" OK")
        except ImportError as e:
            show_error_and_exit("Dependência Faltando", 
                               f"Módulo faltando: {str(e)}\nExecute 'pip install -r requirements.txt'\n\nPressione OK para sair.")
        
        print("[INICIALIZAÇÃO] Verificações concluídas!")
        return True

    def safe_after(self, delay_ms, callback, *args):
        """Executa um callback de forma segura"""
        if self.winfo_exists():
            self.after(delay_ms, lambda: self.safe_callback_wrapper(callback, *args))
    
    def safe_callback_wrapper(self, callback, *args):
        """Wrapper para executar callbacks de forma segura"""
        if self.winfo_exists():
            try:
                callback(*args)
            except Exception as e:
                print(f"Erro no callback: {str(e)}")
    
    def selecionar_diretorio(self):
        """Abre uma janela para selecionar o diretório da Steam"""
        diretorio = filedialog.askdirectory(title="Selecione o diretório da Steam")
        if diretorio:
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", "steam.exe"], 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
                subprocess.run(
                    ["taskkill", "/f", "/im", "steamservice.exe"], 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
                subprocess.run(
                    ["taskkill", "/f", "/im", "steamwebhelper.exe"], 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
                time.sleep(1)
            except Exception as e:
                print(f"Aviso: Não foi possível fechar processos da Steam: {str(e)}")
            
            old_path = get_steam_path()
            try:
                hid_dll_old = old_path / "hid.dll"
                if hid_dll_old.exists() and hid_dll_old.is_file():
                    try:
                        os.remove(hid_dll_old)
                        print(f"Arquivo {hid_dll_old} removido com sucesso.")
                    except Exception as e:
                        print(f"Aviso: Não foi possível remover {hid_dll_old}: {str(e)}")
                
                steamall_old = old_path / "SteamAll"
                if steamall_old.exists() and steamall_old.is_dir():
                    try:
                        shutil.rmtree(steamall_old, ignore_errors=True)
                        print(f"Pasta {steamall_old} removida com sucesso.")
                    except Exception as e:
                        print(f"Aviso: Não foi possível remover {steamall_old}: {str(e)}")
            except Exception as e:
                print(f"Aviso: Não foi possível limpar o diretório antigo: {str(e)}")
            
            self.steam_path_var.set(diretorio)
            set_steam_path(diretorio)
            self.salvar_configuracoes()
            
            steam_exe = os.path.join(diretorio, "Steam.exe")
            
            if os.path.isfile(steam_exe):
                try:
                    icon_path = resource_path('icone.ico')
                    destino_icone = os.path.join(diretorio, "icone.ico")
                    if os.path.exists(icon_path):
                        shutil.copy(icon_path, destino_icone)
                    else:
                        print(f"Aviso: icone.ico não encontrado no diretório do script: {icon_path}")
                    
                    self.criar_atalho_steam(diretorio, steam_exe, destino_icone)
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao criar atalho: {str(e)}")
            else:
                messagebox.showwarning("Aviso", "Steam.exe não encontrado no diretório selecionado. O atalho não será criado.")

            messagebox.showinfo("Sucesso", "Caminho da Steam atualizado com sucesso! Feche o LuaFast e abra novamente para as mudanças entrarem em vigor.")
    
    def criar_atalho_steam(self, steam_dir, steam_exe, icon_path):
        """Cria um atalho para a Steam"""
        try:
            import win32com.client
            from win32com.client import Dispatch
            
            def get_real_desktop():
                CSIDL_DESKTOP = 0x0000
                SHGFP_TYPE_CURRENT = 0
                buf = create_unicode_buffer(wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_DESKTOP, 0, SHGFP_TYPE_CURRENT, buf)
                return os.path.normpath(buf.value)

            desktop_paths = [
                get_real_desktop(),
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/OneDrive/Desktop"),
                os.path.expanduser("~/OneDrive/Ambiente de Trabalho")
            ]

            unique_paths = []
            for path in desktop_paths:
                normalized = os.path.normpath(path)
                if os.path.exists(normalized) and normalized not in unique_paths:
                    unique_paths.append(normalized)

            shortcut_created = False
            for desktop in unique_paths:
                try:
                    shortcut_path = os.path.join(desktop, "Steam LuaFast.lnk")
                    shortcut_path = os.path.normpath(shortcut_path)
                    
                    if os.path.exists(shortcut_path):
                        os.remove(shortcut_path)
                    
                    if not os.path.exists(icon_path):
                        icon_path = steam_exe
                        print("Aviso: icone.ico não encontrado. Usando ícone padrão.")

                    shell = Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(shortcut_path)
                    shortcut.TargetPath = steam_exe
                    shortcut.Arguments = "-noverifyfiles -nobootstrapupdate -skipinitialbootstrap -norepairfiles -console"
                    shortcut.WorkingDirectory = steam_dir
                    shortcut.IconLocation = icon_path
                    shortcut.save()
                    
                    print(f"Atalho criado em: {shortcut_path}")
                    shortcut_created = True
                    break
                    
                except Exception as e:
                    print(f"Falha em {desktop}: {str(e)}")
                    continue

            if not shortcut_created:
                messagebox.showwarning("Aviso", "Não foi possível criar o atalho em nenhum local!")

        except ImportError:
            pass
        except Exception as e:
            print(f"Erro ao criar atalho: {str(e)}")
    
    def carregar_configuracoes(self):
        """Carrega as configurações do arquivo"""
        config_padrao = {
            "tema": "dark"
        }
        
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                    config_carregada = json.load(f)
                    # Garante que todas as chaves padrão existam
                    for chave, valor in config_padrao.items():
                        if chave not in config_carregada:
                            config_carregada[chave] = valor
                    return config_carregada
        except Exception as e:
            print(f"Erro ao carregar configurações: {str(e)}")
        
        # Se não conseguir carregar, cria arquivo com configurações padrão
        try:
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(config_padrao, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar configurações padrão: {str(e)}")
            
        return config_padrao
    
    def salvar_configuracoes(self):
        """Salva as configurações no arquivo"""
        try:
            config = {
                "tema": self.theme_var.get()
            }
            
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
                
            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar configurações: {str(e)}")
    
    def alterar_tema(self, escolha):
        """Altera o modo de aparência"""
        customtkinter.set_appearance_mode(escolha)

    def clear_dynamic_buttons(self):
        """Limpa todos os botões dinâmicos"""
        for widget in self.dynamic_buttons_frame.winfo_children():
            try:
                widget.destroy()
            except:
                pass

    def add_dynamic_button(self, text, command):
        """Adiciona um botão dinâmico ao frame"""
        btn = customtkinter.CTkButton(
            self.dynamic_buttons_frame,
            text=text,
            command=command
        )
        btn.grid(row=0, column=len(self.dynamic_buttons_frame.winfo_children()), 
               padx=5, pady=5, sticky="ew")

    def on_search_keyrelease(self, event):
        """Atualiza os resultados da pesquisa"""
        search_term = self.search_entry.get().strip()
        if len(search_term) >= 3:
            threading.Thread(target=self.search_games, args=(search_term,), daemon=True).start()

    def search_games(self, search_term):
        """Pesquisa jogos na Steam"""
        for widget in self.results_frame.winfo_children():
            try:
                widget.destroy()
            except:
                pass
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = []
            if search_term.isdigit():
                try:
                    url = f"https://store.steampowered.com/api/appdetails?appids={search_term}"
                    response = requests.get(url)
                    data = response.json()
                    if data and str(search_term) in data and data[str(search_term)]['success']:
                        jogo_data = data[str(search_term)]['data']
                        results = [{
                            'id': search_term,
                            'name': jogo_data.get('name', f'Jogo {search_term}')
                        }]
                except:
                    pass
            
            if not results:
                results = loop.run_until_complete(pesquisar_jogo_por_nome(search_term))
            
            loop.close()
            
            self.safe_after(0, self.display_search_results, results)
        except Exception as e:
            self.output_redirect.write(f"\nErro na pesquisa: {str(e)}\n")

    def display_search_results(self, results):
        """Exibe os resultados da pesquisa"""
        self.results_cache = results
        
        for idx, jogo in enumerate(results):
            btn = customtkinter.CTkButton(
                self.results_frame,
                text=f"{jogo['name']} (ID: {jogo['id']})",
                command=lambda idx=idx: self.select_game(idx),
                anchor="w",
                height=30
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=2)

    def select_game(self, index):
        """Seleciona um jogo da lista"""
        if index < len(self.results_cache):
            self.textbox.delete("1.0", "end")
            
            game = self.results_cache[index]
            self.selected_appid = game['id']
            self.selected_game_name = game['name']
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, f"{game['name']} ({game['id']})")
            self.load_game_banner(game['id'])
            
            self.textbox.insert(customtkinter.END, f"\nJogo selecionado: {game['name']} (ID: {game['id']})\n", "info")
            self.output_redirect.force_scroll()
            
            threading.Thread(target=self.check_drm, args=(game['id'],), daemon=True).start()

    def load_game_banner(self, appid):
        """Carrega o banner do jogo"""
        try:
            url = f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg"
            response = requests.get(url)
            response.raise_for_status()
            
            img = Image.open(io.BytesIO(response.content))
            
            width, height = img.size
            new_height = 200
            new_width = int((new_height / height) * width)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            ctk_img = customtkinter.CTkImage(
                light_image=img,
                dark_image=img,
                size=(new_width, new_height)
            )
            
            self.banner_label.configure(image=ctk_img, text="")
        except Exception as e:
            self.banner_label.config(image='')

    def check_drm(self, appid):
        """Verifica o DRM do jogo"""
        try:
            from io import StringIO
            import sys
            old_stdout = sys.stdout
            sys.stdout = buffer = StringIO()
            
            verificar_drm(appid)
            
            sys.stdout = old_stdout
            
            drm_output = buffer.getvalue()
            
            self.textbox.insert(customtkinter.END, drm_output, "info")
            self.output_redirect.force_scroll()
            
        except Exception as e:
            error_msg = f"\nErro ao verificar DRM: {str(e)}\n"
            self.textbox.insert(customtkinter.END, error_msg, "error")
            print(error_msg)

    def run_in_thread(self, target_function, *args):
        """Executa a função alvo em uma thread separada"""
        def runner():
            sys.stdout = self.output_redirect
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if asyncio.iscoroutinefunction(target_function):
                    loop.run_until_complete(target_function(*args))
                else:
                    target_function(*args)
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
        
        thread = threading.Thread(target=runner)
        thread.daemon = True
        thread.start()

    async def install_game(self, appid, metodo):
        """Função assíncrona para instalar o jogo"""
        try:
            if metodo == 1:
                data_recente, total = await baixar_do_bruhhub(appid)
                if data_recente:
                    self.textbox.insert(customtkinter.END, f"✅ {self.selected_game_name} adicionado com sucesso!\n", "success")
                    try:
                        from datetime import datetime
                        data_obj = datetime.fromisoformat(data_recente.replace('Z', '+00:00'))
                        data_br = data_obj.strftime("%d-%m-%Y")
                    except:
                        data_br = formatar_data_brasil(data_recente)
                    self.textbox.insert(customtkinter.END, f"📅 Data: {data_br}\n", "info")
                    self.textbox.insert(customtkinter.END, f"📦 Arquivos: {total}\n\n", "info")
                    self.output_redirect.force_scroll()
                    self.safe_after(0, self.ask_restart_steam)
                else:
                    self.textbox.insert(customtkinter.END, f"\n❌ No momento não possuimos as keys para: {self.selected_game_name}\n", "error")
                    self.textbox.insert(customtkinter.END, f"⚠️ Tente o método 2\n\n", "warning")
                    self.output_redirect.force_scroll()
                    
            elif metodo == 2:
                repo_usado, data_recente, depot_data, depot_map = await desbloquear_jogo(appid)
                
                if repo_usado:
                    self.install_data = {
                        "appid": appid,
                        "depot_data": depot_data,
                        "depot_map": depot_map,
                        "data_recente": data_recente
                    }
                    
                    self.textbox.insert(customtkinter.END, f"\nDeseja bloquear os updates para {self.selected_game_name}?\n", "info")
                    self.output_redirect.force_scroll()
                    
                    self.safe_after(0, self.show_versionlock_buttons)
                else:
                    self.textbox.insert(customtkinter.END, f"\n❌ Não encontrado: {self.selected_game_name}\n\n", "error")
                    self.output_redirect.force_scroll()
                    self.safe_after(0, self.ask_restart_steam)
            
        except Exception as e:
            error_msg = f"\nErro na instalação: {str(e)}\n"
            self.textbox.insert(customtkinter.END, error_msg, "error")
            print(error_msg)

    def show_versionlock_buttons(self):
        """Mostra botões para decisão sobre versionlock"""
        self.clear_dynamic_buttons()
        self.add_dynamic_button("Sim, bloquear updates", 
                               lambda: self.run_in_thread(self.apply_versionlock, True))
        self.add_dynamic_button("Não, permitir updates", 
                               lambda: self.run_in_thread(self.apply_versionlock, False))

    async def apply_versionlock(self, decision):
        """Aplica a decisão do usuário"""
        try:
            appid = self.install_data["appid"]
            depot_data = self.install_data["depot_data"]
            depot_map = self.install_data["depot_map"]
            data_recente = self.install_data["data_recente"]
            
            await apply_versionlock_decision(appid, decision, depot_data, depot_map)
            
            self.textbox.insert(customtkinter.END, f"\n✅ {self.selected_game_name} adicionado!\n", "success")
            try:
                from datetime import datetime
                data_obj = datetime.fromisoformat(data_recente.replace('Z', '+00:00'))
                data_br = data_obj.strftime("%d-%m-%Y")
            except:
                data_br = formatar_data_brasil(data_recente)
            self.textbox.insert(customtkinter.END, f"📅 Data: {data_br}\n\n", "info")
            self.output_redirect.force_scroll()
            
            self.safe_after(0, self.ask_restart_steam)
                
        except Exception as e:
            error_msg = f"\nErro ao aplicar: {str(e)}\n"
            self.textbox.insert(customtkinter.END, error_msg, "error")
            self.output_redirect.force_scroll()

    def ask_restart_steam(self):
        """Pergunta sobre reiniciar Steam"""
        self.clear_dynamic_buttons()
        self.add_dynamic_button("Reinicicar Steam", self.restart_steam)
        self.add_dynamic_button("Pegar outro jogo", self.install_button_event)
        self.textbox.insert(customtkinter.END, "Reiniciar Steam agora? (Sim/Não)\n", "info")
        self.output_redirect.force_scroll()

    def restart_steam(self):
        """Reinicia a Steam"""
        self.output_redirect.write("\nReiniciando Steam...\n")
        encerrar_steam_processos()
        reiniciar_steam_fechar()
        self.output_redirect.write("✅ Steam reiniciada!\n\n")
        self.output_redirect.force_scroll()
        self.clear_dynamic_buttons()
        self.add_dynamic_button("Instalar outro", self.install_button_event)
        self.add_dynamic_button("Voltar", self.home_button_event)

    def start_installation(self):
        """Inicia o processo de instalação"""
        if not self.selected_appid:
            self.output_redirect.write("\nErro: Nenhum jogo selecionado!\n")
            self.output_redirect.force_scroll()
            return
            
        metodo = self.method_var.get()
        self.output_redirect.write(f"\nIniciando instalação do jogo:\n")
        self.output_redirect.write(f"- ID: {self.selected_appid}\n")
        self.output_redirect.write(f"- Nome: {self.selected_game_name}\n")
        self.output_redirect.write(f"- Método: {metodo}\n\n")
        self.output_redirect.force_scroll()
        
        self.run_in_thread(self.install_game, self.selected_appid, metodo)

    # ===== MÉTODOS PARA REMOÇÃO =====
    
    def on_remove_search_keyrelease(self, event):
        """Filtra a lista de jogos instalados"""
        search_term = self.remove_search_entry.get().strip().lower()
        
        if not search_term:
            for appid, data in self.selected_games.items():
                if "widget" in data and data["widget"].winfo_exists():
                    data["widget"].grid()
            return
        
        for appid, data in self.selected_games.items():
            if "widget" in data and data["widget"].winfo_exists():
                game_name = data.get("name", f"Jogo {appid}").lower()
                if search_term in game_name or search_term in appid:
                    data["widget"].grid()
                else:
                    data["widget"].grid_remove()

    def load_installed_games(self):
        """Carrega a lista de jogos instalados"""
        for widget in self.remove_list_frame.winfo_children():
            widget.destroy()
        
        self.selected_games = {}
        
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        if not stplug_path.exists():
            no_games_label = customtkinter.CTkLabel(
                self.remove_list_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        lua_files = [f for f in stplug_path.glob("*.lua") if f.stem != "Steamtools"]
        if not lua_files:
            no_games_label = customtkinter.CTkLabel(
                self.remove_list_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        for idx, lua_file in enumerate(lua_files):
            appid = lua_file.stem
            var = tk.BooleanVar(value=False)
            
            threading.Thread(
                target=self.load_game_name,
                args=(appid, idx, var),
                daemon=True
            ).start()
            
            chk = customtkinter.CTkCheckBox(
                self.remove_list_frame,
                text=f"Carregando... (ID: {appid})",
                variable=var,
                command=lambda a=appid, v=var: self.toggle_game(a, v)
            )
            chk.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.selected_games[appid] = {"var": var, "widget": chk, "name": None}

    def load_game_name(self, appid, idx, var):
        """Carrega o nome do jogo"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            response = requests.get(url)
            data = response.json()
            name = data.get(appid, {}).get("data", {}).get("name", f"Jogo {appid}")
        except:
            name = f"Jogo {appid}"
        
        self.safe_after(0, self.update_game_name, appid, name, idx, var)

    def update_game_name(self, appid, name, idx, var):
        """Atualiza o nome do jogo na interface"""
        if appid in self.selected_games:
            self.selected_games[appid]["name"] = name
            self.selected_games[appid]["widget"].configure(text=f"{name} (ID: {appid})")

    def toggle_game(self, appid, var):
        """Alterna a seleção de um jogo"""
        self.selected_games[appid]["selected"] = var.get()

    def remove_selected_games(self):
        """Remove os jogos selecionados"""
        selected_appids = [appid for appid, data in self.selected_games.items() 
                      if data.get("selected", False)]
    
        if not selected_appids:
            messagebox.showinfo("Nenhum jogo selecionado", "Selecione pelo menos um jogo para remover")
            return
    
        confirm_window = customtkinter.CTkToplevel(self)
        confirm_window.title("Confirmar Remoção")
        confirm_window.geometry("400x200")
        confirm_window.resizable(False, False)
        confirm_window.transient(self)
        confirm_window.grab_set()
    
        main_frame = customtkinter.CTkFrame(confirm_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
    
        label = customtkinter.CTkLabel(
            main_frame,
            text=f"Tem certeza que deseja remover {len(selected_appids)} jogos?\nEsta ação não pode ser desfeita.",
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        label.pack(pady=(20, 30))
    
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
    
        # Botão Sim (Confirmar)
        confirm_btn = customtkinter.CTkButton(
            button_frame,
            text="Sim",
            command=lambda: [self.run_removal(selected_appids), confirm_window.destroy()],
            width=120,
            fg_color="#d9534f",  # Vermelho para ação destrutiva
            hover_color="#c9302c"
                     
        )
        confirm_btn.grid(row=0, column=0, padx=10)
    
        # Botão Não (Cancelar)
        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Não",
            command=confirm_window.destroy,
            width=120
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    def run_removal(self, appids):
        """Executa o processo de remoção"""
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        
        removed_lua = 0
        removed_manifests = 0
        
        for appid in appids:
            # Remover arquivo .lua
            lua_file = stplug_path / f"{appid}.lua"
            if lua_file.exists():
                try:
                    # Primeiro: tentar a remoção normal pelos appids do arquivo lua
                    ids_manifest = extrair_appids_do_lua(lua_file)
                    if ids_manifest:
                        removed_normal = remover_manifests_por_ids(ids_manifest)
                        removed_manifests += removed_normal
                    
                    # Segundo: tentar remoção agressiva usando o appid principal
                    removed_agressivo = remover_manifests_agressivo(appid)
                    removed_manifests += removed_agressivo
                    
                    # Finalmente remover o arquivo lua
                    lua_file.unlink()
                    removed_lua += 1
                    
                    print(f"Jogo {appid}: {removed_normal + removed_agressivo} manifests removidos")
                    
                except Exception as e:
                    error_msg = f"Erro ao remover {appid}: {str(e)}\n"
                    self.textbox.insert("end", error_msg, "error")
                    print(error_msg)
        
        # Atualizar interface com resultado
        self.safe_after(0, self.update_removal_result, removed_lua, removed_manifests)

    def update_removal_result(self, lua_count, manifest_count):
        """Atualiza a interface com o resultado da remoção"""
        self.textbox.insert("end", 
            f"\n✅ Remoção concluída! "
            f"Arquivos .lua removidos: {lua_count}, "
            f"Manifests removidos: {manifest_count}\n",
            "success"
        )
        self.textbox.see("end")
    
        # Recarregar lista de jogos
        self.load_installed_games()
    
        # Mostrar aviso para reiniciar Steam
        self.safe_after(0, self.show_restart_steam_alert)

    def show_restart_steam_alert(self):
        """Mostra alerta para reiniciar a Steam após remoção"""
        alert_window = customtkinter.CTkToplevel(self)
        alert_window.title("Reiniciar Steam")
        alert_window.geometry("400x200")
        alert_window.resizable(False, False)
        alert_window.transient(self)
        alert_window.grab_set()
    
        main_frame = customtkinter.CTkFrame(alert_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
    
        label = customtkinter.CTkLabel(
            main_frame,
            text="Para as mudanças entrarem em efeito,\né necessário reiniciar a Steam.",
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        label.pack(pady=(20, 30))
    
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
    
        restart_btn = customtkinter.CTkButton(
            button_frame,
            text="Reiniciar Steam",
            command=lambda: [self.restart_steam(), alert_window.destroy()],
            width=120
        )
        restart_btn.grid(row=0, column=0, padx=10)
    
        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Cancelar",
            command=alert_window.destroy,
            width=120
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    # ===== MÉTODOS PARA BACKUP =====

    def select_all_backup(self):
        """Seleciona todos os jogos para backup"""
        for appid, data in self.backup_selected_games.items():
            if "var" in data and data["var"]:
                data["var"].set(True)
                data["selected"] = True

    def select_all_restore(self):
        """Seleciona todos os backups para restauração"""
        for backup_name, data in self.restore_selected_games.items():
            if "var" in data and data["var"]:
                data["var"].set(True)
                data["selected"] = True

    def load_installed_games_for_backup(self):
        """Carrega a lista de jogos instalados para backup"""
        for widget in self.backup_list_frame.winfo_children():
            widget.destroy()
        
        self.backup_selected_games = {}
        
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        if not stplug_path.exists():
            no_games_label = customtkinter.CTkLabel(
                self.backup_list_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        lua_files = list(stplug_path.glob("*.lua"))
        if not lua_files:
            no_games_label = customtkinter.CTkLabel(
                self.backup_list_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        for idx, lua_file in enumerate(lua_files):
            appid = lua_file.stem
            var = tk.BooleanVar(value=False)
            
            threading.Thread(
                target=self.load_game_name_for_backup,
                args=(appid, idx, var),
                daemon=True
            ).start()
            
            chk = customtkinter.CTkCheckBox(
                self.backup_list_frame,
                text=f"Carregando... (ID: {appid})",
                variable=var,
                command=lambda a=appid, v=var: self.toggle_backup_game(a, v)
            )
            chk.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.backup_selected_games[appid] = {"var": var, "widget": chk, "name": None}

    def load_game_name_for_backup(self, appid, idx, var):
        """Carrega o nome do jogo para backup"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            response = requests.get(url)
            data = response.json()
            name = data.get(appid, {}).get("data", {}).get("name", f"Jogo {appid}")
        except:
            name = f"Jogo {appid}"
        
        self.safe_after(0, self.update_game_name_for_backup, appid, name, idx, var)

    def update_game_name_for_backup(self, appid, name, idx, var):
        """Atualiza o nome do jogo na interface de backup"""
        if appid in self.backup_selected_games:
            self.backup_selected_games[appid]["name"] = name
            self.backup_selected_games[appid]["widget"].configure(text=f"{name} (ID: {appid})")

    def toggle_backup_game(self, appid, var):
        """Alterna a seleção de um jogo para backup"""
        self.backup_selected_games[appid]["selected"] = var.get()

    def load_existing_backups(self):
        """Carrega a lista de backups existentes"""
        self.load_restore_list()

    def load_restore_list(self):
        """Carrega a lista de backups existentes para restauração"""
        for widget in self.restore_list_frame.winfo_children():
            widget.destroy()
        
        self.restore_selected_games = {}
        
        if not BACKUP_ROOT.exists():
            no_backups_label = customtkinter.CTkLabel(
                self.restore_list_frame,
                text="Nenhum backup encontrado"
            )
            no_backups_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        backup_folders = [f for f in BACKUP_ROOT.iterdir() if f.is_dir() and f.name.isdigit()]
        if not backup_folders:
            no_backups_label = customtkinter.CTkLabel(
                self.restore_list_frame,
                text="Nenhum backup encontrado"
            )
            no_backups_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        for idx, backup_folder in enumerate(backup_folders):
            appid = backup_folder.name
            var = tk.BooleanVar(value=False)
            
            threading.Thread(
                target=self.load_game_name_for_restore,
                args=(appid, idx, var),
                daemon=True
            ).start()
            
            chk = customtkinter.CTkCheckBox(
                self.restore_list_frame,
                text=f"Carregando... (ID: {appid})",
                variable=var,
                command=lambda a=appid, v=var: self.toggle_restore_game(a, v)
            )
            chk.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.restore_selected_games[appid] = {"var": var, "widget": chk, "name": None}

    def load_game_name_for_restore(self, appid, idx, var):
        """Carrega o nome do jogo para restauração"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            response = requests.get(url)
            data = response.json()
            name = data.get(appid, {}).get("data", {}).get("name", f"Jogo {appid}")
        except:
            name = f"Jogo {appid}"
        
        self.safe_after(0, self.update_game_name_for_restore, appid, name, idx, var)

    def update_game_name_for_restore(self, appid, name, idx, var):
        """Atualiza o nome do jogo na interface de restauração"""
        if appid in self.restore_selected_games:
            self.restore_selected_games[appid]["name"] = name
            self.restore_selected_games[appid]["widget"].configure(text=f"{name} (ID: {appid})")

    def toggle_restore_game(self, appid, var):
        """Alterna a seleção de um jogo para restauração"""
        self.restore_selected_games[appid]["selected"] = var.get()

    def do_backup(self):
        """Executa o backup dos jogos selecionados"""
        selected_appids = [appid for appid, data in self.backup_selected_games.items() 
                          if data.get("selected", False)]
        
        if not selected_appids:
            messagebox.showinfo("Nenhum jogo selecionado", "Selecione pelo menos um jogo para backup")
            return
        
        confirm_window = customtkinter.CTkToplevel(self)
        confirm_window.title("Confirmar Backup")
        confirm_window.geometry("400x200")
        confirm_window.resizable(False, False)
        confirm_window.transient(self)
        confirm_window.grab_set()

        main_frame = customtkinter.CTkFrame(confirm_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        label = customtkinter.CTkLabel(
            main_frame,
            text=f"Tem certeza que deseja fazer backup de {len(selected_appids)} jogos?",
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        label.pack(pady=(20, 30))

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        confirm_btn = customtkinter.CTkButton(
            button_frame,
            text="Sim",
            command=lambda: [self.run_backup(selected_appids), confirm_window.destroy()],
            width=120,
            fg_color="green"
        )
        confirm_btn.grid(row=0, column=0, padx=10)

        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Não",
            command=confirm_window.destroy,
            width=120
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    def run_backup(self, appids):
        """Executa o processo de backup"""
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        depotcache_path = Path(get_steam_path()) / "depotcache"
        
        success_count = 0
        error_count = 0
        
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        
        for appid in appids:
            try:
                backup_folder = BACKUP_ROOT / appid
                backup_folder.mkdir(exist_ok=True)
                
                lua_file = stplug_path / f"{appid}.lua"
                if lua_file.exists():
                    shutil.copy2(lua_file, backup_folder)
                    success_count += 1
                
                ids_manifest = []
                if lua_file.exists():
                    with open(lua_file, "r", encoding="utf-8") as f:
                        conteudo = f.read()
                    ids_manifest = list(set(re.findall(r'addappid\((\d+)', conteudo)))
                
                for manifest_id in ids_manifest:
                    for manifest_path in depotcache_path.glob(f"{manifest_id}_*.manifest"):
                        try:
                            shutil.copy2(manifest_path, backup_folder)
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                
            except Exception as e:
                error_count += 1
        
        messagebox.showinfo("Backup Concluído", 
                           f"Backup concluído com sucesso!\n" 
                           f"Arquivos copiados: {success_count}\n"
                           f"Erros: {error_count}")
        
        self.load_restore_list()

    def do_restore(self):
        """Executa a restauração dos backups selecionados"""
        selected_appids = [appid for appid, data in self.restore_selected_games.items() 
                          if data.get("selected", False)]
        
        if not selected_appids:
            messagebox.showinfo("Nenhum backup selecionado", "Selecione pelo menos um backup para restaurar")
            return
        
        confirm_window = customtkinter.CTkToplevel(self)
        confirm_window.title("Confirmar Restauração")
        confirm_window.geometry("400x200")
        confirm_window.resizable(False, False)
        confirm_window.transient(self)
        confirm_window.grab_set()

        main_frame = customtkinter.CTkFrame(confirm_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        label = customtkinter.CTkLabel(
            main_frame,
            text=f"Tem certeza que deseja restaurar {len(selected_appids)} backups?",
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        label.pack(pady=(20, 30))

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        confirm_btn = customtkinter.CTkButton(
            button_frame,
            text="Sim",
            command=lambda: [self.run_restore(selected_appids), confirm_window.destroy()],
            width=120,
            fg_color="blue"
        )
        confirm_btn.grid(row=0, column=0, padx=10)

        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Não",
            command=confirm_window.destroy,
            width=120
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    def run_restore(self, appids):
        """Executa o processo de restauração"""
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        depotcache_path = Path(get_steam_path()) / "depotcache"
        
        success_count = 0
        error_count = 0
        
        for appid in appids:
            backup_folder = BACKUP_ROOT / appid
            if not backup_folder.exists():
                continue
                
            try:
                lua_file = backup_folder / f"{appid}.lua"
                if lua_file.exists():
                    shutil.copy2(lua_file, stplug_path)
                    success_count += 1
                
                for file in backup_folder.glob("*.manifest"):
                    shutil.copy2(file, depotcache_path)
                    success_count += 1
                
            except Exception as e:
                error_count += 1
        
        messagebox.showinfo("Restauração Concluída", 
                           f"Restauração concluída com sucesso!\n"
                           f"Arquivos restaurados: {success_count}\n"
                           f"Erros: {error_count}")
        
        self.ask_restart_steam_after_restore()

    def ask_restart_steam_after_restore(self):
        """Pergunta se deseja reiniciar a Steam após a restauração"""
        alert_window = customtkinter.CTkToplevel(self)
        alert_window.title("Reiniciar Steam")
        alert_window.geometry("400x200")
        alert_window.resizable(False, False)
        alert_window.transient(self)
        alert_window.grab_set()
        
        main_frame = customtkinter.CTkFrame(alert_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        label = customtkinter.CTkLabel(
            main_frame,
            text="Para as mudanças entrarem em efeito,\né necessário reiniciar a Steam.",
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        label.pack(pady=(20, 30))
        
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        restart_btn = customtkinter.CTkButton(
            button_frame,
            text="Reiniciar Steam",
            command=lambda: [self.restart_steam_after_restore(), alert_window.destroy()],
            width=120
        )
        restart_btn.grid(row=0, column=0, padx=10)
        
        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Cancelar",
            command=alert_window.destroy,
            width=120
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    def restart_steam_after_restore(self):
        """Reinicia a Steam após a restauração"""
        encerrar_steam_processos()
        reiniciar_steam_fechar()
        messagebox.showinfo("Sucesso", "Steam reiniciada com sucesso!")

    # ===== MÉTODOS PARA ATUALIZAÇÃO =====

    def on_update_search_keyrelease(self, event):
        """Filtra a lista de jogos instalados para atualização"""
        search_term = self.update_search_entry.get().strip().lower()
        
        if not search_term:
            for appid, data in self.selected_games.items():
                if "widget" in data and data["widget"].winfo_exists():
                    data["widget"].grid()
            return
        
        for appid, data in self.selected_games.items():
            if "widget" in data and data["widget"].winfo_exists():
                game_name = data.get("name", f"Jogo {appid}").lower()
                if search_term in game_name or search_term in appid:
                    data["widget"].grid()
                else:
                    data["widget"].grid_remove()

    def load_update_games(self):
        """Carrega a lista de jogos instalados para atualização"""
        for widget in self.update_list_frame.winfo_children():
            widget.destroy()
        
        self.selected_games = {}
        
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        if not stplug_path.exists():
            no_games_label = customtkinter.CTkLabel(
                self.update_list_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        lua_files = [f for f in stplug_path.glob("*.lua") if f.stem != "Steamtools"]
        if not lua_files:
            no_games_label = customtkinter.CTkLabel(
                self.update_list_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        for idx, lua_file in enumerate(lua_files):
            appid = lua_file.stem
            
            threading.Thread(
                target=self.load_game_name_for_update,
                args=(appid, idx),
                daemon=True
            ).start()
            
            btn = customtkinter.CTkButton(
                self.update_list_frame,
                text=f"Carregando... (ID: {appid})",
                command=lambda a=appid: self.select_game_for_update(a),
                anchor="w",
                height=30
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=2)
            self.selected_games[appid] = {"widget": btn, "name": None}

    def load_game_name_for_update(self, appid, idx, max_attempts=3, delay=1):
        """Carrega o nome do jogo para atualização com múltiplas tentativas"""
        name = None
        attempt = 0
        
        while attempt < max_attempts and name is None:
            try:
                url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    name = data.get(appid, {}).get("data", {}).get("name")
                    
                    if name:
                        break  # Nome encontrado, sai do loop
                
                # Se chegou aqui, não conseguiu obter o nome
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)  # Delay progressivo
                    
            except requests.exceptions.Timeout:
                print(f"Tentativa {attempt + 1} timeout para appid {appid} (update)")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
            except requests.exceptions.ConnectionError:
                print(f"Tentativa {attempt + 1} erro de conexão para appid {appid} (update)")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
            except requests.exceptions.RequestException as e:
                print(f"Tentativa {attempt + 1} erro na requisição para appid {appid} (update): {e}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
            except Exception as e:
                print(f"Tentativa {attempt + 1} erro inesperado para appid {appid} (update): {e}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
        
        # Se não conseguiu obter o nome após todas as tentativas
        if not name:
            name = f"Jogo {appid}"
            print(f"Falha ao carregar nome do jogo {appid} após {max_attempts} tentativas (update)")
        
        self.safe_after(0, self.update_game_name_for_update, appid, name, idx)

    def update_game_name_for_update(self, appid, name, idx):
        """Atualiza o nome do jogo na interface de atualização"""
        if appid in self.selected_games:
            self.selected_games[appid]["name"] = name
            self.selected_games[appid]["widget"].configure(text=f"{name} (ID: {appid})")

    def select_game_for_update(self, appid):
        """Seleciona um jogo para atualização"""
        if hasattr(self, 'update_selected_game_id') and self.update_selected_game_id and self.update_selected_game_id in self.selected_games:
            self.selected_games[self.update_selected_game_id]["widget"].configure(fg_color=["#3B8ED0", "#1F6AA5"])
        
        self.update_selected_game_id = appid
        self.selected_games[appid]["widget"].configure(fg_color="green")
        
        self.update_textbox.delete("1.0", "end")
        
        game_name = self.selected_games[appid]["name"]
        self.update_textbox.insert("end", f"Jogo selecionado: {game_name} (ID: {appid})\n\n", "info")
        self.update_textbox.insert("end", "Clique em 'Atualizar Selecionado' para verificar e atualizar as keys deste jogo.\n", "info")
        
        self.update_output_redirect.force_scroll()

    def update_selected_game(self):
        """Atualiza as keys do jogo selecionado"""
        if not hasattr(self, 'update_selected_game_id') or not self.update_selected_game_id:
            self.update_textbox.insert("end", "Erro: Nenhum jogo selecionado!\n", "error")
            self.update_output_redirect.force_scroll()
            return
        
        appid = self.update_selected_game_id
        game_name = self.selected_games[appid]["name"]
        
        self.update_textbox.insert("end", f"\nIniciando atualização de {game_name} (ID: {appid})...\n\n", "info")
        self.update_output_redirect.force_scroll()
        
        threading.Thread(
            target=self.run_game_update,
            args=(appid, game_name),
            daemon=True
        ).start()

    def run_game_update(self, appid, game_name):
        """Executa o processo de atualização do jogo"""
        try:
            sys.stdout = self.update_output_redirect
            sys.stderr = self.update_output_redirect
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                from install import atualizar_do_bruhhub
                
                data_recente, total_files, success = loop.run_until_complete(
                    atualizar_do_bruhhub(appid)
                )
                
                if success:
                    self.update_textbox.insert("end", f"\n✅ {game_name} atualizado com sucesso!\n", "success")
                    data_br = formatar_data_brasil(data_recente)
                    self.update_textbox.insert("end", f"📅 Data da atualização: {data_br}\n", "info")
                    self.update_textbox.insert("end", f"📦 Arquivos atualizados: {total_files}\n", "info")
                    
                    self.safe_after(0, self.ask_restart_for_update)
                else:
                    self.update_textbox.insert("end", f"\n❌ Não foi possível atualizar {game_name}\n", "error")
                    self.update_textbox.insert("end", "⚠️ Tente reinstalar o jogo usando outro método\n", "warning")
                    
            except Exception as e:
                error_msg = f"\nErro na atualização: {str(e)}\n"
                self.update_textbox.insert("end", error_msg, "error")
                
        except Exception as e:
            error_msg = f"\nErro no processo de atualização: {str(e)}\n"
            self.update_textbox.insert("end", error_msg, "error")
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            
            self.update_output_redirect.force_scroll()

    def ask_restart_for_update(self):
        """Pergunta sobre reiniciar Steam após atualização"""
        self.update_textbox.insert("end", "\nReiniciar Steam agora para aplicar as atualizações?\n", "info")
        self.update_output_redirect.force_scroll()
        
        for widget in self.update_buttons_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkButton) and widget.cget("text") in ["Reiniciar Steam", "Continuar Atualizando"]:
                widget.destroy()
        
        restart_btn = customtkinter.CTkButton(
            self.update_buttons_frame,
            text="Sim, reiniciar",
            command=lambda: [self.restart_steam_for_update(), self.clear_update_buttons()],
            fg_color="green"
        )
        restart_btn.grid(row=2, column=0, padx=5, pady=5)
        
        continue_btn = customtkinter.CTkButton(
            self.update_buttons_frame,
            text="Não, continuar",
            command=self.clear_update_buttons
        )
        continue_btn.grid(row=2, column=1, padx=5, pady=5)

    def restart_steam_for_update(self):
        """Reinicia a Steam para atualização"""
        self.update_textbox.insert("end", "\nReiniciando Steam...\n", "info")
        self.update_output_redirect.force_scroll()
        encerrar_steam_processos()
        reiniciar_steam_fechar()
        self.update_textbox.insert("end", "✅ Steam reiniciada!\n", "success")
        self.update_output_redirect.force_scroll()

    def clear_update_buttons(self):
        """Limpa os botões adicionais da tela de atualização"""
        for widget in self.update_buttons_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkButton) and widget.cget("text") in [
                "Sim, bloquear", "Não, permitir", "Sim, reiniciar", "Não, continuar"
            ]:
                widget.destroy()

    # ===== MÉTODOS PARA DLCS =====

    def load_installed_games_for_dlc(self):
        """Carrega a lista de jogos instalados para a tela de DLCs"""
        for widget in self.dlc_games_frame.winfo_children():
            widget.destroy()
        
        self.dlc_games = {}
        
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        if not stplug_path.exists():
            no_games_label = customtkinter.CTkLabel(
                self.dlc_games_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        lua_files = [f for f in stplug_path.glob("*.lua") if f.stem != "Steamtools"]
        if not lua_files:
            no_games_label = customtkinter.CTkLabel(
                self.dlc_games_frame,
                text="Nenhum jogo instalado encontrado"
            )
            no_games_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        for idx, lua_file in enumerate(lua_files):
            appid = lua_file.stem
            
            threading.Thread(
                target=self.load_game_name_for_dlc,
                args=(appid, idx),
                daemon=True
            ).start()
            
            btn = customtkinter.CTkButton(
                self.dlc_games_frame,
                text=f"Carregando... (ID: {appid})",
                command=lambda a=appid: self.select_game_for_dlc(a),
                anchor="w",
                height=30
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=2)
            self.dlc_games[appid] = {"widget": btn, "name": None}

    def load_game_name_for_dlc(self, appid, idx, max_attempts=3, delay=1):
        """Carrega o nome do jogo para a tela de DLCs com múltiplas tentativas"""
        name = None
        attempt = 0
        
        while attempt < max_attempts and name is None:
            try:
                url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    name = data.get(appid, {}).get("data", {}).get("name")
                    
                    if name:
                        break  # Nome encontrado, sai do loop
                
                # Se chegou aqui, não conseguiu obter o nome
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)  # Delay progressivo
                    
            except requests.exceptions.Timeout:
                print(f"Tentativa {attempt + 1} timeout para appid {appid}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
            except requests.exceptions.ConnectionError:
                print(f"Tentativa {attempt + 1} erro de conexão para appid {appid}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
            except requests.exceptions.RequestException as e:
                print(f"Tentativa {attempt + 1} erro na requisição para appid {appid}: {e}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
            except Exception as e:
                print(f"Tentativa {attempt + 1} erro inesperado para appid {appid}: {e}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(delay * attempt)
        
        # Se não conseguiu obter o nome após todas as tentativas
        if not name:
            name = f"Jogo {appid}"
            print(f"Falha ao carregar nome do jogo {appid} após {max_attempts} tentativas")
        
        self.safe_after(0, self.update_game_name_for_dlc, appid, name, idx)

    def update_game_name_for_dlc(self, appid, name, idx):
        """Atualiza o nome do jogo na interface de DLCs"""
        if appid in self.dlc_games:
            self.dlc_games[appid]["name"] = name
            self.dlc_games[appid]["widget"].configure(text=f"{name} (ID: {appid})")

    def select_game_for_dlc(self, appid):
        """Seleciona um jogo para carregar suas DLCs"""
        if hasattr(self, 'dlc_selected_game_id') and self.dlc_selected_game_id and self.dlc_selected_game_id in self.dlc_games:
            self.dlc_games[self.dlc_selected_game_id]["widget"].configure(fg_color=["#3B8ED0", "#1F6AA5"])
        
        self.dlc_selected_game_id = appid
        self.dlc_games[appid]["widget"].configure(fg_color="green")
        
        for widget in self.dlc_list_frame.winfo_children():
            widget.destroy()
        
        loading_label = customtkinter.CTkLabel(
            self.dlc_list_frame,
            text="Carregando DLCs...",
            font=customtkinter.CTkFont(size=12)
        )
        loading_label.grid(row=0, column=0, padx=10, pady=10)
        
        threading.Thread(
            target=self.load_dlcs_for_game,
            args=(appid,),
            daemon=True
        ).start()

    def load_dlcs_for_game(self, appid):
        """Carrega as DLCs do jogo selecionado"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                app_data = data.get(str(appid), {}).get('data', {})
                
                if 'dlc' in app_data:
                    dlc_list = app_data['dlc']
                    dlcs = []
                    
                    for dlc_id in dlc_list:
                        dlc_name = self.get_dlc_name_from_steam(dlc_id)
                        dlcs.append({'id': dlc_id, 'name': dlc_name})
                    
                    self.safe_after(0, self.display_dlcs, appid, dlcs)
                else:
                    self.safe_after(0, self.display_dlcs, appid, [])
            else:
                self.safe_after(0, self.display_dlcs_error, f"Erro HTTP: {response.status_code}")
                
        except Exception as e:
            self.safe_after(0, self.display_dlcs_error, f"Erro ao carregar DLCs: {str(e)}")

    def get_dlc_name_from_steam(self, dlc_id):
        """Obtém o nome de uma DLC da API da Steam"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={dlc_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                dlc_data = data.get(str(dlc_id), {}).get('data', {})
                return dlc_data.get('name', f'DLC {dlc_id}')
        except:
            pass
        
        return f'DLC {dlc_id}'

    def display_dlcs(self, appid, dlcs):
        """Exibe as DLCs do jogo selecionado"""
        for widget in self.dlc_list_frame.winfo_children():
            widget.destroy()
        
        if not dlcs:
            no_dlcs_label = customtkinter.CTkLabel(
                self.dlc_list_frame,
                text="Nenhuma DLC encontrada para este jogo.",
                font=customtkinter.CTkFont(size=12)
            )
            no_dlcs_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        self.dlc_selected = {}
        
        for idx, dlc in enumerate(dlcs):
            dlc_id = str(dlc['id'])
            dlc_name = dlc.get('name', f'DLC {dlc_id}')
            
            var = tk.BooleanVar(value=False)
            chk = customtkinter.CTkCheckBox(
                self.dlc_list_frame,
                text=f"{dlc_name} (ID: {dlc_id})",
                variable=var,
                command=lambda d=dlc_id, v=var: self.toggle_dlc(d, v)
            )
            chk.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.dlc_selected[dlc_id] = var

    def display_dlcs_error(self, error_msg):
        """Exibe uma mensagem de erro ao carregar DLCs"""
        for widget in self.dlc_list_frame.winfo_children():
            widget.destroy()
        
        error_label = customtkinter.CTkLabel(
            self.dlc_list_frame,
            text=f"Erro ao carregar DLCs: {error_msg}",
            font=customtkinter.CTkFont(size=12)
        )
        error_label.grid(row=0, column=0, padx=10, pady=10)

    def toggle_dlc(self, dlc_id, var):
        """Alterna a seleção de uma DLC"""
        pass

    def install_selected_dlcs(self):
        """Instala as DLCs selecionadas"""
        if not hasattr(self, 'dlc_selected_game_id') or not self.dlc_selected_game_id:
            messagebox.showerror("Erro", "Nenhum jogo selecionado!")
            return
        
        selected_dlcs = [dlc_id for dlc_id, var in self.dlc_selected.items() if var.get()]
        
        if not selected_dlcs:
            messagebox.showinfo("Nenhuma DLC selecionada", "Selecione pelo menos uma DLC para instalar")
            return
        
        stplug_path = Path(get_steam_path()) / "config" / "stplug-in"
        stplug_path.mkdir(parents=True, exist_ok=True)
        steamtools_file = stplug_path / "Steamtools.lua"
        
        lines = []
        if steamtools_file.exists():
            with open(steamtools_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if any(f"addappid({dlc_id}," in line for dlc_id in selected_dlcs):
                continue
            new_lines.append(line)
        
        for dlc_id in selected_dlcs:
            new_lines.append(f"addappid({dlc_id}, 1)\n")
        
        with open(steamtools_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        messagebox.showinfo("Sucesso", 
                          f"{len(selected_dlcs)} DLC(s) adicionada(s) ao Jogo selecionado!\n\n"
                          f"Reinicie a Steam para que as mudanças tenham efeito.")
        
        self.ask_restart_steam_after_dlc()

    def ask_restart_steam_after_dlc(self):
        """Pergunta se deseja reiniciar a Steam após instalar DLCs"""
        alert_window = customtkinter.CTkToplevel(self)
        alert_window.title("Reiniciar Steam")
        alert_window.geometry("400x200")
        alert_window.resizable(False, False)
        alert_window.transient(self)
        alert_window.grab_set()
        
        main_frame = customtkinter.CTkFrame(alert_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        label = customtkinter.CTkLabel(
            main_frame,
            text="Para as mudanças entrarem em efeito,\né necessário reiniciar a Steam.",
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        label.pack(pady=(20, 30))
        
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        restart_btn = customtkinter.CTkButton(
            button_frame,
            text="Reiniciar Steam",
            command=lambda: [self.restart_steam_after_dlc(), alert_window.destroy()],
            width=120
        )
        restart_btn.grid(row=0, column=0, padx=10)
        
        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Cancelar",
            command=alert_window.destroy,
            width=120
        )
        cancel_btn.grid(row=0, column=1, padx=10)

    def restart_steam_after_dlc(self):
        """Reinicia a Steam após instalar DLCs"""
        encerrar_steam_processos()
        reiniciar_steam_fechar()
        messagebox.showinfo("Sucesso", "Steam reiniciada com sucesso!")

def main():
    # Verificar se o acordo já foi aceito
    acordo_aceito = verificar_acordo_aceito()
    
    if acordo_aceito is None:
        # Exibe a tela de termos e aguarda a resposta
        acordo_aceito = exibir_tela_acordo()
        
        # Salva a decisão do usuário
        salvar_acordo(acordo_aceito)
        
        # Se o usuário não aceitou, encerra o aplicativo
        if not acordo_aceito:
            sys.exit(0)
    
    # Inicializar aplicativo
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
# [file content end]