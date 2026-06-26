from auth import cadastrar_usuario, fazer_login, alterar_senha
from paciente import (
    cadastrar_paciente,
    buscar_paciente_por_cpf,
    listar_comorbidades_disponiveis,
)
from triagem import (
    processar_triagem,
    listar_fluxogramas_disponiveis,
    listar_discriminadores_do_fluxograma,
    listar_fila_atendimento,
)
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


def selecionar_id_unico(itens, campo_id, label):
    # Mostra uma lista (ex.: fluxogramas) e deixa o usuário escolher 1 item.
    if not itens:
        print(f"Nenhum(a) {label} cadastrado(a) no sistema.")
        return None

    print(f"\n--- {label.capitalize()}s disponíveis ---")
    for item in itens:
        print(f"{item[campo_id]} - {item['nome']}")

    escolha = input(f"Digite o ID d{'o' if label[-1]!='a' else 'a'} {label}: ").strip()
    if not escolha.isdigit():
        print("ID inválido.")
        return None
    return int(escolha)


def selecionar_ids(itens, campo_id, label):
    # Mostra uma lista (ex.: comorbidades) e deixa o usuário escolher
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


def percorrer_discriminadores(id_fluxograma):
    """
    Apresenta os discriminadores do fluxograma escolhido, nível por nível,
    do mais urgente (EMERGÊNCIA) para o menos urgente (POUCO URGENTE).
    Segue a lógica real do Manchester: ao primeiro discriminador
    confirmado, já para e retorna — não precisa perguntar o resto.

    Se o enfermeiro não confirmar nenhum em nenhum nível, retorna lista
    vazia (cai em NÃO URGENTE).
    """
    discriminadores = listar_discriminadores_do_fluxograma(id_fluxograma)
    if not discriminadores:
        print("Esse fluxograma não tem discriminadores cadastrados.")
        return []

    nivel_atual = None
    for d in discriminadores:
        if d["classificacao"] != nivel_atual:
            nivel_atual = d["classificacao"]
            print(f"\n-- Nível: {nivel_atual} --")

        resposta = input(f"  {d['pergunta']}? (s/n, Enter para pular): ").strip().lower()
        if resposta == "s":
            print(f"  >> Confirmado: \"{d['pergunta']}\" — classificação: {nivel_atual}")
            return [d["id_discriminador"]]

    print("\nNenhum discriminador confirmado nos fluxogramas avaliados.")
    return []


def menu_triagem(id_enfermeiro):
    cpf = normalizar_cpf(input("CPF do paciente para triagem: ").strip())
    paciente = buscar_paciente_por_cpf(cpf)
    if not paciente:
        return

    consciente_input = input("Paciente está consciente? (s/n): ").strip().lower()
    consciente = consciente_input == "s"

    id_fluxograma = None
    lista_id_discriminadores_confirmados = []

    if consciente:
        fluxogramas = listar_fluxogramas_disponiveis()
        id_fluxograma = selecionar_id_unico(fluxogramas, "id_fluxograma", "fluxograma")
        if id_fluxograma is None:
            print("Triagem cancelada: é necessário escolher um fluxograma.")
            return

        lista_id_discriminadores_confirmados = percorrer_discriminadores(id_fluxograma)

    comorbidades = listar_comorbidades_disponiveis()
    id_comorbidades = selecionar_ids(comorbidades, "id_comorbidade", "comorbidade")

    resultado = processar_triagem(
        paciente["id_paciente"],
        id_enfermeiro,
        id_fluxograma,
        lista_id_discriminadores_confirmados,
        id_comorbidades,
        consciente,
    )

    if resultado:
        print("\n=== Resultado da triagem ===")
        print(f"Classificação base (Manchester): {resultado['classificacao_base']}")
        if resultado["agravado_por_comorbidade"]:
            print(f"Agravado por comorbidade -> Classificação final: {resultado['classificacao']}")
        else:
            print(f"Classificação final: {resultado['classificacao']}")
        print(f"Prioridade: {resultado['prioridade']}")
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
