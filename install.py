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

def formatar_data_brasil(data_iso: str) -> str:
    from datetime import datetime
    try:
        data_obj = datetime.strptime(data_iso.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
        return data_obj.strftime("%d/%m/%Y %H:%M")
    except:
        return data_iso

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

STPLUG_PATH = get_steam_path() / "config" / "stplug-in"
DEPOTCACHE_PATH = get_steam_path() / "depotcache"

ASK_VERSION_LOCK_METODO1 = False
DEFAULT_VERSION_LOCK_METODO1 = True

ASK_VERSION_LOCK_METODO2 = True
DEFAULT_VERSION_LOCK_METODO2 = False

STEAMALL_PATH = get_steam_path() / "Steamall"
STEAMALL_TEMP_PATH = STEAMALL_PATH / "temp"

def criar_diretorio_temp_seguro():
    try:
        STEAMALL_PATH.mkdir(exist_ok=True)
        STEAMALL_TEMP_PATH.mkdir(exist_ok=True)
        temp_dir = STEAMALL_TEMP_PATH / f"temp_{int(time.time())}_{os.urandom(4).hex()}"
        temp_dir.mkdir(exist_ok=True)
        return temp_dir
    except Exception as e:
        print(f"⚠️  Erro ao criar diretório temporário seguro: {e}")
        return Path(tempfile.mkdtemp())

def force_remove_tree(path: Path):
    if not path.exists():
        return
    max_retries = 3
    for retry in range(max_retries):
        try:
            shutil.rmtree(path)
            break
        except PermissionError as e:
            if retry == max_retries - 1:
                try:
                    if os.name == 'nt':
                        subprocess.run(
                            f'rmdir /S /Q "{path}"', 
                            shell=True, 
                            capture_output=True,
                            creationflags=CREATE_NO_WINDOW
                        )
                    else:
                        subprocess.run(
                            f'rm -rf "{path}"', 
                            shell=True, 
                            capture_output=True,
                            creationflags=CREATE_NO_WINDOW
                        )
                except:
                    pass
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️  Erro ao limpar diretório temporário: {e}")
            break

def carregar_repositorios_metodo1() -> list:
    try:
        arquivo_repos = Path("repositorios_m1.json")
        if not arquivo_repos.exists():
            print(f"{VERMELHO}❌ Arquivo repositorios_m1.json não encontrado!{RESET}")
            print(f"{AMARELO}📝 Criando arquivo de exemplo...{RESET}")
            repos_exemplo = ["SPIN0ZAi/SB_manifest_DB"]
            with open(arquivo_repos, 'w', encoding='utf-8') as f:
                json.dump(repos_exemplo, f, indent=2)
            print(f"{VERDE}✅ Arquivo repositorios_m1.json criado com repositório de exemplo.{RESET}")
            return repos_exemplo
        with open(arquivo_repos, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if not conteudo:
            print(f"{VERMELHO}❌ Arquivo repositorios_m1.json está vazio!{RESET}")
            return []
        repos = json.loads(conteudo)
        if not isinstance(repos, list):
            print(f"{VERMELHO}❌ Formato inválido no arquivo repositorios_m1.json!{RESET}")
            return []
        if not repos:
            print(f"{VERMELHO}❌ Nenhum repositório encontrado no arquivo repositorios_m1.json!{RESET}")
            return []
        repo_urls = []
        for repo in repos:
            if isinstance(repo, str) and repo.strip():
                repo = repo.strip()
                if not repo.startswith('http'):
                    repo_urls.append(f"https://github.com/{repo}")
                else:
                    repo_urls.append(repo)
        print(f"{VERDE}✅ Carregados {len(repo_urls)} repositórios para Método 1{RESET}")
        return repo_urls
    except json.JSONDecodeError as e:
        print(f"{VERMELHO}❌ Erro de formatação JSON em repositorios_m1.json: {str(e)}{RESET}")
        print(f"{AMARELO}📝 Verifique se o arquivo tem formato JSON válido.{RESET}")
        return []
    except Exception as e:
        print(f"{VERMELHO}❌ Erro ao carregar repositorios_m1.json: {str(e)}{RESET}")
        return []

def carregar_repositorios_metodo2() -> list:
    try:
        arquivo_repos = Path("repositorios_m2.json")
        if not arquivo_repos.exists():
            print(f"{VERMELHO}❌ Arquivo repositorios_m2.json não encontrado!{RESET}")
            print(f"{AMARELO}📝 Criando arquivo de exemplo...{RESET}")
            repos_exemplo = ["SPIN0ZAi/SB_manifest_DB"]
            with open(arquivo_repos, 'w', encoding='utf-8') as f:
                json.dump(repos_exemplo, f, indent=2)
            print(f"{VERDE}✅ Arquivo repositorios_m2.json criado com repositório de exemplo.{RESET}")
            return repos_exemplo
        with open(arquivo_repos, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if not conteudo:
            print(f"{VERMELHO}❌ Arquivo repositorios_m2.json está vazio!{RESET}")
            return []
        repos = json.loads(conteudo)
        if not isinstance(repos, list):
            print(f"{VERMELHO}❌ Formato inválido no arquivo repositorios_m2.json!{RESET}")
            return []
        if not repos:
            print(f"{VERMELHO}❌ Nenhum repositório encontrado no arquivo repositorios_m2.json!{RESET}")
            return []
        print(f"{VERDE}✅ Carregados {len(repos)} repositórios para Método 2{RESET}")
        return repos
    except json.JSONDecodeError as e:
        print(f"{VERMELHO}❌ Erro de formatação JSON em repositorios_m2.json: {str(e)}{RESET}")
        print(f"{AMARELO}📝 Verifique se o arquivo tem formato JSON válido.{RESET}")
        return []
    except Exception as e:
        print(f"{VERMELHO}❌ Erro ao carregar repositorios_m2.json: {str(e)}{RESET}")
        return []

async def get_branch_latest_commit_date(repo_url: str, branch: str) -> str:
    try:
        parts = repo_url.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            return None
        owner = parts[0]
        repo = parts[1]
        url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADER) as response:
                if response.status == 200:
                    data = await response.json()
                    commit_date = data['commit']['commit']['author']['date']
                    return commit_date
                else:
                    return None
    except Exception as e:
        print(f"Erro ao obter data do branch: {str(e)}")
        return None

async def clone_branch_async(repo_url: str, branch: str, target_dir: Path) -> bool:
    try:
        check_git = await asyncio.create_subprocess_exec(
            'git', '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW
        )
        await check_git.communicate()
        if check_git.returncode != 0:
            return False
        target_dir_str = str(target_dir)
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = ''
        env['SSH_ASKPASS'] = ''
        process = await asyncio.create_subprocess_exec(
            'git', 
            '-c', 'core.askPass=',
            '-c', 'credential.helper=',
            'clone', 
            '--depth', '1',
            '--branch', branch, 
            '--single-branch',
            '--config', 'http.sslVerify=false',
            repo_url, 
            target_dir_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            env=env
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return True
        else:
            return False
    except FileNotFoundError:
        return False
    except Exception as e:
        return False

async def download_branch_files(repo_urls: list, app_id: str, file_extensions: list) -> tuple:
    app_id_str = str(app_id)
    for repo_url in repo_urls:
        temp_dir = criar_diretorio_temp_seguro()
        try:
            success = await clone_branch_async(repo_url, app_id_str, temp_dir)
            if success:
                files = []
                for ext in file_extensions:
                    files.extend(list(temp_dir.rglob(f"*{ext}")))
                if files:
                    return True, temp_dir, len(files), repo_url
                else:
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
            return str(resultados[int(escolha)-1]['id'])

async def baixar_do_bruhhub(app_id: str):
    try:
        BRUHHUB_REPOS = carregar_repositorios_metodo1()
        if not BRUHHUB_REPOS:
            print(f"{VERMELHO}❌ Nenhum repositório disponível para o Método 1.{RESET}")
            return None, None
        print(f"🔍 Procurando keys para o ID: '{app_id}' em nosso repositório...")
        success, temp_dir, total_files, repo_used = await download_branch_files(
            BRUHHUB_REPOS, app_id, ['.lua', '.manifest']
        )
        if not success:
            print(f"❌ No momento não possuimos as keys para o ID: {app_id}")
            print("⚠️ Tente o método 2")
            return None, None
        print(f"\n\n✅ Encontramos {total_files} arquivos para o ID: {app_id}")
        latest_commit_date = None
        if repo_used:
            latest_commit_date = await get_branch_latest_commit_date(repo_used, app_id)
        if not latest_commit_date:
            from datetime import datetime
            latest_commit_date = datetime.now().isoformat()
        depot_map = {}
        lua_files = []
        arquivos = list(temp_dir.rglob("*.lua")) + list(temp_dir.rglob("*.manifest"))
        for idx, arquivo in enumerate(arquivos, 1):
            destino = STPLUG_PATH if arquivo.suffix == '.lua' else DEPOTCACHE_PATH
            os.makedirs(destino, exist_ok=True)
            file_path = destino / arquivo.name
            try:
                shutil.copy2(arquivo, file_path)
                if arquivo.suffix == '.lua':
                    lua_files.append(file_path)
                if arquivo.suffix == '.manifest':
                    filename = arquivo.name
                    depot_id, manifest_id = parse_manifest_filename(filename)
                    if depot_id and manifest_id:
                        if depot_id not in depot_map:
                            depot_map[depot_id] = []
                        depot_map[depot_id].append(manifest_id)
            except Exception as e:
                continue
            progresso = int((idx / len(arquivos)) * 50)
            porcentagem = int((idx / len(arquivos)) * 100)
            print(f"\r[{'=' * progresso}{' ' * (50 - progresso)}] {porcentagem}%", end="", flush=True)
        print("\n")
        for depot_id in depot_map:
            try:
                depot_map[depot_id] = sorted(
                    [manifest for manifest in depot_map[depot_id] if manifest.isdigit()],
                    key=lambda x: int(x),
                    reverse=True
                )
            except ValueError:
                depot_map[depot_id] = sorted(depot_map[depot_id], reverse=True)
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
        force_remove_tree(temp_dir)
        return latest_commit_date, len(arquivos)
    except Exception as e:
        print(f"❌ Erro durante o download: {str(e)}")
        if 'temp_dir' in locals() and temp_dir and temp_dir.exists():
            force_remove_tree(temp_dir)
        return None, None

def parse_manifest_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    base = Path(filename).stem
    parts = base.split('_')
    if len(parts) < 2:
        return None, None
    depot_id = parts[0]
    manifest_id = '_'.join(parts[1:])
    return depot_id, manifest_id

async def fetch_from_cdn(sha: str, path: str, repo: str):
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADER, timeout=30) as resp:
            resp.raise_for_status()
            return await resp.read()

def parse_key_vdf(content: bytes) -> List[Tuple[str, str]]:
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
        progresso = int((idx / total) * 50)
        porcentagem = int((idx / total) * 100)
        print(f"\r[{'=' * progresso}{' ' * (50 - progresso)}] {porcentagem}%", end="", flush=True)
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
        url = "https://api.github.com/rate_limit"
        try:
            async with httpx.AsyncClient() as temp_client:
                r = await temp_client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    r_json = r.json()
                    remaining_requests = r_json.get("rate", {}).get("remaining", 0)
                    print(f"{VERDE} Downloads de keys restantes: {remaining_requests}{RESET}")
                else:
                    print(f"{AMARELO}⚠️  Não foi possível verificar o limite da API GitHub{RESET}")
        except Exception as e:
            LOG.debug(f"Erro ao verificar limite da API GitHub: {e}")
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
                creationflags=CREATE_NO_WINDOW
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
            creationflags=CREATE_NO_WINDOW
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
                creationflags=CREATE_NO_WINDOW
            )
            print("[✓] Steam reiniciada com sucesso:\n")
            print("Proteção contra atualização do APP Steam executado.")
        except Exception as e:
            print(f"[!] Erro ao iniciar a Steam: {e}")
    else:
        print("[!] Caminho da Steam não encontrado.")

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

async def main_flow():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{AZUL}      \n        ╔════════════════════════════════════════════════════════════╗")
        print(f"        ║        {BRANCO}     🚀 INSTALADOR DE KEYS STEAM v4.0               {AZUL}║")
        print(f"        ╚════════════════════════════════════════════════════════════╝{RESET}\n")
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
            if entrada.isdigit():
                appid = entrada
            else:
                appid = await selecionar_jogo_por_nome(entrada)
                if not appid:
                    continue
            nome = verificar_drm(appid)
            if nome:            
                if input("Deseja adicionar este jogo a sua Steam❓ (S/N): ").strip().lower() != "s":
                    print("\n❌ Instalação cancelada.\n")
                    time.sleep(2)
                    continue
            else:
                print("\n⚠️ Nome do jogo não encontrado na Steam. Continuando assim mesmo.")
                time.sleep(1)
            if  escolha == "1":
                data_recente, total = await baixar_do_bruhhub(appid)
                if data_recente:
                    print(f"\n✅ {nome if nome else appid} foi adicionado com sucesso!\n")
                    data_br = formatar_data_brasil(data_recente)
                    print(f"📅 Data da atualização da Key: {VERDE}{data_br}{RESET}")
                    print(f"📦 Total de arquivos baixados: {VERDE}{total}{RESET}\n")
                else:
                    print(f"\n{VERMELHO}❌ Não foi possível encontrar arquivos para {nome if nome else appid}.{RESET}")
                    print(f"{AMARELO}⚠️ Verifique se o jogo existe no metodo 2.{RESET}\n")
            elif escolha == "2":
                repo_usado, data_recente, depot_data, depot_map = await desbloquear_jogo(appid)
                if repo_usado:
                    print(f"\nDeseja bloquear os updates para {nome if nome else appid}?")
                    versionlock = DEFAULT_VERSION_LOCK_METODO2
                    if ASK_VERSION_LOCK_METODO2:
                        escolha_versionlock = input(f"Deseja {VERMELHO}BLOQUEAR{RESET} os UPDATES? (s/n): ").lower()
                        versionlock = (escolha_versionlock == "s")
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
        success, temp_dir, total_files, repo_used = await download_branch_files(
            BRUHHUB_REPOS, app_id, ['.lua', '.manifest']
        )
        if not success:
            return None, None, False
        print(f"\n✅ Encontramos {total_files} arquivos atualizados para o ID: {app_id}")
        latest_commit_date = None
        if repo_used:
            latest_commit_date = await get_branch_latest_commit_date(repo_used, app_id)
        if not latest_commit_date:
            from datetime import datetime
            latest_commit_date = datetime.now().isoformat()
        depot_map = {}
        lua_files = []
        arquivos = list(temp_dir.rglob("*.lua")) + list(temp_dir.rglob("*.manifest"))
        for idx, arquivo in enumerate(arquivos, 1):
            destino = STPLUG_PATH if arquivo.suffix == '.lua' else DEPOTCACHE_PATH
            os.makedirs(destino, exist_ok=True)
            file_path = destino / arquivo.name
            try:
                shutil.copy2(arquivo, file_path)
                if arquivo.suffix == '.lua':
                    lua_files.append(file_path)
                if arquivo.suffix == '.manifest':
                    filename = arquivo.name
                    depot_id, manifest_id = parse_manifest_filename(filename)
                    if depot_id and manifest_id:
                        if depot_id not in depot_map:
                            depot_map[depot_id] = []
                        depot_map[depot_id].append(manifest_id)
            except Exception as e:
                continue
            progresso = int((idx / len(arquivos)) * 50)
            porcentagem = int((idx / len(arquivos)) * 100)
            print(f"\r[{'=' * progresso}{' ' * (50 - progresso)}] {porcentagem}%", end="", flush=True)
        print("\n")
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
                            lines = new_content.split('\n')
                            new_lines = []
                            for line in lines:
                                if not line.strip().startswith(f'setManifestid({depot_id}'):
                                    new_lines.append(line)
                            new_content = '\n'.join(new_lines)
                            new_content += versionlock_cmd
                    if new_content != content:
                        async with aiofiles.open(lua_file, 'w') as f:
                            await f.write(new_content)
                except Exception as e:
                    continue
        force_remove_tree(temp_dir)
        return latest_commit_date, len(arquivos), True
    except Exception as e:
        print(f"❌ Erro durante a atualização: {str(e)}")
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
                break
        except Exception as e:
            print(f"\n{VERMELHO}⚠️ Ocorreu um erro inesperado:{RESET}")
            print(f"{VERMELHO}{traceback.format_exc()}{RESET}")
            print(f"\n{AMARELO}🔄 O programa será reiniciado automaticamente em 5 segundos...{RESET}")
            time.sleep(8)
            continue