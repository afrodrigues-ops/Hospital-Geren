from lista_encadeada import ListaEncadeada
from faker import Faker
from misc import normalizar_cpf
import time
import random
class TabelaHash:
    def __init__(self, tam):
        self.tam = tam
        self.listas = [None] * self.tam

    def inserir(self, nome, cpf, idade, urgencia):
        cpf = normalizar_cpf(cpf)  # garante que o CPF seja salvo sempre sem pontos
        index = self.func_hash(cpf)
        if self.listas[index] is None:
            self.listas[index] = ListaEncadeada()

        self.listas[index].inserir(nome, cpf, idade, urgencia)
        self.listas[index].ordenar()

    def excluir(self, cpf):
        cpf = normalizar_cpf(cpf)  # aceita CPF com ou sem pontos
        index = self.func_hash(cpf)
        if self.listas[index] is None:
            return

        if self.listas[index].excluir(cpf):
            print("Paciente excluído!")
            if self.listas[index].primeiro is None:
                self.listas[index] = None

    def busca(self, cpf):
        cpf = normalizar_cpf(cpf)  # aceita CPF com ou sem pontos
        # Usa a função hash para ir direto ao índice correto — O(1) no acesso
        index = self.func_hash(cpf)
        if self.listas[index] is None:
            return False

        self.listas[index].pesquisar(cpf)
        return True

    def busca_sem_hash(self, cpf):
        cpf = normalizar_cpf(cpf)  # aceita CPF com ou sem pontos
        # Percorre toda a tabela sequencialmente, sem usar o índice hash — O(n)
        for i in range(self.tam):
            if self.listas[i] is not None:
                atual = self.listas[i].primeiro
                while atual is not None:
                    if atual.cpf == cpf:
                        return True
                    atual = atual.proximo
        return False

    def busca_silenciosa(self, cpf):
        # Busca COM hash sem imprimir — usada apenas para medir tempo
        cpf = normalizar_cpf(cpf)
        index = self.func_hash(cpf)
        if self.listas[index] is None:
            return False
        return self.listas[index].pesquisar_silencioso(cpf)

    def busca_sem_hash_silenciosa(self, cpf):
        # Busca SEM hash sem imprimir — usada apenas para medir tempo
        cpf = normalizar_cpf(cpf)
        for i in range(self.tam):
            if self.listas[i] is not None:
                atual = self.listas[i].primeiro
                while atual is not None:
                    if atual.cpf == cpf:
                        return True
                    atual = atual.proximo
        return False

    def func_hash(self, cpf):
        # Usa o valor numérico completo do CPF (não a soma dos dígitos)
        # A soma de 11 dígitos nunca passa de 99, então soma % 500 nunca
        # usava os índices 100-499. int(cpf) % tam distribui por toda a tabela.
        return int(cpf) % self.tam

    def mostrar_tabela(self):
        # Verifica se há algum paciente cadastrado antes de exibir
        tem_paciente = any(self.listas[i] is not None for i in range(self.tam))
        if not tem_paciente:
            print("Nenhum paciente cadastrado ainda.")
            return

        # Exibe apenas os índices que possuem pacientes
        for ind in range(self.tam):
            if self.listas[ind] is not None:
                print(f"Índice {ind + 1}: ", end=" ")
                self.listas[ind].mostrar_lista()

