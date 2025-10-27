import asyncio
import os
import time
import platform
import json
import shutil
import sys
import subprocess
import traceback
import requests  # Adicionado para downloads públicos
from pathlib import Path

# ANSI Colors
VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
VERMELHO_ESCURO = "\033[31m"
AMARELO_ESCURO = "\033[33m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Paths
CAMINHO_LOG = os.path.join("log", "acordo.json")
STEAM_CONFIG_FILE = os.path.join("log", "steam_config.json")

# Cache para informações do menu
menu_cache = {
    "dll_status": None,
    "activation_info": None,
    "last_updated": 0
}

# ================= FUNÇÕES AUXILIARES =================

def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")

def salvar_acordo(aceito: bool):
    """Save agreement ensuring log directory exists"""
    try:
        os.makedirs(os.path.dirname(CAMINHO_LOG), exist_ok=True)
        with open(CAMINHO_LOG, "w", encoding='utf-8') as f:
            json.dump({"acordo_aceito": aceito}, f, indent=4)
    except Exception as e:
        print(f"{VERMELHO}Error saving agreement: {str(e)}{RESET}")
        raise

def get_steam_path():
    """Retorna o caminho configurado da Steam ou o padrão se não existir configuração"""
    default_path = Path("C:/Program Files (x86)/Steam")
    try:
        if os.path.exists(STEAM_CONFIG_FILE):
            with open(STEAM_CONFIG_FILE, "r") as f:
                config = json.load(f)
                return Path(config.get("steam_path", default_path))
        return default_path
    except Exception:
        return default_path

def steam_exists(path=None):
    """Verifica se a Steam está instalada no caminho especificado"""
    path = path or get_steam_path()
    steam_exe = path / "steam.exe"
    steam_exe2 = path / "Steam.exe"
    return steam_exe.exists() or steam_exe2.exists()

def get_steam_all_path():
    """Retorna o caminho para a pasta SteamAll"""
    path = get_steam_path() / "SteamAll"
    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        print(f"{VERMELHO}Erro de permissão ao acessar: {path}{RESET}")
        print(f"{AMARELO}Tentando usar diretório alternativo...{RESET}")
        alt_path = Path(os.path.expanduser("~/SteamAll"))
        os.makedirs(alt_path, exist_ok=True)
        return alt_path
    return path

def set_steam_path(new_path):
    """Define um novo caminho para a Steam"""
    try:
        os.makedirs(os.path.dirname(STEAM_CONFIG_FILE), exist_ok=True)
        with open(STEAM_CONFIG_FILE, "w") as f:
            json.dump({"steam_path": str(new_path)}, f)
        return True
    except Exception:
        return False

def download_from_public_drive(file_id, destination):
    """Faz download de arquivo do Google Drive público"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        print(f"{VERMELHO}Erro no download: {str(e)}{RESET}")
        return False

def ensure_script_downloaded(script_name):
    """Faz o Download direto para SteamAll com link público"""
    try:
        destination = os.path.join(get_steam_all_path(), script_name)
        
        if os.path.exists(destination) and os.path.getsize(destination) > 0:
            print(f"{VERDE}✓ Arquivo {script_name} já existe{RESET}")
            return destination
            
        # Mapeamento de arquivos públicos
        PUBLIC_FILES = {
            "hid.rar": "1B3aWT0sg4jkAo-pCTAbsmEoIEZWJ-2hQ",
            "CreamInstaller.rar": "1nT3t1eie8jurWvdDd4xsJJNKBXCyBMl3",
            "LuaFastAuto.rar": "1lSlV9d-NL87RxMPc9md5DSLPBJo27nkb"
        }
        
        if script_name not in PUBLIC_FILES:
            raise ValueError(f"Arquivo {script_name} não configurado")
        
        print(f"{AZUL}Baixando {script_name}...{RESET}")
        
        file_id = PUBLIC_FILES[script_name]
        success = download_from_public_drive(file_id, destination)
        
        if success:
            print(f"{VERDE}✓ Download de {script_name} completo{RESET}")
            return destination
        else:
            raise Exception("Falha no download")
        
    except Exception as e:
        print(f"\n{VERMELHO}Erro crítico no download: {str(e)}{RESET}")
        if os.path.exists(destination):
            os.remove(destination)
        raise

def ensure_script_downloaded_crack(script_name, max_retries=3):
    """Versão para crack com retry"""
    destination = os.path.join(get_steam_all_path(), script_name)

    for attempt in range(max_retries):
        try:
            # Mapeamento de arquivos públicos
            PUBLIC_FILES = {
                "hid.rar": "1B3aWT0sg4jkAo-pCTAbsmEoIEZWJ-2hQ",
                "CreamInstaller.rar": "1nT3t1eie8jurWvdDd4xsJJNKBXCyBMl3", 
                "LuaFastAuto.rar": "1lSlV9d-NL87RxMPc9md5DSLPBJo27nkb"
            }
            
            if script_name not in PUBLIC_FILES:
                raise ValueError(f"Arquivo {script_name} não configurado")
            
            file_id = PUBLIC_FILES[script_name]
            success = download_from_public_drive(file_id, destination)
            
            if success:
                print(f"{VERDE}✓ Iniciando...{RESET}")
                return destination
            else:
                raise Exception("Falha no download")

        except Exception as e:
            print(f"{AMARELO}Erro na tentativa {attempt + 1}: {e}{RESET}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise

# ================= FUNÇÕES DE ACORDO E ATIVAÇÃO =================
def verificar_acordo():
    """Verifica o acordo e a configuração da Steam"""
    try:
        os.makedirs("log", exist_ok=True)
        os.makedirs(get_steam_all_path(), exist_ok=True)
        
        print(f"{AZUL}Verificando configurações da Steam...{RESET}", end='\r')
        
        from dll_manager import check_and_install
        dll_status, dll_message = check_and_install()
        
        if not dll_status:
            print(f"{VERMELHO}Erro na configuração: {dll_message}{RESET}")
            time.sleep(3)
            return False

        if os.path.exists(CAMINHO_LOG):
            try:
                with open(CAMINHO_LOG, "r", encoding='utf-8') as f:
                    dados = json.load(f)
                    return dados.get("acordo_aceito")
            except:
                return None
        return None

    except Exception as e:
        print(f"{VERMELHO}Erro na verificação inicial: {str(e)}{RESET}")
        traceback.print_exc()
        time.sleep(3)
        return None

def tela_inicial():
    limpar_tela()
    if os.name == "nt":
        os.system("mode con: cols=120 lines=50")
    
    try:
        print(VERDE + "\t           Bem-vindo ao Gerenciador de Games STEAM LuaFast !" + RESET)
        print(AMARELO_ESCURO + "\n                          Termos de Licença e Utilização" + RESET)
        print(f"\nEste projeto é distribuído sob a {AZUL}licença GPL-3.0{RESET}. As diretrizes a seguir são complementares à licença GPL-3.0; em caso de conflito, prevalecem sobre a mesma.")
        print(f"\nDurante o uso deste programa, podem ser gerados dados protegidos por direitos autorais. O usuário deverá excluir quaisquer dados protegidos no prazo máximo de 24 horas.")
        print(f"\nEste projeto é completamente {AZUL}gratuito , mas você pode contribuir fazendo uma doação caso queira ajudar o projeto{RESET}.")
        print("\nÉ proibido utilizar este projeto para fins comerciais.")
        print("Modificações no projeto só serão permitidas mediante a publicação conjunta do código-fonte correspondente e menções aos criadores.")
        print(f"{AMARELO}Ao utilizar este programa, você declara estar de acordo com todos os termos acima.{RESET}")

        while True:
            resposta = input(f"\n{VERMELHO}Você concorda com os termos de uso descritos acima? (s/n): {RESET}").strip().lower()
            if resposta == "s":
                try:
                    salvar_acordo(True)
                    return True
                except Exception as e:
                    print(f"{VERMELHO}Falha ao registrar aceite: {str(e)}{RESET}")
                    print("Tentando novamente...")
                    time.sleep(1)
                    continue
            elif resposta == "n":
                salvar_acordo(False)
                print(VERMELHO + "\nVocê não confirmou a leitura das instruções." + RESET)
                print(VERMELHO + "O programa será fechado em 4 segundos..." + RESET)
                time.sleep(4)
                exit(0)
            else:
                print(VERMELHO + "Opção inválida! Digite apenas 's' ou 'n'." + RESET)
    except Exception as e:
        print(f"{VERMELHO}Erro crítico na tela inicial: {str(e)}{RESET}")
        traceback.print_exc()
        time.sleep(5)
        exit(1)

# ================= FUNÇÕES DO MENU =================
def exibir_banner():
    limpar_tela()
    if not platform.system() == "Windows":
        print("Este script só pode ser executado no Windows.")
        exit(1)
    
    banner = r"""
 _        _   _     ___     _____    _____     ___    _____   
| |      | | | |   / _ \   |  ___|  | ____|   / __|  |_   _|  
| |      | | | |  / /_\ \  | |_     |  _|     \__ \    | |    
| |___   | | | |  |  _  |  |  _|    | |___    __/ /    | |    
|_____|   \___/   | | | |  | |      |_____|  |___/     |_|    
                  \_| |_/  |_|                                 
    """
    print(VERDE + banner + RESET)
    version_line = "Dev's: @blumenal & @jeffersonsud"
    print(version_line)
    print("Use o site " + AZUL + "https://steamdb.info/" + RESET + " para obter o ID e o nome dos games desejado.")
    print(f"Se gostou do App {VERDE}faça uma doação e ajude a manter o LuaFast funcionando{RESET}.")

def atualizar_cache_menu():
    """Atualiza as informações do menu em background"""
    try:
        from dll_manager import check_and_install
        menu_cache["dll_status"] = check_and_install()[1]
    except:
        menu_cache["dll_status"] = f"{VERMELHO}X Steam Não configurada{RESET}"
    
    try:
        from ativador import check_activation_status
        status, info = check_activation_status()
        if status:
            if info.get("Status") == "TESTE":
                menu_cache["activation_info"] = f"{info['Código']} (TESTE)"
            else:
                menu_cache["activation_info"] = f"{info['Código']} (ATIVADO)"
        else:
            menu_cache["activation_info"] = f"{info['Código']} (EXPIRADO)"
    except:
        menu_cache["activation_info"] = "ERRO"
    
    menu_cache["last_updated"] = time.time()

def exibir_menu():
    """Exibe o menu completo após pré-carregar todas as informações"""
    atualizar_cache_menu()
    
    dll_status = menu_cache.get("dll_status", f"{VERMELHO}X Steam Não configurada{RESET}")
    
    limpar_tela()
    exibir_banner()
    
    # REMOVIDA LINHA DO CÓDIGO DE ATIVAÇÃO
    print(f"{CYAN}Status: {dll_status}{RESET}\n")
    
    print("     ╔═════════════════════════════════════════════╗")
    print("     ║         🎮 GERENCIADOR DE JOGOS 🎮          ║")
    print("     ╠═════════════════════════════════════════════╣")
    print(f"     ║ [1] {VERDE}ADICIONAR GAMES NA BIBLIOTECA STEAM{RESET}     ║")
    print(f"     ║ [2] {VERMELHO}REMOVER GAMES DA BIBLIOTECA STEAM{RESET}       ║")
    print("     ╠═════════════════════════════════════════════╣")
    print("     ║ [3] BACKUP & RESTAURAÇÃO                    ║")
    print("     ╠═════════════════════════════════════════════╣")
    print(f"     ║ [4] {VERMELHO}FINALIZAR STEAM / REINICIAR{RESET}             ║")
    print(f"     ║ [5] {CYAN}CONFIGURAR DIRETÓRIO DA STEAM{RESET}           ║")
    print("     ╠═════════════════════════════════════════════╣")
    print(f"     ║ [0] ❌ {VERMELHO}SAIR{RESET}                                 ║")
    print("     ╚═════════════════════════════════════════════╝")
    
def menu():
    while True:
        exibir_menu()
        
        escolha = input("     Digite o número da opção desejada: ").strip()

        if escolha == "1":
            try:
                import install
                asyncio.run(install.main_flow())
            except Exception as e:
                print(f"Erro: {e}")
                input("Pressione Enter para continuar...")
        elif escolha == "2":
            try:
                import remove
                asyncio.run(remove.main())
            except Exception as e:
                print(f"Erro: {e}")
                input("Pressione Enter para continuar...")
        elif escolha == "3":
            try:
                import backup
                asyncio.run(backup.menu_principal())
            except Exception as e:
                print(f"Erro: {e}")
                input("Pressione Enter para continuar...")
        elif escolha == "4":
            try:
                import fecharsteam
                fecharsteam.encerrar_steam_processos()
            except Exception as e:
                print(f"Erro: {e}")
                input("Pressione Enter para continuar...")
        elif escolha == "5":
            configurar_diretorio_steam()
        elif escolha == "0":
            print("Saindo do programa...")
            break
        else:
            print("Opção inválida.")
            input("Pressione Enter para continuar...")    
            
# ================= FUNÇÕES DE OPERAÇÕES =================
def configurar_diretorio_steam():
    limpar_tela()
    print(f"{AZUL}╔════════════════════════════════════════════╗")
    print(f"║       CONFIGURAR DIRETÓRIO DA STEAM        ║")
    print(f"╚════════════════════════════════════════════╝{RESET}")
    
    current_path = get_steam_path()
    print(f"\nDiretório atual da Steam: {VERDE}{current_path}{RESET}")
    
    print("\n1. Usar diretório padrão (C:/Program Files (x86)/Steam)")
    print("2. Especificar outro diretório")
    print("0. Voltar")
    
    escolha = input("\nEscolha uma opção: ").strip()
    
    if escolha == "1":
        old_path = current_path
        set_steam_path("C:/Program Files (x86)/Steam")
        
        if old_path != get_steam_path():
            steamall_old = old_path / "SteamAll"
            hid_dll_old = old_path / "hid.dll"
            icone_old = old_path / "icone.ico"
            try:
                if steamall_old.exists() and steamall_old.is_dir():
                    shutil.rmtree(steamall_old, ignore_errors=True)
                if hid_dll_old.exists() and hid_dll_old.is_file():
                    os.remove(hid_dll_old)
                if icone_old.exists() and icone_old.is_file():
                    os.remove(icone_old)
            except Exception as e:
                print(f"{AMARELO}Aviso: Não foi possível limpar o diretório antigo - {e}{RESET}")
        
        print(f"\n{VERDE}Diretório da Steam redefinido para o padrão.{RESET}")
        input("\nPressione Enter para continuar...")
        
    elif escolha == "2":
        print(f"\n{AMARELO}Exemplo:{RESET} D:/Games/Steam")
        old_path = current_path
        novo_caminho = input("\nDigite ou cole o novo caminho completo para a pasta Steam: \n").strip()
        
        if os.path.exists(novo_caminho):
            steam_exe = os.path.join(novo_caminho, "Steam.exe")
            
            if os.path.isfile(steam_exe):
                try:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    icone_origem = os.path.join(script_dir, "icone.ico")
                    icone_destino = os.path.join(novo_caminho, "icone.ico")
                    
                    if os.path.exists(icone_origem):
                        try:
                            shutil.copy(icone_origem, icone_destino)
                        except Exception as e:
                            print(f"{AMARELO}Aviso: Falha ao copiar ícone - {e}{RESET}")
                    else:
                        print(f"{AMARELO}Aviso: icone.ico não encontrado no diretório do script{RESET}")

                    try:
                        import win32com.client
                        from win32com.client import Dispatch
                        import ctypes
                        from ctypes import wintypes, create_unicode_buffer

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
                                
                                icon_path = os.path.join(novo_caminho, "icone.ico")
                                if not os.path.exists(icon_path):
                                    icon_path = steam_exe
                                    print(f"{AMARELO}Aviso: icone.ico não encontrado. Usando ícone padrão.{RESET}")

                                shell = Dispatch('WScript.Shell')
                                shortcut = shell.CreateShortCut(shortcut_path)
                                shortcut.TargetPath = steam_exe
                                shortcut.Arguments = "-noverifyfiles -nobootstrapupdate -skipinitialbootstrap -norepairfiles -console"
                                shortcut.WorkingDirectory = novo_caminho
                                shortcut.IconLocation = icon_path
                                shortcut.save()
                                
                                print(f"{VERDE}Atalho criado em: {shortcut_path}{RESET}")
                                shortcut_created = True
                                break
                                
                            except Exception as e:
                                print(f"{AMARELO}Falha em {desktop}: {str(e)}{RESET}")
                                continue

                        if not shortcut_created:
                            print(f"{VERMELHO}Não foi possível criar o atalho em nenhum local!{RESET}")

                    except ImportError:
                        print(f"{VERMELHO}Erro: Instale o pywin32 com 'pip install pywin32'.{RESET}")
                    except Exception as e:
                        print(f"{VERMELHO}Falha crítica: {str(e)}{RESET}")

                    if set_steam_path(novo_caminho):
                        if old_path != get_steam_path():
                            steamall_old = old_path / "SteamAll"
                            hid_dll_old = old_path / "hid.dll"
                            icone_old = old_path / "icone.ico"
                            try:
                                if steamall_old.exists() and steamall_old.is_dir():
                                    shutil.rmtree(steamall_old, ignore_errors=True)
                                if hid_dll_old.exists() and hid_dll_old.is_file():
                                    os.remove(hid_dll_old)
                                if icone_old.exists() and icone_old.is_file():
                                    os.remove(icone_old)
                            except Exception as e:
                                print(f"{AMARELO}Aviso: Não foi possível limpar o diretório antigo - {e}{RESET}")
                        
                        print(f"\n{VERDE}Diretório atualizado com sucesso!{RESET}")
                    else:
                        print(f"\n{VERMELHO}Falha ao salvar o caminho.{RESET}")
                        
                except Exception as e:
                    print(f"{VERMELHO}Erro durante a configuração: {str(e)}{RESET}")
                    
            else:
                print(f"\n{VERMELHO}Está pasta que está sendo definida não contém os arquivos da Steam, verifique a pasta e tente novamente.{RESET}")
                print(f"{VERMELHO}A mudança de diretório não foi salva.{RESET}")
                
        else:
            print(f"\n{VERMELHO}Diretório inválido!{RESET}")
            
        input("\nPressione Enter para continuar...")

    elif escolha == "0":
        return

def instalar_dlcs():
    limpar_tela()
    print(f"{VERDE}\nIniciando instalação das DLCs...{RESET}")
   
    print(f"{VERDE}\nInstalando/Executando CreamInstaller...{RESET}")
    print(f"{VERDE}CreamInstaller foi Criado por: https://github.com/pointfeev{RESET}")
    
    try:
        rar_path = ensure_script_downloaded("CreamInstaller.rar")
        extract_dir = get_steam_all_path()
        
        seven_zip = r"C:\Program Files\7-Zip\7z.exe"
        winrar = r"C:\Program Files\WinRAR\WinRAR.exe"
        
        if not os.path.exists(seven_zip) and not os.path.exists(winrar):
            print(f"{VERMELHO}ERRO: Instale 7-Zip ou WinRAR{RESET}")
            input("Pressione Enter para continuar...")
            return

        cmd = (
            [winrar, 'x', '-ibck', '-p123', rar_path, extract_dir]
            if os.path.exists(winrar)
            else [seven_zip, 'x', '-p123', rar_path, f'-o{extract_dir}', '-y']
        )

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if result.returncode != 0:
            print(f"{VERMELHO}Falha na extração: {result.stderr.decode()}{RESET}")
            input("Pressione Enter para continuar...")
            return
        
        exe_path = os.path.join(extract_dir, "CreamInstaller.exe")
        if not os.path.exists(exe_path):
            raise FileNotFoundError("Arquivo CreamInstaller.exe não encontrado.")
        
        processo = subprocess.Popen(exe_path)
        print(f"{VERDE}\nAguardando finalização...{RESET}")
        processo.wait()
        
        os.remove(exe_path)
        print(f"{VERDE}\nProcesso concluído!{RESET}")
        time.sleep(1)
        
    except Exception as e:
        print(f"{VERMELHO}\nErro ao instalar DLCs: {str(e)}{RESET}")
        traceback.print_exc()
        input("Pressione Enter para continuar...")

def autocrack():
    limpar_tela()
    print(f"{VERDE}\nIniciando LuaFast AutoCrack...{RESET}")
    print(f"{VERDE}\nAguarde...{RESET}")
    
    try:
        rar_path = ensure_script_downloaded_crack("LuaFastAuto.rar")
        extract_dir = get_steam_all_path()
        
        seven_zip = r"C:\Program Files\7-Zip\7z.exe"
        winrar = r"C:\Program Files\WinRAR\WinRAR.exe"
        
        if not os.path.exists(seven_zip) and not os.path.exists(winrar):
            print(f"{VERMELHO}ERRO: Instale 7-Zip ou WinRAR{RESET}")
            input("Pressione Enter para continuar...")
            return
        
        cmd = (
            [winrar, 'x', '-ibck', '-p123', rar_path, extract_dir]
            if os.path.exists(winrar)
            else [seven_zip, 'x', '-p123', rar_path, f'-o{extract_dir}', '-y']
        )

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if result.returncode != 0:
            print(f"{VERMELHO}Falha na extração: {result.stderr.decode()}{RESET}")
            input("Pressione Enter para continuar...")
            return
        
        exe_path = os.path.join(extract_dir, "LuaAuto.exe")
        if not os.path.exists(exe_path):
            raise FileNotFoundError("Arquivo LuaFast AutoCrack não encontrado.")
        
        processo = subprocess.Popen(exe_path)
        print(f"{VERDE}\nAguardando finalização...{RESET}")
        processo.wait()

        # Exclusão do executável
        if os.path.exists(exe_path):
            os.remove(exe_path)

        # Exclusão das pastas TEMP e Goldberg
        steamall = get_steam_all_path()
        for pasta in ["TEMP", "Goldberg"]:
            caminho = steamall / pasta
            if caminho.exists() and caminho.is_dir():
                shutil.rmtree(caminho, ignore_errors=True)

        print(f"{VERDE}\nProcesso concluído!{RESET}")
        time.sleep(1)
        
    except Exception as e:
        print(f"{VERMELHO}\nErro ao instalar LuaFast AutoCrack: {str(e)}{RESET}")
        traceback.print_exc()
        input("Pressione Enter para continuar...")
        
# ================= FUNÇÃO PRINCIPAL =================
def main():
    try:
        # VERIFICAÇÃO INICIAL DA STEAM (MANTIDA)
        if not steam_exists():
            limpar_tela()
            current_path = get_steam_path()
            print(f"\n\n{AMARELO}Steam não encontrada no diretório:{RESET}{VERMELHO} {current_path}{RESET}\n{AMARELO}Provávelmente sua Steam está instalada em outro diretório.{RESET}\n")
            print(f"\n{AMARELO}Você precisa configurar o caminho correto da Steam.{RESET}\n{VERDE}Na próxima tela configure o local de instalação da Steam.{RESET}\n")
            input("Pressione Enter para continuar...")
            configurar_diretorio_steam()
            
            if not steam_exists():
                print(f"{VERMELHO}Ainda não foi possível localizar a Steam.{RESET}")
                print("O programa será encerrado.")
                time.sleep(3)
                sys.exit(1)

        # GARANTIR PASTAS NECESSÁRIAS (MANTIDA)
        os.makedirs("log", exist_ok=True)
        os.makedirs(get_steam_all_path(), exist_ok=True)
        
        # VERIFICAÇÃO INICIAL DA DLL (MANTIDA)
        print(f"{AZUL}Verificando requisitos do sistema...{RESET}", end='\r')
        
        # VERIFICAÇÃO SIMPLES DA DLL
        from dll_manager import check_and_install
        dll_status, dll_message = check_and_install()
        
        if not dll_status:
            print(f"{VERMELHO}Erro na configuração: {dll_message}{RESET}")
            time.sleep(3)
            return False

        # SE CHEGOU ATÉ AQUI, INICIA O MENU DIRETAMENTE
        menu()

    except Exception as e:
        print(f"{VERMELHO}\nERRO CRÍTICO: {str(e)}{RESET}")
        traceback.print_exc()
        input("\nPressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()