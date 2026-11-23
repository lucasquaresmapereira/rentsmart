"""
RentSmart - Sistema de Orçamento de Locação da R.M Imóveis
===========================================================

Aplicação de console que:
  1. coleta as características da locação (com validação);
  2. aplica automaticamente as regras comerciais da imobiliária;
  3. exibe um orçamento detalhado (aluguel mensal e taxa contratual separados);
  4. gera um CSV com a projeção dos 12 primeiros meses de contrato.

Organização das classes (Programação Orientada a Objetos):

    ItemOrcamento        -> uma linha do orçamento (descrição + valor)
    Imovel (abstrata)    -> contrato comum a todo imóvel (template method)
      ├─ ImovelResidencial (abstrata) -> regras comuns a casa e apartamento
      │    ├─ Apartamento -> desconto de 5% para clientes sem crianças
      │    └─ Casa
      └─ Estudio         -> regra própria de estacionamento
    Orcamento            -> combina imóvel + taxa contratual + parcelamento
    LinhaProjecao        -> um mês da projeção de 12 meses
    ExportadorCSV        -> grava a projeção em arquivo CSV
    InterfaceConsole     -> entrada/saída com o usuário (leitura validada)

Execução:  python rentsmart.py
"""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes de negócio (único lugar a alterar caso as regras mudem)
# ---------------------------------------------------------------------------
TAXA_CONTRATUAL = Decimal("2000.00")
MAX_PARCELAS_TAXA = 5
DESCONTO_SEM_CRIANCAS = Decimal("0.05")  # 5% (somente apartamentos)
MESES_PROJECAO = 12
VALOR_GARAGEM_RESIDENCIAL = Decimal("300.00")
PACOTE_ESTUDIO = Decimal("250.00")  # pacote inicial de 2 vagas
VAGAS_NO_PACOTE_ESTUDIO = 2
VAGA_ADICIONAL_ESTUDIO = Decimal("60.00")
MAX_VAGAS_ESTUDIO = 10


# ---------------------------------------------------------------------------
# Funções utilitárias de dinheiro
# ---------------------------------------------------------------------------
def arredondar(valor: Decimal) -> Decimal:
    """Arredonda para centavos (meio para cima), evitando erros de float."""
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formatar_brl(valor: Decimal) -> str:
    """Formata como moeda brasileira: 1234.5 -> 'R$ 1.234,50'."""
    texto = f"{arredondar(valor):,.2f}"
    texto = texto.replace(",", "#").replace(".", ",").replace("#", ".")
    return f"R$ {texto}"


def formatar_csv(valor: Decimal) -> str:
    """Número com vírgula decimal, sem símbolo (padrão do Excel em pt-BR)."""
    return f"{arredondar(valor):.2f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Item do orçamento
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ItemOrcamento:
    """Uma linha do detalhamento do aluguel."""

    descricao: str
    valor: Decimal


# ---------------------------------------------------------------------------
# Hierarquia de imóveis
# ---------------------------------------------------------------------------
class Imovel(ABC):
    """
    Classe base abstrata. Define o *algoritmo* de composição do aluguel
    (template method) e deixa para as subclasses os detalhes de cada regra.
    """

    NOME: str = ""
    ALUGUEL_BASE: Decimal = Decimal("0")

    def itens_aluguel(self) -> list[ItemOrcamento]:
        """Monta a lista de itens que compõem o aluguel (antes do desconto)."""
        itens = [ItemOrcamento(f"Aluguel-base ({self.descricao()})", self.ALUGUEL_BASE)]
        itens.extend(self._adicionais())
        return itens

    @abstractmethod
    def descricao(self) -> str:
        """Texto curto descrevendo o imóvel escolhido."""

    @abstractmethod
    def _adicionais(self) -> list[ItemOrcamento]:
        """Adicionais (quartos, garagem...) específicos de cada tipo."""

    def percentual_desconto(self) -> Decimal:
        """Por padrão, imóveis não têm desconto. Subclasses podem sobrescrever."""
        return Decimal("0")

    def aluguel_bruto(self) -> Decimal:
        return sum((i.valor for i in self.itens_aluguel()), Decimal("0"))

    def valor_desconto(self) -> Decimal:
        return arredondar(self.aluguel_bruto() * self.percentual_desconto())

    def aluguel_mensal(self) -> Decimal:
        return arredondar(self.aluguel_bruto() - self.valor_desconto())


class ImovelResidencial(Imovel, ABC):
    """Regras comuns a casas e apartamentos: 1 ou 2 quartos e garagem opcional."""

    ADICIONAL_2_QUARTOS: Decimal = Decimal("0")

    def __init__(self, quartos: int, tem_garagem: bool):
        if quartos not in (1, 2):
            raise ValueError("Quantidade de quartos deve ser 1 ou 2.")
        self.quartos = quartos
        self.tem_garagem = tem_garagem

    def descricao(self) -> str:
        return f"{self.NOME} de {self.quartos} quarto{'s' if self.quartos == 2 else ''}"

    def _adicionais(self) -> list[ItemOrcamento]:
        itens: list[ItemOrcamento] = []
        if self.quartos == 2:
            itens.append(ItemOrcamento("Adicional de 2º quarto", self.ADICIONAL_2_QUARTOS))
        if self.tem_garagem:
            itens.append(ItemOrcamento("Vaga de garagem", VALOR_GARAGEM_RESIDENCIAL))
        return itens


class Apartamento(ImovelResidencial):
    NOME = "Apartamento"
    ALUGUEL_BASE = Decimal("700.00")
    ADICIONAL_2_QUARTOS = Decimal("200.00")

    def __init__(self, quartos: int, tem_garagem: bool, tem_criancas: bool):
        super().__init__(quartos, tem_garagem)
        self.tem_criancas = tem_criancas

    def percentual_desconto(self) -> Decimal:
        # 5% sobre o aluguel já com os adicionais, somente se NÃO há crianças.
        return Decimal("0") if self.tem_criancas else DESCONTO_SEM_CRIANCAS


class Casa(ImovelResidencial):
    NOME = "Casa"
    ALUGUEL_BASE = Decimal("900.00")
    ADICIONAL_2_QUARTOS = Decimal("250.00")


class Estudio(Imovel):
    """Estúdio: sem quartos; estacionamento por pacote de 2 vagas + adicionais."""

    NOME = "Estúdio"
    ALUGUEL_BASE = Decimal("1200.00")

    def __init__(self, vagas: int):
        if not 0 <= vagas <= MAX_VAGAS_ESTUDIO:
            raise ValueError(f"Vagas devem estar entre 0 e {MAX_VAGAS_ESTUDIO}.")
        self.vagas = vagas

    def descricao(self) -> str:
        return self.NOME

    def _adicionais(self) -> list[ItemOrcamento]:
        itens: list[ItemOrcamento] = []
        if self.vagas >= 1:
            # Pacote inicial (cobre até 2 vagas)
            itens.append(
                ItemOrcamento(f"Pacote de estacionamento ({VAGAS_NO_PACOTE_ESTUDIO} vagas)", PACOTE_ESTUDIO)
            )
        extras = self.vagas - VAGAS_NO_PACOTE_ESTUDIO
        if extras > 0:
            itens.append(
                ItemOrcamento(
                    f"Vagas adicionais ({extras} x {formatar_brl(VAGA_ADICIONAL_ESTUDIO)})",
                    VAGA_ADICIONAL_ESTUDIO * extras,
                )
            )
        return itens


# ---------------------------------------------------------------------------
# Orçamento e projeção
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LinhaProjecao:
    mes: int
    aluguel: Decimal
    parcela_taxa: Decimal
    total_mes: Decimal
    total_acumulado: Decimal


class Orcamento:
    """Reúne o imóvel, a taxa contratual e o parcelamento escolhido."""

    def __init__(self, cliente: str, imovel: Imovel, parcelas_taxa: int):
        if not 1 <= parcelas_taxa <= MAX_PARCELAS_TAXA:
            raise ValueError(f"Parcelas da taxa devem estar entre 1 e {MAX_PARCELAS_TAXA}.")
        self.cliente = cliente
        self.imovel = imovel
        self.parcelas_taxa = parcelas_taxa

    # --- cálculos -----------------------------------------------------------
    def valores_parcelas_taxa(self) -> list[Decimal]:
        """Divide a taxa em parcelas; a última absorve a diferença de centavos."""
        base = arredondar(TAXA_CONTRATUAL / self.parcelas_taxa)
        parcelas = [base] * self.parcelas_taxa
        parcelas[-1] = arredondar(TAXA_CONTRATUAL - base * (self.parcelas_taxa - 1))
        return parcelas

    def projecao_12_meses(self) -> list[LinhaProjecao]:
        parcelas = self.valores_parcelas_taxa()
        aluguel = self.imovel.aluguel_mensal()
        linhas: list[LinhaProjecao] = []
        acumulado = Decimal("0")
        for mes in range(1, MESES_PROJECAO + 1):
            parcela = parcelas[mes - 1] if mes <= len(parcelas) else Decimal("0.00")
            total = arredondar(aluguel + parcela)
            acumulado += total
            linhas.append(LinhaProjecao(mes, aluguel, parcela, total, arredondar(acumulado)))
        return linhas

    def total_primeiro_ano(self) -> Decimal:
        return self.projecao_12_meses()[-1].total_acumulado

    # --- apresentação -------------------------------------------------------
    def resumo(self) -> str:
        larg = 58
        linha = "=" * larg
        sep = "-" * larg
        saida = [linha, "RENTSMART - ORÇAMENTO DE LOCAÇÃO".center(larg), "R.M Imóveis".center(larg), linha]
        saida.append(f"Cliente: {self.cliente}")
        saida.append(f"Imóvel : {self.imovel.descricao()}")
        saida.append(sep)
        saida.append("COMPOSIÇÃO DO ALUGUEL MENSAL")
        for item in self.imovel.itens_aluguel():
            saida.append(self._linha(item.descricao, formatar_brl(item.valor), larg))
        saida.append(self._linha("Subtotal", formatar_brl(self.imovel.aluguel_bruto()), larg))
        if self.imovel.percentual_desconto() > 0:
            pct = int(self.imovel.percentual_desconto() * 100)
            saida.append(
                self._linha(f"Desconto de {pct}% (sem crianças)", "- " + formatar_brl(self.imovel.valor_desconto()), larg)
            )
        saida.append(self._linha("ALUGUEL MENSAL", formatar_brl(self.imovel.aluguel_mensal()), larg))
        saida.append(sep)
        saida.append("TAXA CONTRATUAL (cobrada à parte do aluguel)")
        saida.append(self._linha("Valor da taxa", formatar_brl(TAXA_CONTRATUAL), larg))
        parcelas = self.valores_parcelas_taxa()
        if self.parcelas_taxa == 1:
            saida.append(self._linha("Condição", f"à vista ({formatar_brl(parcelas[0])})", larg))
        else:
            saida.append(
                self._linha("Condição", f"{self.parcelas_taxa}x de {formatar_brl(parcelas[0])}", larg)
            )
            if parcelas[-1] != parcelas[0]:
                saida.append(self._linha("Última parcela", formatar_brl(parcelas[-1]), larg))
        saida.append(sep)
        saida.append(self._linha("TOTAL DO 1º MÊS (aluguel + 1ª parcela)", formatar_brl(self.projecao_12_meses()[0].total_mes), larg))
        saida.append(self._linha("TOTAL DOS 12 MESES (aluguel + taxa)", formatar_brl(self.total_primeiro_ano()), larg))
        saida.append(linha)
        return "\n".join(saida)

    @staticmethod
    def _linha(esquerda: str, direita: str, largura: int) -> str:
        espacos = max(1, largura - len(esquerda) - len(direita))
        return f"{esquerda}{' ' * espacos}{direita}"


# ---------------------------------------------------------------------------
# Exportação CSV
# ---------------------------------------------------------------------------
class ExportadorCSV:
    """
    Grava a projeção em CSV.
    Formato pensado para abrir direto no Excel em português: separador ';',
    vírgula decimal e codificação UTF-8 com BOM.
    """

    CABECALHO = ["Mes", "Aluguel", "Parcela_Taxa_Contratual", "Total_do_Mes", "Total_Acumulado"]

    @classmethod
    def gerar(cls, orcamento: Orcamento, caminho: str | Path) -> Path:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        linhas = orcamento.projecao_12_meses()
        with caminho.open("w", newline="", encoding="utf-8-sig") as arq:
            escritor = csv.writer(arq, delimiter=";")
            escritor.writerow(cls.CABECALHO)
            for l in linhas:
                escritor.writerow(
                    [l.mes, formatar_csv(l.aluguel), formatar_csv(l.parcela_taxa),
                     formatar_csv(l.total_mes), formatar_csv(l.total_acumulado)]
                )
            escritor.writerow(
                ["TOTAL",
                 formatar_csv(sum((l.aluguel for l in linhas), Decimal("0"))),
                 formatar_csv(sum((l.parcela_taxa for l in linhas), Decimal("0"))),
                 formatar_csv(linhas[-1].total_acumulado),
                 formatar_csv(linhas[-1].total_acumulado)]
            )
        return caminho


# ---------------------------------------------------------------------------
# Interface de console (leitura com validação)
# ---------------------------------------------------------------------------
class InterfaceConsole:
    """Responsável apenas por conversar com o usuário e montar o Orcamento."""

    @staticmethod
    def ler_texto(pergunta: str) -> str:
        while True:
            valor = input(pergunta).strip()
            if valor:
                return valor
            print("  ! O campo não pode ficar vazio.")

    @staticmethod
    def ler_inteiro(pergunta: str, minimo: int, maximo: int) -> int:
        while True:
            bruto = input(pergunta).strip()
            try:
                numero = int(bruto)
            except ValueError:
                print("  ! Digite um número inteiro.")
                continue
            if minimo <= numero <= maximo:
                return numero
            print(f"  ! Digite um valor entre {minimo} e {maximo}.")

    @classmethod
    def ler_sim_nao(cls, pergunta: str) -> bool:
        while True:
            resposta = input(pergunta + " [s/n]: ").strip().lower()
            if resposta in ("s", "sim"):
                return True
            if resposta in ("n", "nao", "não"):
                return False
            print("  ! Responda com 's' ou 'n'.")

    def montar_imovel(self) -> Imovel:
        print("\nTipos de imóvel:")
        print("  1) Apartamento  2) Casa  3) Estúdio")
        tipo = self.ler_inteiro("Escolha o tipo (1-3): ", 1, 3)

        if tipo == 3:
            vagas = self.ler_inteiro(f"Quantas vagas de estacionamento (0-{MAX_VAGAS_ESTUDIO})? ", 0, MAX_VAGAS_ESTUDIO)
            return Estudio(vagas)

        quartos = self.ler_inteiro("Número de quartos (1 ou 2): ", 1, 2)
        garagem = self.ler_sim_nao("Deseja vaga de garagem?")
        if tipo == 1:
            tem_criancas = self.ler_sim_nao("Há crianças que morarão no imóvel?")
            return Apartamento(quartos, garagem, tem_criancas)
        return Casa(quartos, garagem)

    def montar_orcamento(self) -> Orcamento:
        print("=" * 58)
        print("RENTSMART - R.M Imóveis".center(58))
        print("=" * 58)
        cliente = self.ler_texto("Nome do cliente: ")
        imovel = self.montar_imovel()
        print(f"\nA taxa contratual é de {formatar_brl(TAXA_CONTRATUAL)} (até {MAX_PARCELAS_TAXA}x).")
        parcelas = self.ler_inteiro(f"Em quantas parcelas (1-{MAX_PARCELAS_TAXA})? ", 1, MAX_PARCELAS_TAXA)
        return Orcamento(cliente, imovel, parcelas)


def main() -> None:
    interface = InterfaceConsole()
    orcamento = interface.montar_orcamento()
    print()
    print(orcamento.resumo())
    caminho = ExportadorCSV.gerar(orcamento, Path("saida") / "projecao_12_meses.csv")
    print(f"\nProjeção de 12 meses salva em: {caminho}")


if __name__ == "__main__":
    main()
