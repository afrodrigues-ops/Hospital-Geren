from tabela_hash import TabelaHash
from misc import normalizar_cpf
from faker import Faker
import time
import random

fake = Faker('pt_BR')  # configura para nomes e dados em português do Brasil

def cadastrar_aleatorios(fila, quantidade=995):
    # Guarda os CPFs inseridos para usar nos testes de tempo depois
    cpfs_inseridos = []

    for i in range(quantidade):
        nome     = fake.name()             # nome brasileiro gerado automaticamente
        cpf      = fake.cpf()              # CPF no formato 000.000.000-00
        idade    = random.randint(1, 99)  # idade entre 1 e 99 anos
        urgencia = random.randint(0, 4)   # nível 0-4, igual ao seu sistema

        fila.inserir(nome, cpf, idade, urgencia)
        cpfs_inseridos.append(cpf)

    print(f"{quantidade} pacientes cadastrados com sucesso!")
    return cpfs_inseridos


def medir_tempo_busca(fila, cpf):
    REPETICOES = 1000  # repete a busca 1000 vezes para garantir precisao estatistica

    # --- Busca COM hash ---
    # Usa versao silenciosa para nao imprimir mensagens durante as 1000 repeticoes
    inicio = time.perf_counter()
    for _ in range(REPETICOES):
        fila.busca_silenciosa(cpf)
    fim = time.perf_counter()
    media_com = (fim - inicio) / REPETICOES

    # --- Busca SEM hash ---
    inicio = time.perf_counter()
    for _ in range(REPETICOES):
        fila.busca_sem_hash_silenciosa(cpf)
    fim = time.perf_counter()
    media_sem = (fim - inicio) / REPETICOES

    print("\n========== Resultado: Tempo de Busca ==========")
    print(f"  CPF buscado: {cpf}")
    print(f"  Com hash:    {media_com:.8f} segundos")
    print(f"  Sem hash:    {media_sem:.8f} segundos")

    if media_com > 0:
        print(f"  A busca com hash foi {media_sem / media_com:.1f}x mais rapida!")
    print("================================================\n")

def main():
    menu()


def menu():
    fila = TabelaHash(500)
    legenda = {"1": (4), "2": (3), "3": (2), "4": (1), "5": (0)}
    cpfs_cadastrados = []  # guarda os CPFs dos cadastros em massa para uso na medição

    while True:
        print("\n")
        print("1. Cadastrar Paciente")
        print("2. Mostrar Fila de Pacientes")
        print("3. Excluir Paciente da Fila")
        print("4. Pesquisar Paciente")
        print("5. Cadastrar múltiplos pacientes")
        print("6. Medir tempo médio de busca (com e sem hash)")
        print("7. Sair")

        opcao = input("Escolha uma opção: ")

        if opcao == "1":
            nome = input("Nome do paciente: ")
            cpf = input("Digite o CPF: ")

            # Valida o CPF: remove pontos e traço e verifica se tem exatamente 11 dígitos
            cpf_numeros = normalizar_cpf(cpf)
            
            if not cpf_numeros.isdigit() or len(cpf_numeros) != 11:
                print("CPF inválido! O CPF deve conter exatamente 11 números.")
            else:
                # --- BLOCO COLOADO AQUI PARA PROTEGER CONTRA ENTERS EM BRANCO ---
                while True:
                    idade_input = input("Idade: ").strip()
                    if idade_input.isdigit():
                        idade = int(idade_input)
                        break
                    print("Por favor, digite uma idade válida (apenas números)!")
                # -----------------------------------------------------------------

                print(
                    "Urgência: 1-Emergência, 2-Muito Urgente, 3-Urgente, 4-Pouco Urgente, 5-Não Urgente"
                )
                op = input("Opção: ")

                if op in legenda:
                    nivel_urgencia = legenda[op]
                    fila.inserir(nome, cpf_numeros, idade, nivel_urgencia)
                    print("Paciente cadastrado!")
                else:
                    print("Opção de urgência inválida!")

        elif opcao == "2":
            fila.mostrar_tabela()

        elif opcao == "3":
            cpf_excluir = input("Digite o cpf para excluir: ")
            cpf_excluir_limpo = normalizar_cpf(cpf_excluir)
            fila.excluir(cpf_excluir_limpo)

        elif opcao == "4":
            cpf_busca = input("Digite o cpf para pesquisar: ")
            cpf_busca_limpo = normalizar_cpf(cpf_busca)
            if not fila.busca(cpf_busca_limpo):
                print("Paciente não encontrado ou lista está vazia")

        elif opcao == "5":
            qtd = input("Quantos pacientes deseja cadastrar? (Enter para 995): ")
            if qtd.strip() == "":
                qtd = 995
            else:
                qtd = int(qtd)
            cpfs_cadastrados = cadastrar_aleatorios(fila, qtd)

        elif opcao == "6":
            if len(cpfs_cadastrados) == 0:
                print("Cadastre multiplos pacientes primeiro (opcao 5)!")
            else:
                cpf_teste = input("Digite o CPF para comparar o tempo de busca: ")
                cpf_teste_limpo = normalizar_cpf(cpf_teste)
                medir_tempo_busca(fila, cpf_teste_limpo)

        elif opcao == "7":
            break


if __name__ == "__main__":
    menu()
