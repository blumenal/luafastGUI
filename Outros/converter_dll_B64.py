import base64, sys

def dll_para_base64_uma_linha(caminho_dll, arquivo_saida=None):
    """
    Converte uma DLL para base64 em uma única linha
    """
    try:
        with open(caminho_dll, 'rb') as f:
            dados_dll = f.read()
        
        base64_dll = base64.b64encode(dados_dll).decode('utf-8')
        
        # Se especificar arquivo de saída, salva
        if arquivo_saida:
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                f.write(base64_dll)
            print(f"DLL convertida e salva em: {arquivo_saida}")
        
        return base64_dll
        
    except Exception as e:
        print(f"Erro ao converter DLL: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python converter_dll.py <caminho_para_dll>")
        sys.exit(1)
    
    caminho_dll = sys.argv[1]
    base64_resultado = dll_para_base64_uma_linha(caminho_dll, "dll_base64.txt")
    
    if base64_resultado:
        print(f"Tamanho do base64: {len(base64_resultado)} caracteres")
        print("Primeiros 100 caracteres:", base64_resultado[:100])