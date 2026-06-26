from auth import cadastrar_usuario, fazer_login, alterar_senha
from paciente import (
    cadastrar_paciente,
    buscar_paciente_por_cpf,
    listar_comorbidades_disponiveis,
)
from triagem import processar_triagem, listar_sintomas_disponiveis, listar_fila_atendimento
from misc import normalizar_cpf


def tela_login():
    while True:
        print("\n=== Hospital - Login ===")
        print("1. Entrar")
        print("2. Cadastrar novo usuário")
        print("3. Sair")
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            email = input("Email: ").strip()
            senha = input("Senha: ").strip()
            usuario = fazer_login(email, senha)
            if usuario:
                return usuario

        elif opcao == "2":
            nome = input("Nome: ").strip()
            email = input("Email: ").strip()
            senha = input("Senha: ").strip()
            print("Tipo de usuário: 1-Enfermeiro, 2-Médico, 3-Administrador")
            tipo_opcao = input("Opção: ").strip()
            tipos = {"1": "ENFERMEIRO", "2": "MEDICO", "3": "ADMINISTRADOR"}
            tipo_usuario = tipos.get(tipo_opcao, "ENFERMEIRO")
            cadastrar_usuario(nome, email, senha, tipo_usuario)

        elif opcao == "3":
            return None

        else:
            print("Opção inválida!")


def menu_cadastrar_paciente():
    nome = input("Nome do paciente: ").strip()
    cpf = normalizar_cpf(input("CPF: ").strip())
    data_nascimento = input("Data de nascimento (AAAA-MM-DD): ").strip()
    sexo = input("Sexo (Enter para pular): ").strip() or None
    telefone = input("Telefone (Enter para pular): ").strip() or None
    endereco = input("Endereço (Enter para pular): ").strip() or None
    cadastrar_paciente(nome, cpf, data_nascimento, sexo, telefone, endereco)


def menu_buscar_paciente():
    cpf = normalizar_cpf(input("CPF do paciente: ").strip())
    paciente = buscar_paciente_por_cpf(cpf)
    if paciente:
        print(f"\nNome: {paciente['nome']}")
        print(f"CPF: {paciente['cpf']}")
        print(f"Nascimento: {paciente['data_nascimento']}")
        print(f"Sexo: {paciente['sexo']}")
        print(f"Telefone: {paciente['telefone']}")
        print(f"Endereço: {paciente['endereco']}")
    return paciente


def selecionar_ids(itens, campo_id, label):
    # Mostra uma lista (sintomas ou comorbidades) e deixa o usuário escolher
    # vários IDs separados por vírgula.
    if not itens:
        print(f"Nenhum(a) {label} cadastrado(a) no sistema.")
        return []

    print(f"\n--- {label.capitalize()}s disponíveis ---")
    for item in itens:
        print(f"{item[campo_id]} - {item['nome']}")

    escolha = input(
        f"Digite os IDs de {label} separados por vírgula (Enter para nenhum): "
    ).strip()
    if not escolha:
        return []
    return [int(x.strip()) for x in escolha.split(",") if x.strip().isdigit()]


def menu_triagem(id_enfermeiro):
    cpf = normalizar_cpf(input("CPF do paciente para triagem: ").strip())
    paciente = buscar_paciente_por_cpf(cpf)
    if not paciente:
        return

    consciente_input = input("Paciente está consciente? (s/n): ").strip().lower()
    consciente = consciente_input == "s"

    lista_id_sintomas = []
    id_comorbidades = []

    if consciente:
        sintomas = listar_sintomas_disponiveis()
        lista_id_sintomas = selecionar_ids(sintomas, "id_sintoma", "sintoma")

        comorbidades = listar_comorbidades_disponiveis()
        id_comorbidades = selecionar_ids(comorbidades, "id_comorbidade", "comorbidade")

    resultado = processar_triagem(
        paciente["id_paciente"],
        id_enfermeiro,
        lista_id_sintomas,
        id_comorbidades,
        consciente,
    )

    if resultado:
        print("\n=== Resultado da triagem ===")
        print(f"Classificação: {resultado['classificacao']}")
        print(f"Prioridade: {resultado['prioridade']}")
        print(f"Pontuação total: {resultado['pontuacao_total']}")
    else:
        print("Não foi possível processar a triagem.")


def menu_ver_fila():
    fila = listar_fila_atendimento()
    if not fila:
        print("Fila de atendimento vazia.")
        return

    print("\n=== Fila de Atendimento (mais urgente primeiro) ===")
    for paciente in fila:
        print(
            f"{paciente['nome']} | CPF: {paciente['cpf']} | "
            f"Classificação: {paciente['classificacao']} | "
            f"Prioridade: {paciente['prioridade']} | Status: {paciente['status']}"
        )


def menu_principal(usuario):
    while True:
        print(f"\n=== Bem-vindo, {usuario['nome']} ({usuario['tipo_usuario']}) ===")
        print("1. Cadastrar paciente")
        print("2. Buscar paciente por CPF")
        print("3. Registrar triagem")
        print("4. Ver fila de atendimento")
        print("5. Alterar senha")
        print("6. Logout")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            menu_cadastrar_paciente()
        elif opcao == "2":
            menu_buscar_paciente()
        elif opcao == "3":
            menu_triagem(usuario["id_usuario"])
        elif opcao == "4":
            menu_ver_fila()
        elif opcao == "5":
            senha_atual = input("Senha atual: ").strip()
            nova_senha = input("Nova senha: ").strip()
            alterar_senha(usuario["id_usuario"], senha_atual, nova_senha)
        elif opcao == "6":
            print("Sessão encerrada.")
            return
        else:
            print("Opção inválida!")


def main():
    while True:
        usuario = tela_login()
        if usuario is None:
            print("Saindo do sistema...")
            break
        menu_principal(usuario)


if __name__ == "__main__":
    main()
