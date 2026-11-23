# RentSmart — Sistema de Orçamento de Locação

Sistema desenvolvido em Python para automatizar a elaboração de orçamentos de locação imobiliária da R.M Imóveis.

## Sobre o projeto

O RentSmart é uma aplicação de console que permite cadastrar informações de clientes e imóveis, calcular valores de aluguel, aplicar regras comerciais e gerar uma projeção financeira dos primeiros 12 meses de contrato.

O objetivo é facilitar a elaboração de orçamentos, tornando os cálculos mais organizados, precisos e automatizados.

## Funcionalidades

- Cadastro do nome do cliente.
- Seleção entre apartamento, casa e estúdio.
- Cálculo automático do aluguel mensal.
- Aplicação de descontos conforme as regras comerciais.
- Cálculo da taxa contratual de R$ 2.000,00.
- Parcelamento da taxa em até 5 vezes.
- Validação das informações inseridas.
- Geração de projeção financeira de 12 meses.
- Exportação dos resultados para arquivo CSV, compatível com Excel.

## Tecnologias utilizadas

- Python 3
- Programação Orientada a Objetos (POO)
- Classes, herança e abstração
- Biblioteca Decimal para cálculos financeiros
- Biblioteca CSV para exportação de dados

## Estrutura do projeto

```text
RentSmart/
│
├── rentsmart.py
├── README.md
└── saida/
    └── projecao_12_meses.csv
```

A pasta `saida` e o arquivo CSV são gerados durante a execução do programa.

## Como executar

1. Instale o Python 3.
2. Baixe ou clone este repositório.
3. Abra o terminal na pasta do projeto.
4. Execute:

```bash
python rentsmart.py
```

5. Informe os dados solicitados pelo programa.
6. Consulte o orçamento gerado e a projeção financeira em CSV.

## Conceitos aplicados

O projeto utiliza Programação Orientada a Objetos para organizar as regras de negócio.

Entre os conceitos aplicados estão:

- Encapsulamento e organização de responsabilidades.
- Herança entre diferentes tipos de imóveis.
- Abstração por meio de classes abstratas.
- Polimorfismo na implementação das regras específicas de cada imóvel.
- Tratamento e validação de entradas.

## Desenvolvido por

Projeto desenvolvido para fins de aprendizado e aplicação prática dos conhecimentos em Python e desenvolvimento de software.
