# fecharsteam.py
import subprocess
import time
import os
from pathlib import Path
from config_manager import get_steam_path 

if os.name == 'nt':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


VERMELHO = "\033[91m"
VERDE = "\033[92m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
RESET = "\033[0m"


PROCESSOS_STEAM = [
    "steam.exe",
    "steamwebhelper.exe",
    "gameoverlayui.exe", 
    "steamservice.exe",
    "steamerrorreporter.exe",
    "steamstart.exe",
    "steamguard.exe"
]

def encerrar_steam_processos():
    """Encerra todos os processos relacionados à Steam"""
    processos_encerrados = 0
    
    for processo in PROCESSOS_STEAM:
        try:
            result = subprocess.run(
                ["taskkill", "/f", "/im", processo],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                check=False
            )
            if result.returncode == 0:
                print(f"{VERDE}[✓] Processo {processo} encerrado{RESET}")
                processos_encerrados += 1
        except Exception as e:
          
            pass
    
    if processos_encerrados > 0:
        print(f"{AZUL}[*] Aguardando processos encerrarem...{RESET}")
        time.sleep(2)
    
    return processos_encerrados > 0

def reiniciar_steam():
    """Reinicia o Steam no diretório configurado com parâmetros otimizados"""
    steam_exe = get_steam_path() / "Steam.exe"
    
    if not steam_exe.exists():
        print(f"\n{VERMELHO}[!] Steam.exe não encontrado em: {steam_exe}{RESET}")
        print(f"{AMARELO}Verifique se o diretório da Steam está configurado corretamente{RESET}")
        return False
    
    try:
        print(f"\n{AZUL}[*] Iniciando Steam com parâmetros otimizados...{RESET}")
        subprocess.Popen(
            [str(steam_exe), "-noverifyfiles", "-nobootstrapupdate", 
            "-skipinitialbootstrap", "-norepairfiles", "-console"],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW
        )
        print(f"{VERDE}[✓] Steam iniciada com sucesso{RESET}")
        print(f"{AMARELO}Proteção contra atualização do APP Steam {RESET}")
        return True
    except Exception as e:
        print(f"{VERMELHO}[!] Falha ao iniciar Steam: {e}{RESET}")
        return False

def apenas_encerrar_steam():
    """Apenas encerra a Steam sem reiniciar"""
    print(f"\n{AMARELO}[*] Encerrando processos da Steam...{RESET}")
    if encerrar_steam_processos():
        print(f"{VERDE}[✓] Steam encerrada com sucesso{RESET}")
    else:
        print(f"{AZUL}[i] Nenhum processo da Steam estava em execução{RESET}")

def encerrar_e_reiniciar_steam():
    """Encerra e reinicia a Steam"""
    print(f"\n{AMARELO}[*] Encerrando processos da Steam...{RESET}")
    encerrar_steam_processos()
    time.sleep(1)
    return reiniciar_steam()

def apenas_reiniciar_steam():
    """Apenas reinicia a Steam (sem encerrar primeiro)"""
    return reiniciar_steam()

def menu_reiniciar():
    """Menu interativo para reiniciar a Steam"""
    print(f"\n{AZUL}╔════════════════════════════════════════════╗")
    print(f"║           GERENCIADOR DA STEAM             ║")
    print(f"╚════════════════════════════════════════════╝{RESET}")
    
    print(f"\n1. {VERDE}Encerrar e reiniciar a Steam{RESET}")
    print(f"2. {AMARELO}Apenas encerrar a Steam{RESET}")
    print(f"3. {AZUL}Apenas reiniciar a Steam{RESET}")
    print(f"0. {VERMELHO}Voltar{RESET}")
    
    escolha = input("\nEscolha uma opção: ").strip()
    
    if escolha == "1":
        encerrar_e_reiniciar_steam()
    elif escolha == "2":
        apenas_encerrar_steam()
    elif escolha == "3":
        apenas_reiniciar_steam()
    elif escolha == "0":
        return True 
    else:
        print(f"{VERMELHO}Opção inválida!{RESET}")
    
    input("\nPressione Enter para continuar...")
    return False

if __name__ == "__main__":

    while True:
        voltar = menu_reiniciar()
        if voltar:
            break