# remove.py
import asyncio
import os
import re
import httpx
from pathlib import Path
from typing import List
from main import get_steam_path  # Importa a função do main.py

# Cores ANSI
VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
CIANO = "\033[96m"
RESET = "\033[0m"

def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")

def mostrar_cabecalho():
    limpar_tela()
    print(f"{AZUL}╔════════════════════════════════════════════════════════╗")
    print(f"║          🎮 REMOVER GAMES DA CONTA STEAM 🎮            ║")
    print(f"╚════════════════════════════════════════════════════════╝{RESET}")
    print(f"Diretório da Steam: {VERDE}{get_steam_path()}{RESET}\n")

def get_stplug_path():
    """Retorna o caminho para a pasta stplug-in"""
    return get_steam_path() / "config" / "stplug-in"

def get_depotcache_path():
    """Retorna o caminho para a pasta depotcache"""
    return get_steam_path() / "depotcache"

def remover_todos_arquivos():
    """Remove TODOS os arquivos das duas pastas (sem verificação de IDs)"""
    stplug_path = get_stplug_path()
    depotcache_path = get_depotcache_path()
    
    # Remove todos os .lua
    lua_removidos = 0
    if stplug_path.exists():
        for arquivo in stplug_path.glob("*.lua"):
            try:
                arquivo.unlink()
                lua_removidos += 1
            except Exception as e:
                print(f"{VERMELHO}Erro ao remover {arquivo.name}: {e}{RESET}")
    
    # Remove todos os .manifest
    manifest_removidos = 0
    if depotcache_path.exists():
        for arquivo in depotcache_path.glob("*.manifest"):
            try:
                arquivo.unlink()
                manifest_removidos += 1
            except Exception as e:
                print(f"{VERMELHO}Erro ao remover {arquivo.name}: {e}{RESET}")
    
    return lua_removidos, manifest_removidos

def extrair_appids_do_lua(lua_path: Path) -> List[str]:
    """Extrai IDs para remoção específica de forma mais robusta"""
    try:
        with open(lua_path, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()
        
        # Padrões para encontrar appids no arquivo lua
        padroes = [
            r'addappid\(\s*(\d+)\s*,',  # addappid(12345,
            r'appid\s*=\s*(\d+)',        # appid = 12345
            r'["\']?appid["\']?\s*:\s*["\']?(\d+)["\']?',  # "appid": "12345"
        ]
        
        appids_encontrados = []
        for padrao in padroes:
            appids_encontrados.extend(re.findall(padrao, conteudo))
        
        return list(set(appids_encontrados))  # Remover duplicatas
    except Exception as e:
        print(f"{VERMELHO}Erro ao ler arquivo {lua_path.name}: {e}{RESET}")
        return []

def remover_manifests_agressivo(appid):
    """Tenta remover manifests de forma mais agressiva"""
    depotcache_path = Path(get_steam_path()) / "depotcache"
    removidos = 0
    
    if not depotcache_path.exists():
        return removidos
    
    # Tentar vários padrões diferentes
    padroes = [
        f"{appid}_*.manifest",
        f"*_{appid}_*.manifest", 
        f"*{appid}*.manifest"
    ]
    
    for padrao in padroes:
        for manifest in depotcache_path.glob(padrao):
            try:
                # Verificar se realmente contém o appid de forma isolada
                nome_arquivo = manifest.stem
                if (f"_{appid}_" in nome_arquivo or 
                    nome_arquivo.startswith(f"{appid}_") or
                    re.search(rf'\b{appid}\b', nome_arquivo)):
                    
                    manifest.unlink()
                    removidos += 1
                    print(f"Manifest removido: {manifest.name}")
            except Exception as e:
                print(f"Erro ao remover {manifest.name}: {e}")
    
    return removidos

def remover_manifests_por_ids(ids_manifest: List[str]) -> int:
    """Remove apenas manifests com IDs específicos e retorna o número de manifests removidos"""
    depotcache_path = get_depotcache_path()
    if not depotcache_path.exists():
        print(f"{AMARELO}Pasta depotcache não encontrada!{RESET}")
        return 0
    
    removidos = 0
    for app_id in ids_manifest:
        # Buscar por TODOS os manifests que começam com o app_id
        for manifest in depotcache_path.glob(f"{app_id}_*.manifest"):
            try:
                manifest.unlink()
                removidos += 1
                print(f"{VERDE}✓ Manifest removido: {manifest.name}{RESET}")
            except Exception as e:
                print(f"{VERMELHO}✗ Erro ao remover {manifest.name}: {e}{RESET}")
        
        # Também buscar por manifests que contenham o app_id em qualquer posição no nome
        # (para lidar com diferentes formatos de nomeação)
        for manifest in depotcache_path.glob(f"*{app_id}*.manifest"):
            try:
                if manifest.name.startswith(f"{app_id}_") or f"_{app_id}_" in manifest.name:
                    manifest.unlink()
                    removidos += 1
                    print(f"{VERDE}✓ Manifest removido: {manifest.name}{RESET}")
            except Exception as e:
                print(f"{VERMELHO}✗ Erro ao remover {manifest.name}: {e}{RESET}")
    
    if removidos > 0:
        print(f"{CIANO}Total de manifests removidos: {VERDE}{removidos}{RESET}")
    
    return removidos

def encontrar_manifests_por_appid(app_id: str) -> List[Path]:
    """Encontra todos os arquivos .manifest associados a um app_id"""
    depotcache_path = get_depotcache_path()
    manifests_encontrados = []
    
    if not depotcache_path.exists():
        return manifests_encontrados
    
    # Padrão 1: appid_*.manifest
    manifests_encontrados.extend(depotcache_path.glob(f"{app_id}_*.manifest"))
    
    # Padrão 2: *_appid_*.manifest (para casos onde o appid está no meio do nome)
    manifests_encontrados.extend(depotcache_path.glob(f"*_{app_id}_*.manifest"))
    
    # Padrão 3: *appid*.manifest (busca mais ampla)
    # Filtramos depois para evitar falsos positivos
    for manifest in depotcache_path.glob(f"*{app_id}*.manifest"):
        # Verificar se o app_id aparece como número isolado no nome do arquivo
        name_without_ext = manifest.stem
        if f"_{app_id}_" in name_without_ext or name_without_ext.startswith(f"{app_id}_"):
            if manifest not in manifests_encontrados:
                manifests_encontrados.append(manifest)
    
    return list(set(manifests_encontrados))  # Remover duplicatas

async def fetch_game_name(app_id: str) -> str:
    """Obtém o nome do jogo da API da Steam"""
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get(app_id, {}).get("success"):
                return data[app_id]["data"]["name"]
            return "Nome não encontrado"
    except Exception as e:
        print(f"{VERMELHO}Erro ao buscar nome do jogo: {e}{RESET}")
        return "Erro ao buscar nome"

async def remove_game():
    """Função principal para remover jogos"""
    stplug_path = get_stplug_path()
    if not stplug_path.exists():
        print(f"\n{VERMELHO}Pasta stplug-in não encontrada em {stplug_path}{RESET}")
        input("\nPressione Enter para continuar...")
        return

    while True:
        arquivos = list(stplug_path.glob("*.lua"))
        mostrar_cabecalho()

        if not arquivos:
            print(f"\n{AMARELO}Nenhum Game/App foi localizado.{RESET}\n")
            input("Pressione Enter para continuar...")
            return

        print(f"{AZUL}Jogos encontrados:{RESET}\n")
        id_map = {}
        for idx, arq in enumerate(arquivos, 1):
            app_id = arq.stem
            nome = await fetch_game_name(app_id)
            id_map[str(idx)] = arq
            print(f"{idx}. {app_id} - {nome}")

        print(f"\n{VERDE}00. Remover TODOS os jogos (limpeza completa){RESET}")
        print(f"{VERMELHO}0. Voltar / Sair{RESET}")

        escolha = input("\nDigite o número do(s) jogo(s) que deseja remover (separados por espaço): ").strip()

        if escolha == "0":
            return

        elif escolha == "00":
            confirm = input(f"\n{VERMELHO}Tem certeza que deseja remover TODOS os {len(arquivos)} jogos? (s/n): {RESET}").strip().lower()
            if confirm == "s":
                lua, manifest = remover_todos_arquivos()
                print(f"\n{VERDE}Remoção concluída!{RESET}")
                print(f"Arquivos .lua removidos: {VERDE}{lua}{RESET}")
                print(f"Arquivos .manifest removidos: {VERDE}{manifest}{RESET}")
            input("\nPressione Enter para continuar...")
            continue

        else:
            # Processar múltiplas escolhas
            escolhas = escolha.split()
            removidos = 0
            erros = 0
            
            for esc in escolhas:
                if esc in id_map:
                    arq = id_map[esc]            
                    ids_manifest = extrair_appids_do_lua(arq)
                    
                    if ids_manifest:
                        remover_manifests_por_ids(ids_manifest)
                    
                    try:
                        arq.unlink()
                        removidos += 1
                        print(f"\n{VERDE}✔ Jogo {arq.stem} removido com sucesso{RESET}")
                    except Exception as e:
                        print(f"\n{VERMELHO}✘ Erro ao remover {arq.stem}: {e}{RESET}")
                        erros += 1
            
            if removidos > 0 or erros > 0:
                print(f"\n{CIANO}Resumo da remoção:{RESET}")
                print(f"{VERDE}Jogos removidos: {removidos}{RESET}")
                if erros > 0:
                    print(f"{VERMELHO}Erros durante a remoção: {erros}{RESET}")
            input("\nPressione Enter para continuar...")

async def main():
    """Função principal assíncrona"""
    await remove_game()

if __name__ == "__main__":
    asyncio.run(main())