from paciente import Paciente

class ListaEncadeada:
    def __init__(self):
        self.primeiro = None

    def lista_vazia(self):
        return self.primeiro is None

    def mostrar_lista(self):
        if self.lista_vazia():
            return

        atual = self.primeiro
        print("\n--- Fila de Atendimento ---")
        while atual is not None:
            atual.mostrar_no()
            print("-" * 20)
            atual = atual.proximo

    def inserir(self, nome, cpf, idade, urgencia):
        novo = Paciente(nome, cpf, idade, urgencia)
        novo.proximo = None
        atual = self.primeiro

        if self.lista_vazia():
            self.primeiro = novo
            return

        while atual.proximo is not None:
            atual = atual.proximo

        atual.proximo = novo

    def excluir(self, valor):
        atual = self.primeiro

        if self.lista_vazia():
            print("Lista está vazia, operação não permitida.")
            return False

        # Caso o paciente a remover seja o primeiro (cabeça) da lista
        if atual.cpf == valor:
            self.primeiro = atual.proximo
            return True

        # Procura o nó ANTERIOR ao que tem o cpf buscado
        while atual.proximo is not None and atual.proximo.cpf != valor:
            atual = atual.proximo

        if atual.proximo is None:
            print("Paciente não existe na lista")
            return False

        atual.proximo = atual.proximo.proximo
        return True

    def pesquisar(self, cpf_busca):
        atual = self.primeiro
        posicao = 0

        if self.lista_vazia():
            print("Lista está vazia.")
            return False

        while atual is not None:
            if atual.cpf == cpf_busca:
                print(f"\nPaciente com cpf {cpf_busca} encontrado na posição {posicao}!")
                atual.mostrar_no()
                return True

            atual = atual.proximo
            posicao += 1

        print(f"Paciente com cpf {cpf_busca} não encontrado na lista.")
        return False

    def pesquisar_silencioso(self, cpf_busca):
        # Igual ao pesquisar, mas sem imprimir nada — usado apenas para medir tempo
        atual = self.primeiro
        while atual is not None:
            if atual.cpf == cpf_busca:
                return True
            atual = atual.proximo
        return False

    def ordenar(self):
        if self.lista_vazia():
            return

        tam = self.tam_lista()
        aux_i = 0
        aux_u = 0
        aux_n = ""

        if tam == 1:
            return

        for i in range(tam):
            atual = self.primeiro
            for j in range(tam - 1):
                if atual.proximo is None:
                    break

                if verificar_preferencia(
                    atual.idade,
                    atual.proximo.idade,
                    atual.urgencia,
                    atual.proximo.urgencia,
                ):
                    aux_i = atual.idade
                    aux_u = atual.urgencia
                    aux_n = atual.nome
                    aux_c = atual.cpf
                    atual.idade = atual.proximo.idade
                    atual.urgencia = atual.proximo.urgencia
                    atual.nome = atual.proximo.nome
                    atual.cpf = atual.proximo.cpf
                    atual.proximo.idade = aux_i
                    atual.proximo.cpf = aux_c
                    atual.proximo.urgencia = aux_u
                    atual.proximo.nome = aux_n
                atual = atual.proximo

    def tam_lista(self):
        atual = self.primeiro
        i = 0

        if self.lista_vazia():
            return i

        while atual.proximo is not None:
            i += 1
            atual = atual.proximo
        i += 1
        return i


def verificar_preferencia(idade1, idade2, urgencia1, urgencia2):
    if idade2 > 65 and idade1 < 65:
        if urgencia2 > urgencia1 or urgencia2 == urgencia1:
            return True
        else:
            return False

    elif urgencia2 > urgencia1:
        return True

    else:
        return False
