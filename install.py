
import tempfile
import shutil
import os
import io
import sys
import time
import asyncio
import aiohttp
import aiofiles
import httpx
import vdf
import subprocess
import requests
import traceback
import json
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Any, Tuple, List, Dict, Optional
from common import log, variable
from config_manager import get_steam_path
from common.variable import CLIENT, HEADER, STEAM_PATH

if os.name == 'nt':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

# Cores ANSI
PRETO = "\033[30m"
VERMELHO = "\033[91m"
VERDE = "\033[92m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
MAGENTA = "\033[95m"
CIANO = "\033[96m"
BRANCO = "\033[97m"
VERMELHO_ESCURO = "\033[31m"
VERDE_ESCURO = "\033[32m"
AMARELO_ESCURO = "\033[33m"
AZUL_ESCURO = "\033[34m"
RESET = "\033[0m"

# Repositórios embutidos diretamente no código
REPOSITORIOS_METODO1 = [
    
    "https://github.com/blumenal/luafastdb"
    "https://github.com/dvahana2424-web/sojogamesdatabase1",
    "https://github.com/SPIN0ZAi/SB_manifest_DB"
]
REPOSITORIOS_METODO2 = [
    "SPIN0ZAi/SB_manifest_DB"
]

def formatar_data_brasil(data_iso: str) -> str:
    """Converte data ISO (ex: '2024-05-20T14:30:00Z') para DD/MM/AAAA HH:MM."""
    from datetime import datetime
    try:
        data_obj = datetime.strptime(data_iso.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
        return data_obj.strftime("%d/%m/%Y %H:%M")  # Formato BR
    except:
        return data_iso  # Mantém o original se falhar

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

STPLUG_PATH = get_steam_path() / "config" / "stplug-in"
DEPOTCACHE_PATH = get_steam_path() / "depotcache"

# Configurações de versionlock por método para controlar se a pergunta sobre versionlock será feita
ASK_VERSION_LOCK_METODO1 = False  # Altere para False para desativar a pergunta
DEFAULT_VERSION_LOCK_METODO1 = True  # Valor padrão quando ASK_VERSION_LOCK1 = False

ASK_VERSION_LOCK_METODO2 = True  # Altere para False para desativar a pergunta
DEFAULT_VERSION_LOCK_METODO2 = False  # Valor padrão quando ASK_VERSION_LOCK2 = False

# --- Diretório temporário personalizado dentro da pasta Steamall ---
STEAMALL_PATH = get_steam_path() / "Steamall"
STEAMALL_TEMP_PATH = STEAMALL_PATH / "temp"

def criar_diretorio_temp_seguro():
    """Cria um diretório temporário seguro dentro da pasta Steamall"""
    try:
        # Garante que a pasta Steamall existe
        STEAMALL_PATH.mkdir(exist_ok=True)
        STEAMALL_TEMP_PATH.mkdir(exist_ok=True)
        
        # Cria um diretório temporário único dentro de Steamall/temp
        temp_dir = STEAMALL_TEMP_PATH / f"temp_{int(time.time())}_{os.urandom(4).hex()}"
        temp_dir.mkdir(exist_ok=True)
        
        return temp_dir
    except Exception as e:
        print(f"⚠️  Erro ao criar diretório temporário seguro: {e}")
        # Fallback para o diretório temporário padrão do sistema
        return Path(tempfile.mkdtemp())

# --- Função auxiliar para limpeza robusta de diretórios ---
def force_remove_tree(path: Path):
    """Remove diretório de forma robusta, lidando com erros de permissão"""
    if not path.exists():
        return
    
    max_retries = 3
    for retry in range(max_retries):
        try:
            # Tenta remover normalmente primeiro
            shutil.rmtree(path)
            break
        except PermissionError as e:
            if retry == max_retries - 1:
                # Tenta método alternativo para Windows
                try:
                    if os.name == 'nt':  # Windows
                        subprocess.run(
                            f'rmdir /S /Q "{path}"', 
                            shell=True, 
                            capture_output=True,
                            creationflags=CREATE_NO_WINDOW  # Adicione esta linha
                        )
                    else:  # Linux/Mac
                        subprocess.run(
                            f'rm -rf "{path}"', 
                            shell=True, 
                            capture_output=True,
                            creationflags=CREATE_NO_WINDOW  # Adicione esta linha
                        )
                except:
                    pass
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️  Erro ao limpar diretório temporário: {e}")
            break

# --- Funções para carregar repositórios embutidos ---
def carregar_repositorios_metodo1() -> list:
    """Carrega repositórios embutidos para o Método 1"""
    return REPOSITORIOS_METODO1

def carregar_repositorios_metodo2() -> list:
    """Carrega repositórios embutidos para o Método 2"""
    return REPOSITORIOS_METODO2

# --- Funções auxiliares para Método 1 (clone Git) ---

async def get_branch_latest_commit_date(repo_url: str, branch: str) -> str:
    """Obtém a data do commit mais recente do branch via API do GitHub"""
    try:
        # Extrai owner e repo da URL
        parts = repo_url.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            return None
            
        owner = parts[0]
        repo = parts[1]
        
        # API do GitHub para obter informações do branch (já inclui o commit mais recente)
        url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADER) as response:
                if response.status == 200:
                    data = await response.json()
                    # Data do commit mais recente no branch
                    commit_date = data['commit']['commit']['author']['date']
                    return commit_date
                else:
                    return None
    except Exception as e:
        return None

async def clone_branch_async(repo_url: str, branch: str, target_dir: Path) -> bool:
    try:
        # Verifica se o git está disponível
        check_git = await asyncio.create_subprocess_exec(
            'git', '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW
        )
        await check_git.communicate()
        if check_git.returncode != 0:
            return False

        # Garante que target_dir é string
        target_dir_str = str(target_dir)
        
        # Configura variáveis de ambiente para evitar prompts de autenticação
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = ''  # Desativa askpass
        env['SSH_ASKPASS'] = ''  # Desativa askpass para SSH
        
        process = await asyncio.create_subprocess_exec(
            'git', 
            '-c', 'core.askPass=',  # Desativa prompt de senha
            '-c', 'credential.helper=',  # Desativa helper de credenciais
            'clone', 
            '--depth', '1',
            '--branch', branch, 
            '--single-branch',
            '--config', 'http.sslVerify=false',  # Opcional: desativa verificação SSL se necessário
            repo_url, 
            target_dir_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            env=env  # Passa as variáveis de ambiente modificadas
        )
        
        stdout, stderr = await process.communicate()
        
        return process.returncode == 0
            
    except FileNotFoundError:
        return False
    except Exception as e:
        return False

async def download_branch_files(repo_urls: list, app_id: str, file_extensions: list) -> tuple:
    """
    Baixa arquivos de um branch usando git clone
    Retorna: (success: bool, temp_dir: Path, file_count: int, repo_used: str)
    """
    # Garante que app_id é string
    app_id_str = str(app_id)
    
    for repo_url in repo_urls:
        # Usa nosso diretório temporário seguro
        temp_dir = criar_diretorio_temp_seguro()
        try:
            success = await clone_branch_async(repo_url, app_id_str, temp_dir)
            
            if success:
                # Conta arquivos com as extensões desejadas
                files = []
                for ext in file_extensions:
                    files.extend(list(temp_dir.rglob(f"*{ext}")))
                
                if files:
                    return True, temp_dir, len(files), repo_url
                else:
                    # Limpa e tenta próximo repositório
                    force_remove_tree(temp_dir)
                    
        except Exception as e:
            if temp_dir.exists():
                force_remove_tree(temp_dir)
            continue
    
    return False, None, 0, None

async def buscar_nome_jogo(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data and str(appid) in data and data[str(appid)]['success']:
                return data[str(appid)]['data']['name']
            return None

async def pesquisar_jogo_por_nome(nome: str) -> List[Dict[str, Any]]:
    """Pesquisa jogos na Steam por nome e retorna lista de resultados."""
    url = "https://store.steampowered.com/api/storesearch"
    params = {
        "term": nome,
        "l": "english",
        "cc": "us"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                return data.get('items', [])
    except Exception:
        return []

async def selecionar_jogo_por_nome(nome: str):
    """Permite ao usuário selecionar um jogo da lista de resultados."""
    resultados = await pesquisar_jogo_por_nome(nome)
    if not resultados:
        print(f"\n{VERMELHO}❌ Nenhum jogo encontrado com o nome '{nome}'.{RESET}")
        return None
    
    print(f"\n{VERDE}🎮 Jogos encontrados:{RESET}\n")
    for idx, jogo in enumerate(resultados, 1):
        print(f"{AZUL}[{idx}]{RESET} {jogo['name']} (ID: {jogo['id']})")
    
    while True:
        escolha = input(f"\n{CIANO}👉 Digite o número do jogo desejado (ou 0 para cancelar):{RESET} ").strip()
        if escolha == "0":
            return None
        if escolha.isdigit() and 1 <= int(escolha) <= len(resultados):
            return str(resultados[int(escolha)-1]['id'])  # Retorna como string para consistência
        print(f"{VERMELHO}❌ Escolha inválida. Tente novamente.{RESET}")

# --- MÉTODO 1: Baixar arquivos prontos (.lua e .manifest) usando clone Git ---
async def baixar_do_bruhhub(app_id: str):
    try:
        BRUHHUB_REPOS = carregar_repositorios_metodo1()
        
        if not BRUHHUB_REPOS:
            print(f"{VERMELHO}❌ Nenhum repositório disponível para o Método 1.{RESET}")
            return None, None
        
        print(f"🔍 Procurando keys para o ID: '{app_id}' em nosso repositório...")
        
        # Usar o método de clone em vez da API
        success, temp_dir, total_files, repo_used = await download_branch_files(
            BRUHHUB_REPOS, app_id, ['.lua', '.manifest']
        )
        
        if not success:
            # Mensagem única e limpa quando não encontra
            print(f"❌ No momento não possuimos as keys para o ID: {app_id}")
            print("⚠️ Tente o método 2")
            return None, None
        
        print(f"\n\n✅ Encontramos {total_files} arquivos para o ID: {app_id}")
        
        # OBTER DATA DO COMMIT MAIS RECENTE DO BRANCH (NOVA IMPLEMENTAÇÃO)
        latest_commit_date = None
        if repo_used:
            latest_commit_date = await get_branch_latest_commit_date(repo_used, app_id)
        
        # Se não conseguiu a data do commit, usa a data atual como fallback
        if not latest_commit_date:
            from datetime import datetime
            latest_commit_date = datetime.now().isoformat()
        
        # Resto do código permanece igual...
        # Estruturas para coletar informações necessárias para o versionlock
        depot_map = {}
        lua_files = []
        
        # Encontrar todos os arquivos .lua e .manifest
        arquivos = list(temp_dir.rglob("*.lua")) + list(temp_dir.rglob("*.manifest"))
        
        for idx, arquivo in enumerate(arquivos, 1):
            destino = STPLUG_PATH if arquivo.suffix == '.lua' else DEPOTCACHE_PATH
            os.makedirs(destino, exist_ok=True)
            file_path = destino / arquivo.name
            
            # Copiar arquivo
            try:
                shutil.copy2(arquivo, file_path)
                
                # Registrar arquivos .lua
                if arquivo.suffix == '.lua':
                    lua_files.append(file_path)
                
                # Processar manifestos para versionlock
                if arquivo.suffix == '.manifest':
                    filename = arquivo.name
                    depot_id, manifest_id = parse_manifest_filename(filename)
                    if depot_id and manifest_id:
                        if depot_id not in depot_map:
                            depot_map[depot_id] = []
                        depot_map[depot_id].append(manifest_id)
            except Exception as e:
                continue
            
            # Barra de progresso
            progresso = int((idx / len(arquivos)) * 50)
            porcentagem = int((idx / len(arquivos)) * 100)
            print(f"\r[{'=' * progresso}{' ' * (50 - progresso)}] {porcentagem}%", end="", flush=True)
        
        print("\n")
        
        # Ordenar manifestos (código existente)
        for depot_id in depot_map:
            try:
                depot_map[depot_id] = sorted(
                    [manifest for manifest in depot_map[depot_id] if manifest.isdigit()],
                    key=lambda x: int(x),
                    reverse=True
                )
            except ValueError:
                depot_map[depot_id] = sorted(depot_map[depot_id], reverse=True)
        
        # Versionlock (código existente)
        versionlock = DEFAULT_VERSION_LOCK_METODO1
        if ASK_VERSION_LOCK_METODO1:
            escolha = input(f"Deseja {VERMELHO}BLOQUEAR{RESET} os UPDATES? (s/n): ").lower()
            versionlock = (escolha == "s")
        
        if versionlock:
            for lua_file in lua_files:
                try:
                    async with aiofiles.open(lua_file, 'r') as f:
                        content = await f.read()
                    
                    new_content = content
                    for depot_id, manifest_ids in depot_map.items():
                        if manifest_ids:
                            latest_manifest = manifest_ids[0]
                            versionlock_cmd = f'\nsetManifestid({depot_id},"{latest_manifest}")'
                            
                            if f'setManifestid({depot_id}' not in new_content:
                                new_content += versionlock_cmd
                    
                    if new_content != content:
                        async with aiofiles.open(lua_file, 'w') as f:
                            await f.write(new_content)
                except Exception as e:
                    continue
        
        # Limpar diretório temporário de forma segura
        force_remove_tree(temp_dir)
        
        # Retornar data do commit mais recente (em vez da data atual)
        return latest_commit_date, len(arquivos)
        
    except Exception as e:
        print(f"❌ Erro durante o download: {str(e)}")
        # Garantir que o diretório temporário seja limpo mesmo em caso de erro
        if 'temp_dir' in locals() and temp_dir and temp_dir.exists():
            force_remove_tree(temp_dir)
        return None, None

# --- MÉTODO 2: Exatamente igual ao install_old.py (usando API GitHub) ---

# Função auxiliar para extrair depot_id e manifest_id do nome do arquivo
def parse_manifest_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrai depot_id e manifest_id do nome do arquivo de manifesto."""
    base = Path(filename).stem  # Remove a extensão
    parts = base.split('_')
    if len(parts) < 2:
        return None, None
    depot_id = parts[0]
    manifest_id = '_'.join(parts[1:])  # Juntar o resto caso tenha more underscores
    return depot_id, manifest_id

async def fetch_from_cdn(sha: str, path: str, repo: str):
    """Função auxiliar para baixar um arquivo do CDN do GitHub."""
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADER, timeout=30) as resp:
            resp.raise_for_status()
            return await resp.read()

def parse_key_vdf(content: bytes) -> List[Tuple[str, str]]:
    """Analisa o conteúdo de um arquivo key.vdf e retorna lista de (depot_id, key)"""
    try:
        depots = vdf.loads(content.decode("utf-8"))['depots']
        return [(d_id, d_info['DecryptionKey']) for d_id, d_info in depots.items()]
    except Exception as e:
        log.log("LuaFast").error(f"Erro parseando chave: {e}")
        return []

async def handle_depot_files(repos: List, app_id: str, steam_path: Path, repo: str):
    coletados = []
    mapa_depot = {}
    
    url = f"https://api.github.com/repos/{repo}/branches/{app_id}"
    r = await CLIENT.get(url, headers=HEADER)
    tree_url = r.json()["commit"]["commit"]["tree"]["url"]
    tree_res = await CLIENT.get(tree_url, headers=HEADER)
    
    arquivos = [item for item in tree_res.json()["tree"] 
               if item["path"].endswith(".manifest") or "key.vdf" in item["path"].lower()]
    total = len(arquivos)
    
    if total == 0:
        print("Nenhum arquivo encontrado para download.")
        return coletados, mapa_depot
        
    for idx, item in enumerate(arquivos, 1):
        path = item["path"]
        
        if path.endswith(".manifest"):
            caminho_salvar = steam_path / "depotcache" / Path(path).name
            os.makedirs(caminho_salvar.parent, exist_ok=True)
            
            if not caminho_salvar.exists():
                try:
                    conteudo = await fetch_from_cdn(r.json()["commit"]["sha"], path, repo)
                    async with aiofiles.open(caminho_salvar, "wb") as f:
                        await f.write(conteudo)
                    
                    depot_id, manifest_id = parse_manifest_filename(path)
                    if depot_id and manifest_id:
                        mapa_depot.setdefault(depot_id, []).append(manifest_id)
                except Exception:
                    pass
        
        elif "key.vdf" in path.lower():
            try:
                conteudo = await fetch_from_cdn(r.json()["commit"]["sha"], path, repo)
                novas_chaves = parse_key_vdf(conteudo)
                coletados.extend(novas_chaves)
            except Exception:
                pass

        # Barra de progresso melhorada
        progresso = int((idx / total) * 50)  # 50 caracteres de largura
        porcentagem = int((idx / total) * 100)
        print(f"\r[{'=' * progresso}{' ' * (50 - progresso)}] {porcentagem}%", end="", flush=True)
    
    # Ordenar manifestos
    for depot_id in mapa_depot:
        try:
            mapa_depot[depot_id] = sorted(mapa_depot[depot_id], key=lambda x: int(x), reverse=True)
        except ValueError:
            pass
            
    return coletados, mapa_depot

async def desbloquear_jogo(app_id: str):
    LOG = log.log("LuaFast")

    def stack_error(exception: Exception) -> str:
        return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

    async def check_github_api_rate_limit(headers):
        """Verifica o limite de requisições da API do GitHub de forma robusta"""
        url = "https://api.github.com/rate_limit"
        try:
            # Usar um cliente temporário para evitar problemas de conexão
            async with httpx.AsyncClient() as temp_client:
                r = await temp_client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    r_json = r.json()
                    remaining_requests = r_json.get("rate", {}).get("remaining", 0)
                    print(f"{VERDE} Downloads de keys restantes: {remaining_requests}{RESET}")
                else:
                    print(f"{AMARELO}⚠️  Não foi possível verificar o limite da API GitHub{RESET}")
        except Exception as e:
            # Log mais silencioso para evitar poluição visual
            LOG.debug(f"Erro ao verificar limite da API GitHub: {e}")
            # Não mostra o erro completo para o usuário

    async def get_latest_repo_info(repos: list, app_id: str, headers):
        data_mais_recente = None
        repo_selecionado = None
        for repo in repos:
            try:
                url = f"https://api.github.com/repos/{repo}/branches/{app_id}"
                r = await CLIENT.get(url, headers=headers, timeout=30.0)
                if r.status_code == 200 and "commit" in r.json():
                    data = r.json()["commit"]["commit"]["author"]["date"]
                    if (data_mais_recente is None) or (data > data_mais_recente):
                        data_mais_recente = str(data)
                        repo_selecionado = str(repo)
            except Exception as e:
                # Continua para o próximo repositório em caso de erro
                continue
        return repo_selecionado, data_mais_recente

    try:
        REPO_LIST = carregar_repositorios_metodo2()
        if not REPO_LIST:
            print(f"{VERMELHO}❌ Nenhum repositório disponível para o Método 2.{RESET}")
            return None, None, None, None
            
        await check_github_api_rate_limit(HEADER)
        repo_usado, data_recente = await get_latest_repo_info(REPO_LIST, app_id, HEADER)
            
        if not repo_usado:
            return None, None, None, None
        
        depot_data, depot_map = await handle_depot_files(REPO_LIST, app_id, STEAM_PATH, repo_usado)
        return repo_usado, data_recente, depot_data, depot_map
        
    except Exception as e:
        print(f"{VERMELHO}❌ Erro ao acessar repositórios GitHub: {str(e)}{RESET}")
        return None, None, None, None

async def apply_versionlock_decision(app_id: str, versionlock: bool, depot_data, depot_map):
    """Aplica a decisão do usuário sobre o versionlock"""
    st_path = STEAM_PATH / "config" / "stplug-in"
    st_path.mkdir(exist_ok=True)
    
    conteudo = f'addappid({app_id}, 1, "None")\n'
    for d_id, d_key in depot_data:
        if versionlock:
            if d_id in depot_map and depot_map[d_id]:
                latest_manifest = depot_map[d_id][0]
                conteudo += f'addappid({d_id}, 1, "{d_key}")\nsetManifestid({d_id},"{latest_manifest}")\n'
        else:
            conteudo += f'addappid({d_id}, 1, "{d_key}")\n'
    
    async with aiofiles.open(st_path / f"{app_id}.lua", "w") as f:
        await f.write(conteudo)
    
    return True

def verificar_drm(appid):
    def buscar_drm_steam_store(appid):
        def extrair_drm(texto):
            texto = texto.lower()
            drm = set()
            if "denuvo" in texto:
                drm.add("Denuvo")
            if "steamworks" in texto or "requires steam" in texto or "necessita do steam" in texto:
                drm.add("Steamworks")
            if "third-party drm" in texto or "3rd-party drm" in texto or "drm de terceiros" in texto:
                drm.add("Third-party DRM")
            return drm

        try:
            drm_total = set()
            url_en = f"https://store.steampowered.com/app/{appid}/?cc=us&l=en"
            response_en = requests.get(url_en, headers=HEADERS)
            if response_en.status_code == 200:
                soup_en = BeautifulSoup(response_en.text, "html.parser")
                drm_total.update(extrair_drm(soup_en.get_text()))

            url_pt = f"https://store.steampowered.com/app/{appid}/"
            response_pt = requests.get(url_pt, headers=HEADERS)
            if response_pt.status_code == 200:
                soup_pt = BeautifulSoup(response_pt.text, "html.parser")
                drm_total.update(extrair_drm(soup_pt.get_text()))

            return ", ".join(sorted(drm_total)) if drm_total else "Não especificado"

        except Exception:
            return "Não especificado"

    def get_steam_game_info(appid):
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException:
            return {"appid": appid, "error": "Erro ao acessar a Steam API."}

        data = response.json()
        game_data = data.get(str(appid), {}).get("data")
        if not game_data:
            return {"appid": appid, "error": "Jogo não encontrado."}

        name = game_data.get("name", "Desconhecido")
        about = game_data.get("about_the_game", "")
        detailed = game_data.get("detailed_description", "")
        drm = []

        about_lower = about.lower()
        detailed_lower = detailed.lower()

        if "denuvo" in about_lower or "denuvo" in detailed_lower:
            drm.append("Denuvo")
        if "third-party drm" in about_lower or "3rd-party drm" in about_lower:
            drm.append("Third-party DRM")
        if "steamworks" in about_lower or "requires steam" in about_lower:
            drm.append("Steamworks")

        drm_info = ", ".join(drm) if drm else buscar_drm_steam_store(appid)

        return {"appid": appid, "name": name, "drm": drm_info}

    info = get_steam_game_info(appid)
    if "error" in info:
        print(f"\n❌ [{appid}] ERRO: {info['error']}")
        return

    print(f"\n📌 AppID: {appid}")
    print(f"🎮 Nome : {info['name']}")
    print(f"🔐 DRM  : {info['drm']}")

    
    drm_text = info['drm'].lower()
    if "denuvo" in drm_text:
        print("🚫 Situação: ❌ O jogo não funciona atualmente (Denuvo), mas pode funcionar no futuro.\n")
    elif "steamworks" in drm_text and ("third-party" in drm_text or "," in drm_text):
        print("⚠️ Situação: ⚠️ O jogo talvez funcione (Steamworks + outro DRM).\n")
    elif "steamworks" in drm_text:
        print("✅ Situação: ✔️ O jogo deve funcionar normalmente.\n")
    elif drm_text in ["", "não especificado"]:
        print("✅ Situação: ✔️ O jogo deve funcionar (sem DRM detectado).\n")
    else:
        print("❓ Situação: ❓ DRM não identificado claramente. Talvez funcione.\n")
    return info['name']

def encerrar_e_reiniciar_steam():
    processos_steam = [
        "Steam.exe",
        "steamwebhelper.exe",
        "GameOverlayUI.exe",
        "SteamService.exe",
        "steamerrorreporter.exe",
        "steamstart.exe",
        "steamguard.exe"
    ]

    print("[*] Encerrando processos da Steam...\n")
    for processo in processos_steam:
        try:
            print(f"[-] Encerrando {processo}...")
            subprocess.run(
                ["taskkill", "/F", "/IM", processo], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW  # Adicione esta linha
            )
        except Exception as e:
            print(f"[!] Erro ao encerrar {processo}: {e}")

    time.sleep(2)

    print("\n[*] Verificando se ainda há processos ativos...")
    try:
        output = subprocess.check_output(
            "tasklist", 
            shell=True, 
            encoding="mbcs",
            creationflags=CREATE_NO_WINDOW  # Adicione esta linha
        ).lower()
        processos_ativos = [p for p in processos_steam if p.lower() in output]

        if processos_ativos:
            print("[!] Ainda existem processos ativos:")
            for p in processos_ativos:
                print(f"    - {p}")
        else:
            print("[✓] Todos os processos da Steam foram encerrados.")
    except Exception as e:
        print(f"[!] Erro ao verificar processos: {e}")

    print("\n[*] Reiniciando a Steam com parâmetros otimizados...")
    caminho_steam = STEAM_PATH / "Steam.exe"
    if os.path.exists(caminho_steam):
        try:
            subprocess.Popen(
                [str(caminho_steam), "-noverifyfiles", "-nobootstrapupdate", 
                 "-skipinitialbootstrap", "-norepairfiles", "-console"],
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW  # Adicione esta linha
            )
            print("[✓] Steam reiniciada com sucesso:\n")
            print("Proteção contra atualização do APP Steam executado.")
        except Exception as e:
            print(f"[!] Erro ao iniciar a Steam: {e}")
    else:
        print("[!] Caminho da Steam não encontrado.")

# --- Nova função para adicionar múltiplos IDs ---
async def instalar_multiplos_ids():
    print(f"\n{AMARELO}🎮 Digite os IDs que deseja adicionar (separados por espaço):{RESET}\n")
    ids_input = input().strip()
    ids = ids_input.split()
    
    if not ids:
        print(f"{VERMELHO}❌ Nenhum ID fornecido.{RESET}")
        return
    
    for appid in ids:
        appid = appid.strip()
        if not appid.isdigit():
            print(f"{VERMELHO}❌ ID inválido: {appid}. Pulando...{RESET}")
            continue
            
        print(f"\n{AZUL}════════════════════════════════════════════════════════════{RESET}")
        print(f"{VERDE}🔍 Processando ID: {appid}{RESET}")
        
        nome = verificar_drm(appid)
        if not nome:
            print(f"{VERMELHO}⚠️ Nome do jogo não encontrado na Steam. Continuando assim mesmo.{RESET}")
            nome = appid
            
        try:
            repo_usado, data_recente, depot_data, depot_map = await desbloquear_jogo(appid)
            if repo_usado:
                print(f"✅ O game {nome if nome else appid} foi adicionado com sucesso!\n")
                data_br = formatar_data_brasil(data_recente)
                print(f"📅 Data da atualização da Key: {VERDE}{data_br}{RESET}\n")
              
            else:
                print(f"\n{VERMELHO}❌ Não foi possível encontrar arquivos para {nome if nome else appid}.{RESET}\n")
        except Exception as e:
            print(f"{VERMELHO}❌ Erro ao adicionar {nome}: {str(e)}{RESET}")
            continue

# --- Menu principal ---
async def main_flow():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Cabeçalho decorativo
        print(f"{AZUL}      \n        ╔════════════════════════════════════════════════════════════╗")
        print(f"        ║        {BRANCO}     🚀 INSTALADOR DE KEYS STEAM v4.0               {AZUL}║")
        print(f"        ╚════════════════════════════════════════════════════════════╝{RESET}\n")

        # Informações explicativas
        print(f"{VERDE}       📢 Escolha o servidor de onde será feito o download das keys. {RESET}\n")

        print(f"{AZUL}                ╔════════════════════════════════════════════╗")
        print(f"                ║  {AMARELO}[1]{RESET} Servidor de Keys 1                    {AZUL}║")
        print(f"                ╚════════════════════════════════════════════╝{RESET}")
        print(f"{AZUL}                ╔════════════════════════════════════════════╗")
        print(f"                ║  {CIANO}[2]{RESET} Servidor de Keys 2                    {AZUL}║")
        print(f"                ╚════════════════════════════════════════════╝{RESET}")
        print(f"{AZUL}                ╔════════════════════════════════════════════╗")
        print(f"                ║  {VERMELHO}[0]{RESET} Voltar para o menu principal          {AZUL}║")
        print(f"                ║  {VERMELHO}[00]{RESET} Sair do programa                     {AZUL}║")
        print(f"                ╚════════════════════════════════════════════╝{RESET}")

        escolha = input(f"\n{CIANO}👉 Digite sua escolha: {RESET}").strip().lower()
        
        if escolha == "00":
            print(f"\n{VERMELHO}❌ Encerrando o programa...{RESET}")
            time.sleep(1)
            sys.exit()
        
        if escolha == "0":
            return "voltar"
            
        if escolha not in ["1", "2"]:
            print(f"\n{VERMELHO}❗ Escolha inválida. Tente novamente.{RESET}")
            time.sleep(2)
            continue

        if escolha == "4":
            await instalar_multiplos_ids()
        else:
            entrada = input(f"\n{AMARELO}🔎 Digite o ID ou nome do jogo:{RESET} ").strip()
            
            # Se for apenas dígitos, assume que é um AppID
            if entrada.isdigit():
                appid = entrada
            else:
                # Se não for apenas dígitos, assume que é um nome e faz a pesquisa
                appid = await selecionar_jogo_por_nome(entrada)
                if not appid:
                    continue  # Volta ao menu se não selecionou um jogo

            nome = verificar_drm(appid) # Faz a verificação de DRM
            if nome:            
                if input("Deseja adicionar este jogo a sua Steam❓ (S/N): ").strip().lower() != "s":
                    print("\n❌ Instalação cancelada.\n")
                    time.sleep(2)
                    continue
            else:
                print("\n⚠️ Nome do jogo não encontrado na Steam. Continuando assim mesmo.")
                time.sleep(1)
                     
            if  escolha == "1": #Servidor de arquivos prontos, baixa o .lua e os .manifast
                data_recente, total = await baixar_do_bruhhub(appid)
                if data_recente:
                    print(f"\n✅ {nome if nome else appid} foi adicionado com sucesso!\n")
                    data_br = formatar_data_brasil(data_recente)
                    print(f"📅 Data da atualização da Key: {VERDE}{data_br}{RESET}")
                    print(f"📦 Total de arquivos baixados: {VERDE}{total}{RESET}\n")
                else:
                    print(f"\n{VERMELHO}❌ Não foi possível encontrar arquivos para {nome if nome else appid}.{RESET}")
                    print(f"{AMARELO}⚠️ Verifique se o jogo existe no metodo 2.{RESET}\n")

            elif escolha == "2": #Servidor de keys, depois cria o .lua
                repo_usado, data_recente, depot_data, depot_map = await desbloquear_jogo(appid)
                
                if repo_usado:
                    # Exibir pergunta sobre bloquear updates
                    print(f"\nDeseja bloquear os updates para {nome if nome else appid}?")
                    
                    # Mostrar botões de decisão
                    versionlock = DEFAULT_VERSION_LOCK_METODO2
                    if ASK_VERSION_LOCK_METODO2:
                        escolha_versionlock = input(f"Deseja {VERMELHO}BLOQUEAR{RESET} os UPDATES? (s/n): ").lower()
                        versionlock = (escolha_versionlock == "s")
                    
                    # Aplicar a decisão do versionlock
                    success = await apply_versionlock_decision(appid, versionlock, depot_data, depot_map)
                    if success:
                        print(f"\n✅ {nome if nome else appid} foi adicionado com sucesso!\n")
                        data_br = formatar_data_brasil(data_recente)
                        print(f"📅 Data da atualização da Key: {VERDE}{data_br}{RESET}\n")
                    else:
                        print(f"\n{VERMELHO}❌ Erro ao aplicar versionlock para {nome if nome else appid}.{RESET}\n")
                else:
                    print(f"\n{VERMELHO}❌ Não foi possível encontrar arquivos para {nome if nome else appid}.{RESET}\n")

        if input("\nDeseja adicionar mais jogos a sua Steam❓ (S/N): ").strip().lower() != "s":
            if input("Deseja reiniciar a Steam agora❓ (S/N): ").strip().lower() == "s":
                encerrar_e_reiniciar_steam()
                print("✅ Steam reiniciada com sucesso!")
            break
async def atualizar_do_bruhhub(app_id: str):

    try:
        BRUHHUB_REPOS = carregar_repositorios_metodo1()
        
        print(f"🔍 Procurando atualizações para o ID: '{app_id}' em nosso repositório...")
        
        # Usar o método de clone em vez da API
        success, temp_dir, total_files, repo_used = await download_branch_files(
            BRUHHUB_REPOS, app_id, ['.lua', '.manifest']
        )
        
        if not success:
            return None, None, False
        
        print(f"\n✅ Encontramos {total_files} arquivos atualizados para o ID: {app_id}")
        
        # OBTER DATA DO COMMIT MAIS RECENTE DO BRANCH
        latest_commit_date = None
        if repo_used:
            latest_commit_date = await get_branch_latest_commit_date(repo_used, app_id)
        
        # Se não conseguiu a data do commit, usa a data atual como fallback
        if not latest_commit_date:
            from datetime import datetime
            latest_commit_date = datetime.now().isoformat()
        
        # Estruturas para coletar informações necessárias
        depot_map = {}
        lua_files = []
        
        # Encontrar todos os arquivos .lua e .manifest
        arquivos = list(temp_dir.rglob("*.lua")) + list(temp_dir.rglob("*.manifest"))
        
        for idx, arquivo in enumerate(arquivos, 1):
            destino = STPLUG_PATH if arquivo.suffix == '.lua' else DEPOTCACHE_PATH
            os.makedirs(destino, exist_ok=True)
            file_path = destino / arquivo.name
            
            # Copiar arquivo (sobrescreve se existir)
            try:
                shutil.copy2(arquivo, file_path)
                
                # Registrar arquivos .lua
                if arquivo.suffix == '.lua':
                    lua_files.append(file_path)
                
                # Processar manifestos
                if arquivo.suffix == '.manifest':
                    filename = arquivo.name
                    depot_id, manifest_id = parse_manifest_filename(filename)
                    if depot_id and manifest_id:
                        if depot_id not in depot_map:
                            depot_map[depot_id] = []
                        depot_map[depot_id].append(manifest_id)
            except Exception as e:
                continue
            
            # Barra de progresso
            progresso = int((idx / len(arquivos)) * 50)
            porcentagem = int((idx / len(arquivos)) * 100)
            print(f"\r[{'=' * progresso}{' ' * (50 - progresso)}] {porcentagem}%", end="", flush=True)
        
        print("\n")
        
        # NA ATUALIZAÇÃO, SEMPRE APLICAMOS VERSIONLOCK PARA MANTER A VERSÃO MAIS RECENTE
        # Isso evita que o Steam atualize para uma versão mais nova que pode quebrar as keys
        versionlock = True
        
        if versionlock:
            for lua_file in lua_files:
                try:
                    async with aiofiles.open(lua_file, 'r') as f:
                        content = await f.read()
                    
                    new_content = content
                    for depot_id, manifest_ids in depot_map.items():
                        if manifest_ids:
                            latest_manifest = manifest_ids[0]
                            versionlock_cmd = f'\nsetManifestid({depot_id},"{latest_manifest}")'
                            
                            # Remove comandos de versionlock existentes para este depot
                            lines = new_content.split('\n')
                            new_lines = []
                            for line in lines:
                                if not line.strip().startswith(f'setManifestid({depot_id}'):
                                    new_lines.append(line)
                            new_content = '\n'.join(new_lines)
                            
                            # Adiciona o novo comando de versionlock
                            new_content += versionlock_cmd
                    
                    if new_content != content:
                        async with aiofiles.open(lua_file, 'w') as f:
                            await f.write(new_content)
                except Exception as e:
                    continue
        
        # Limpar diretório temporário de forma segura
        force_remove_tree(temp_dir)
        
        # Retornar data do commit mais recente e total de arquivos
        return latest_commit_date, len(arquivos), True
        
    except Exception as e:
        print(f"❌ Erro durante a atualização: {str(e)}")
        # Garantir que o diretório temporário seja limpo mesmo em caso de erro
        if 'temp_dir' in locals() and temp_dir and temp_dir.exists():
            force_remove_tree(temp_dir)
        return None, None, False                                            

if __name__ == "__main__":
    while True:
        try:
            resultado = asyncio.run(main_flow())
            if resultado == "voltar":
                import subprocess
                subprocess.run(["python", "main.py"])
                break
            else:
                break  # Sai do loop se main_flow() terminar sem erros
        except Exception as e:
            print(f"\n{VERMELHO}⚠️ Ocorreu um erro inesperado:{RESET}")
            print(f"{VERMELHO}{traceback.format_exc()}{RESET}")
            print(f"\n{AMARELO}🔄 O programa será reiniciado automaticamente em 5 segundos...{RESET}")
            time.sleep(8)
            continue  # Reinicia o loop e o programa
