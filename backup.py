import os
import asyncio
import shutil
import aiohttp
import re
from pathlib import Path
from config_manager import get_steam_subpath

# Cores ANSI
NEUTRO = "\033[97m"
AZUL = "\033[94m"
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
RESET = "\033[0m"

# Símbolos
SUCESSO = f"{VERDE}✔{RESET}"
FALHA = f"{VERMELHO}✘{RESET}"

# Caminhos
STPLUG_PATH = get_steam_subpath("config/stplug-in")
DEPOTCACHE_PATH = get_steam_subpath("depotcache")
BACKUP_ROOT = Path("log/backup")


# === UTILIDADES VISUAIS ===

def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")

def mostrar_cabecalho():
    print(f"{NEUTRO}")
    print("╔" + "═" * 56 + "╗")
    print("║" + "🎮 GERENCIADOR DE BACKUPS STEAM 🎮".center(54) + "║")
    print("╚" + "═" * 56 + "╝" + f"{RESET}")

def mostrar_menu():
    print()
    print(f"{NEUTRO}╔════════════════════════════════════════════════════════╗")
    print(f"║{NEUTRO} 1. 💾 Fazer Backup dos Jogos{RESET}".ljust(57) + "        ║")
    print(f"{NEUTRO}║                                                        ║")
    print(f"║{AMARELO} 2. ♻️ Restaurar Backup{RESET}".ljust(57) + "         ║")
    print(f"{NEUTRO}║                                                        ║")
    print(f"║{VERMELHO} 0. ❌ Sair{RESET}".ljust(57) +   "        ║")
    print(f"{NEUTRO}╚════════════════════════════════════════════════════════╝{RESET}")


# === BACKUP ===

async def fetch_game_name(app_id: str) -> str:
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return data[app_id]["data"]["name"] if data[app_id]["success"] else "Desconhecido"
    except:
        return "Desconhecido"

def listar_arquivos_lua():
    return list(STPLUG_PATH.glob("*.lua"))

def extrair_appids_do_lua(lua_path: Path) -> list[str]:
    try:
        with open(lua_path, "r", encoding="utf-8") as f:
            conteudo = f.read()
        return list(set(re.findall(r'addappid\((\d+)', conteudo)))
    except Exception:
        return []

def copiar_arquivos_backup(lua_filename: str) -> tuple[int, int]:
    app_id = Path(lua_filename).stem
    destino = BACKUP_ROOT / app_id
    destino.mkdir(parents=True, exist_ok=True)
    
    sucessos = 0
    falhas = 0
    
    lua_origem = STPLUG_PATH / lua_filename
    if lua_origem.exists():
        try:
            shutil.copy2(lua_origem, destino)
            print(f"  {lua_origem.name.ljust(30)} {SUCESSO}")
            sucessos += 1
        except Exception as e:
            print(f"  {lua_origem.name.ljust(30)} {FALHA} ({str(e)})")
            falhas += 1
            
        for a_id in extrair_appids_do_lua(lua_origem):
            for manifest_path in DEPOTCACHE_PATH.glob(f"{a_id}_*.manifest"):
                try:
                    shutil.copy2(manifest_path, destino)
                    print(f"  {manifest_path.name.ljust(30)} {SUCESSO}")
                    sucessos += 1
                except Exception as e:
                    print(f"  {manifest_path.name.ljust(30)} {FALHA} ({str(e)})")
                    falhas += 1
    
    return sucessos, falhas

def backup_existe(app_id: str) -> bool:
    return (BACKUP_ROOT / app_id).exists()

async def fazer_backup():
    if not STPLUG_PATH.exists() or not DEPOTCACHE_PATH.exists():
        print("Pastas necessárias não foram encontradas.")
        input("\nPressione Enter para voltar...")
        return

    while True:
        limpar_tela()
        mostrar_cabecalho()
        arquivos = listar_arquivos_lua()
        if not arquivos:
            print("Nenhum jogo (.lua) encontrado para backup.")
            input("\nPressione Enter para sair...")
            break

        id_map = {}
        print("Jogos disponíveis para backup:\n")
        for idx, arq in enumerate(arquivos, 1):
            app_id = arq.stem
            nome = await fetch_game_name(app_id)
            id_map[str(idx)] = arq.name
            status = f"{VERDE}[Backup OK]{RESET}" if backup_existe(app_id) else ""
            print(f"{idx}. {app_id} - {nome} {status}")

        print("\n00. Fazer backup de TODOS os jogos")
        print("0. Voltar ao menu")

        escolha = input("\nEscolha um número: ").strip()

        if escolha == "0":
            break
        elif escolha == "00":
            print("\nIniciando backup de todos os jogos...\n")
            total_sucessos = 0
            total_falhas = 0
            for arq in arquivos:
                sucessos, falhas = copiar_arquivos_backup(arq.name)
                total_sucessos += sucessos
                total_falhas += falhas
            print(f"\nResumo: {SUCESSO} {total_sucessos} arquivos | {FALHA} {total_falhas} falhas")
            input("\nBackup de todos os jogos concluído. Pressione Enter...")
        elif escolha in id_map:
            print(f"\nIniciando backup de {Path(id_map[escolha]).stem}...\n")
            sucessos, falhas = copiar_arquivos_backup(id_map[escolha])
            print(f"\nResumo: {SUCESSO} {sucessos} arquivos | {FALHA} {falhas} falhas")
            input(f"\nBackup de {Path(id_map[escolha]).stem} concluído. Pressione Enter...")
        else:
            input("\nOpção inválida. Pressione Enter para tentar novamente...")


# === RESTAURAÇÃO ===

def listar_backups_disponiveis():
    return sorted([p for p in BACKUP_ROOT.iterdir() if p.is_dir()])

def restaurar_backup(app_id: str) -> tuple[int, int]:
    origem = BACKUP_ROOT / app_id
    sucessos = 0
    falhas = 0
    
    if not origem.exists():
        return sucessos, falhas
        
    print(f"\nRestaurando {app_id}...\n")
    for arquivo in origem.glob("*"):
        try:
            if arquivo.suffix == ".lua":
                shutil.copy2(arquivo, STPLUG_PATH)
                print(f"  {arquivo.name.ljust(30)} {SUCESSO}")
                sucessos += 1
            elif arquivo.suffix == ".manifest":
                shutil.copy2(arquivo, DEPOTCACHE_PATH)
                print(f"  {arquivo.name.ljust(30)} {SUCESSO}")
                sucessos += 1
        except Exception as e:
            print(f"  {arquivo.name.ljust(30)} {FALHA} ({str(e)})")
            falhas += 1
    
    return sucessos, falhas

async def restaurar():
    if not BACKUP_ROOT.exists():
        print("A pasta de backups não foi encontrada.")
        input("\nPressione Enter para sair...")
        return

    backups = listar_backups_disponiveis()
    if not backups:
        print("A pasta de backups está vazia.")
        input("\nPressione Enter para sair...")
        return

    while True:
        limpar_tela()
        mostrar_cabecalho()
        id_map = {}
        print("Backups disponíveis:\n")
        for idx, pasta in enumerate(backups, 1):
            app_id = pasta.name
            nome = await fetch_game_name(app_id)
            id_map[str(idx)] = app_id
            print(f"{idx}. {app_id} - {nome}")

        print("\n00. Restaurar TODOS os backups")
        print("0. Voltar ao menu")

        escolha = input("\nEscolha uma opção: ").strip()

        if escolha == "0":
            break
        elif escolha == "00":
            total_sucessos = 0
            total_falhas = 0
            for app_id in [p.name for p in backups]:
                sucessos, falhas = restaurar_backup(app_id)
                total_sucessos += sucessos
                total_falhas += falhas
            print(f"\nResumo: {SUCESSO} {total_sucessos} arquivos | {FALHA} {total_falhas} falhas")
            input("\nTodos os backups foram restaurados. Pressione Enter...")
        elif escolha in id_map:
            sucessos, falhas = restaurar_backup(id_map[escolha])
            print(f"\nResumo: {SUCESSO} {sucessos} arquivos | {FALHA} {falhas} falhas")
            input(f"\nBackup de {id_map[escolha]} restaurado. Pressione Enter...")
        else:
            input("\nOpção inválida. Pressione Enter para tentar novamente...")


# === MENU PRINCIPAL ===

async def menu_principal():
    while True:
        limpar_tela()
        mostrar_cabecalho()
        mostrar_menu()

        escolha = input(f"\n{NEUTRO}Digite o número da opção desejada: {RESET}").strip()

        if escolha == "1":
            await fazer_backup()
        elif escolha == "2":
            await restaurar()
        elif escolha == "0":
            print(f"\n{VERMELHO}Voltando para o menu principal...{RESET}")
            break
        else:
            input(f"\n{VERMELHO}Opção inválida. Pressione Enter para tentar novamente.{RESET}")

if __name__ == "__main__":
    asyncio.run(menu_principal())