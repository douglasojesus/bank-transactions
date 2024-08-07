import subprocess
import requests

# Lista de contêineres que você deseja obter o endereço IP
container_names = [
    'projeto-app1-1',
    'projeto-app2-1',
    'projeto-app3-1'
]

# Dicionário para armazenar os resultados
container_ips = []

# Loop sobre cada nome de contêiner e executar o comando docker inspect
for container_name in container_names:
    command = r"docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' " + container_name
    try:
        # Executa o comando usando subprocess
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        
        # Armazena o resultado no dicionário
        container_ips.append(result.stdout.strip())

    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar comando para '{container_name}': {e.stderr.strip()}")

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

urls = [
    f"http://{container_ips[0]}:8000/",
    f"http://{container_ips[1]}:8001/",
    f"http://{container_ips[2]}:8002/",
]

names = ['bancoA', 'bancoB', 'bancoC']

def exibe_urls(urls):
    if container_ips[0] != '':
        for i in range(len(urls)):
            print(names[i] + ': ' + urls[i])
    else:
        print("O seu contêiner não está em execução. Verifique isso antes de usar o menu.")

def registra_bancos(url, data):
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Bancos registrados com sucesso!")
        else:
            print(f"Falha ao registrar bancos. Código de status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Erro durante a requisição: {e}")

def menu():
    print("""
(1) Limpar todos os cadastros de clientes e bancos.
(2) Configurar todos os 3 bancos para registrar os outros bancos.
(3) Criar 3 clientes para teste nos 3 bancos (com mil reais na conta de todos os Douglas).
""")
    return int(input('>>> '))

while True:
    exibe_urls(urls)
    opcao = menu()
    if opcao == 1:
        for i in range(len(urls)):
            command = 'curl ' + urls[i] + 'flush/'
            print(command)
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        print("Tudo limpo!")

    if opcao == 2:
        for i in range(len(urls)):
            url = urls[i] + "configure/" 
            if i == 0:
                data = {
                    'name[]': ['this', 'bancoB', 'bancoC'],  # Lista de nomes dos bancos
                    'ip[]': [container_ips[0], container_ips[1], container_ips[2]],  # Lista de IPs dos bancos
                    'port[]': ['8000', '8001', '8002']  # Lista de portas dos bancos
                }
            elif i == 1:
                data = {
                    'name[]': ['bancoA', 'this', 'bancoC'],  # Lista de nomes dos bancos
                    'ip[]': [container_ips[0], container_ips[1], container_ips[2]],  # Lista de IPs dos bancos
                    'port[]': ['8000', '8001', '8002']  # Lista de portas dos bancos
                }
            elif i == 2:
                data = {
                    'name[]': ['bancoA', 'bancoB', 'this'],  # Lista de nomes dos bancos
                    'ip[]': [container_ips[0], container_ips[1], container_ips[2]],  # Lista de IPs dos bancos
                    'port[]': ['8000', '8001', '8002']  # Lista de portas dos bancos
                }
            registra_bancos(url, data)
        print("Tudo configurado!")

    if opcao == 3:
        for i in range(len(urls)):
            command = 'curl ' + urls[i] + 'create_test/'
            print(command)
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        print("Tudo criado!")