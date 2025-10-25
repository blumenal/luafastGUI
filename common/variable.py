import os
import httpx
import sys
import winreg
import ujson as json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Caminho para salvar o config.json na pasta log
CONFIG_DIR = Path("./log")
CONFIG_FILE = CONFIG_DIR / "config.json"

# Credenciais do Google Drive
SERVICE_ACCOUNT_INFO = {
    "type": "service_account",
    "project_id": "repositorios-459911",
    "private_key_id": "e64094bb8a038fd7c2072d0b447c2e72ccce8858",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDHTfLIMe/DFlzL
0IMrgNb74gJFiFDlmzk2vG0/J6c2YWNAlnzCIEkSNhKENNfwjxybuSlRL/LderdX
TmOVH3WmYj3bkL4Ak6cCL49y963OaoaZsU8xTYVK+apLWolFOgv4WJcwZWVj0SRo
dTXKeygLNy5a7rKP2jfoWmU5faM702VszFDehq4c9pRyJyNgoDeoNhUyF7RFHPla
CCdAhr0PI/Tct6Kr8tz9vUf/IYi6QG8HN1fW9yk+CmIFoGrtySKvYriVk9/aYsFQ
DtqsfXpnJThz+rz9reOyTOgT47g89mmN6qmgUrrpBfxc7XQYM5kzn4Kmd6+ykLVv
XN9ErXelAgMBAAECggEAX8CFScUkCbgusQTmX/owTydQLBPHuegPXsq8OcFVRn0X
cCpcme9k68jqsHWq4ToAZphYz1aX+exBNULF+Rj6Lwu36Err3d8SN6yd4IA6Epd/
P0u+XlN+HH1CYZ2Hoai3o4L8cBXm1kPemAjn5PWyUWEbdjiDtTUD8y+qviosSEr4
PZsCBtBNBzGno+ke/c8LD1f3f1rtVh5HUjaYvLNyOgVhW/NNYpyTET6h7mH8T0Q0
n/MRlj38ghYRCeMP9g5+0yuDGTKdqyv/wuukywBi2GzFcO6hADZd4vifESqJNOQa
ydVPHkz5j20ExvcW/AhBBwTmKFnAEeXdeBehf/nOKQKBgQDxzADHGiFb+O02yfgr
szCzuxT/FaXDaB//u5EcusdlCMvPx3F57KvGiiIyzmN+mkRNfadDW73E6Gvk/Uhd
YVnSyBosqTkRdwvN+7+YGNamAbcvjSCvl9IJeqGj8dOpRMEXcNSqGPR31xeEhaYX
IjE1RiI/trSv8eYq7Pw7sDzN1wKBgQDTAvhTEOLC0ZY2qoj/ltDlhdiWTbq0P8+D
aZFotoePdqng8Bh4ef0zDnauP6/i/YXyDavXdWwjE+L82JFXpElJSbGCqjTcnkoI
EjZyo72c4+FHaYayr6QXizcDuWSEHrAYa13VFxmkEJfoe3xC3m/Rz3ztOttOXLFg
OwOxfIJe4wKBgQDsf7G/DFLWp4o1jaR78b9P/EtUGHNSxnSN6ILNy+6dZtYae6QF
MjTtc0xxzybHvNHTzXQdUQ0zHHXzurzeAQsfPHNFfZsA9ySHq5XBiYHhS0pGa04u
EVvxw414Ul7JcCNA7y5C1TfAQ5SQHTzP4bSpu9hh4y2l7f9HuxYWt5ExbwKBgQCV
qNubfrR2XNRffWChdsQ+pknRgNvVEBUMLYnWbO+EzzL5uRCCEnOFDNMcD0uegRXJ
cezZag0CbA5oKuoa8QiRlFT0SegoOZRkWRaJBJ1tcyrKzYudnHmTwUeJuqoSEvnu
t+fbRQEInkQ/vaWKf91rP/BpCX+V+qRLjk+2SIrm5QKBgEvz4YHBeXdzxh6ZNTD7
WgzuV1ed2skKBRjJO2vHbmb6aijGhvKfySFSKT7Mj24A92cRXgV4aKRO59qobspo
DMKicXWZ+dIbPjMilS6acLQ/BFaCmnqc9xXG5n3srC7WSVGhm1+5p9LBFhiRfT7I
XGwPNMlIO1ey2qrZJxMrsxjp
-----END PRIVATE KEY-----
""",
    "client_email": "repositorios@repositorios-459911.iam.gserviceaccount.com",
    "client_id": "107371837116786194777",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/repositorios%40repositorios-459911.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

def get_steam_path(config: dict) -> Path:
    """Obter o caminho de instalação do Steam"""
    try:
        if custom_path := config.get("Custom_Steam_Path"):
            return Path(custom_path)

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            return Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except Exception as e:
        print(f"Falha ao obter o caminho do Steam: {str(e)}")
        sys.exit(1)

DEFAULT_CONFIG = {
    "Github_Personal_Token": "",
    "Custom_Steam_Path": "",
    "Debug_Mode": False,
    "Logging_Files": True,
    "Help": "O token pessoal do GitHub pode ser gerado nas configurações de desenvolvedor do GitHub.",
}

def generate_config() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
        print(f"Arquivo de configuração gerado em {CONFIG_FILE}")
    except IOError as e:
        print(f"Falha ao criar o arquivo de configuração: {str(e)}")
        sys.exit(1)

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        generate_config()
        #print(" ")
        #os.system("pause")

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except json.JSONDecodeError:
        print("Arquivo de configuração corrompido, regenerando...")
        generate_config()
        sys.exit(1)
    except Exception as e:
        print(f"Falha ao carregar a configuração: {str(e)}")
        sys.exit(1)

def get_repos_from_drive() -> list:
    """Obtém a lista de repositórios diretamente do Google Drive"""
    try:
        # Autenticação
        creds = service_account.Credentials.from_service_account_info(
            SERVICE_ACCOUNT_INFO,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Criar serviço do Google Drive
        service = build('drive', 'v3', credentials=creds)
        
        # ID do arquivo no Google Drive
        file_id = "1Ht8kx7zHddF6au0RJdJb0pirCZwAm4Ml"
        
        # Obter o conteúdo do arquivo diretamente
        request = service.files().get_media(fileId=file_id)
        content = request.execute().decode('utf-8')
        
        # Processar o conteúdo
        repos = [repo.strip().strip('",') for repo in content.splitlines() if repo.strip()]
        if not repos:
            raise ValueError("Nenhum repositório encontrado no arquivo")
        return repos
        
    except HttpError as e:
        print(f"Erro ao acessar o Google Drive: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao processar repositórios: {str(e)}")
        sys.exit(1)

CLIENT = httpx.AsyncClient(verify=False)
CONFIG = load_config()
DEBUG_MODE = CONFIG.get("Debug_Mode", False)
LOG_FILE = CONFIG.get("Logging_Files", True)
GITHUB_TOKEN = str(CONFIG.get("Github_Personal_Token", ""))
STEAM_PATH = get_steam_path(CONFIG)
IS_CN = True
HEADER = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else None
REPO_LIST = get_repos_from_drive()

def get_client():
    return httpx.AsyncClient()