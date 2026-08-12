"""
agregacao.py - Camada GOLD
============================

OBJETIVO DESTA CAMADA
----------------------
A camada gold entrega dados prontos para consumo de negócio: agregações,
métricas, coisas que alguém da área comercial ia querer olhar num
dashboard. Aqui você não lê mais a landing nem a bronze -- só a silver,
que já está limpa.

Entrada:  lakehouse/silver/saida/*.csv
Saída:    lakehouse/gold/saida/resumo_vendas_categoria.csv
          lakehouse/gold/saida/vendas_por_mes.csv
          lakehouse/gold/saida/top_clientes.csv
          lakehouse/gold/saida/resumo_geral.csv

O que cada arquivo de saída deve conter:

  resumo_vendas_categoria.csv
      colunas: categoria, quantidade_vendida, valor_total
      -> uma linha por categoria de produto (junte vendas com produtos
         pelo id_produto), somando quantidade e valor_total.

  vendas_por_mes.csv
      colunas: mes, quantidade_vendas, valor_total
      -> uma linha por mês (formato "AAAA-MM", extraído de data_venda),
         com o número de vendas (linhas) e a soma de valor_total.

  top_clientes.csv
      colunas: id_cliente, nome, valor_total
      -> os 10 clientes que mais gastaram (junte vendas com clientes),
         ORDENADOS do maior para o menor valor_total.

  resumo_geral.csv
      colunas: total_vendas, valor_total_geral, ticket_medio
      -> UMA única linha com: número total de vendas, soma de todos os
         valor_total, e o ticket médio (valor_total_geral / total_vendas,
         arredondado para 2 casas decimais).

Dica: como não usamos pandas, some e agrupe "na mão" com dicionários,
por exemplo: um dict {categoria: {"quantidade": 0, "valor_total": 0.0}}
que você vai incrementando conforme percorre as vendas.
"""

import csv
from collections import defaultdict
from pathlib import Path

LAKEHOUSE = Path(__file__).parent.parent
SILVER_SAIDA = LAKEHOUSE / "silver" / "saida"
SAIDA = Path(__file__).parent / "saida"


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def salvar_csv(registros: list[dict], caminho_saida: Path, colunas: list[str]) -> None:
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        for registro in registros:
            escritor.writerow({coluna: registro.get(coluna, "") for coluna in colunas})


def calcular_resumo_por_categoria(vendas: list[dict], produtos: list[dict]) -> list[dict]:
    produtos_por_id = {}

    for produto in produtos:
        produtos_por_id[int(produto["id_produto"])] = produto

    resumo = defaultdict(lambda: {
        "quantidade": 0,
        "valor_total": 0.0
    })

    for venda in vendas:
        produto = produtos_por_id[int(venda["id_produto"])]
        categoria = produto["categoria"]

        resumo[categoria]["quantidade"] += int(venda["quantidade"])
        resumo[categoria]["valor_total"] += float(venda["valor_total"])

    resultado = []

    for categoria, dados in resumo.items():
        resultado.append({
            "categoria": categoria,
            "quantidade_vendida": dados["quantidade"],
            "valor_total": dados["valor_total"],
        })

    return resultado


def calcular_vendas_por_mes(vendas: list[dict]) -> list[dict]:
    resumo = defaultdict(lambda: {
        "quantidade_vendas": 0,
        "valor_total": 0.0
    })

    for venda in vendas:
        mes = venda["data_venda"][:7]

        resumo[mes]["quantidade_vendas"] += 1
        resumo[mes]["valor_total"] += float(venda["valor_total"])

    resultado = []

    for mes, dados in resumo.items():
        resultado.append({
            "mes": mes,
            "quantidade_vendas": dados["quantidade_vendas"],
            "valor_total": dados["valor_total"],
        })

    return resultado


def calcular_top_clientes(
    vendas: list[dict],
    clientes: list[dict],
    top_n: int = 10
) -> list[dict]:

    clientes_por_id = {}

    for cliente in clientes:
        clientes_por_id[int(cliente["id_cliente"])] = cliente

    gastos = defaultdict(float)

    for venda in vendas:
        id_cliente = int(venda["id_cliente"])
        gastos[id_cliente] += float(venda["valor_total"])

    clientes_ordenados = sorted(
        gastos.items(),
        key=lambda item: item[1],
        reverse=True
    )

    resultado = []

    for id_cliente, valor_total in clientes_ordenados[:top_n]:
        cliente = clientes_por_id[id_cliente]

        resultado.append({
            "id_cliente": id_cliente,
            "nome": cliente["nome"],
            "valor_total": valor_total
        })

    return resultado


def calcular_resumo_geral(vendas: list[dict]) -> list[dict]:
    total_vendas = len(vendas)

    valor_total_geral = 0.0

    for venda in vendas:
        valor_total_geral += float(venda["valor_total"])

    if total_vendas == 0:
        ticket_medio = 0.0
    else:
        ticket_medio = round(valor_total_geral / total_vendas, 2)

    return [{
        "total_vendas": total_vendas,
        "valor_total_geral": valor_total_geral,
        "ticket_medio": ticket_medio,
    }]


def main() -> None:
    vendas = ler_csv(SILVER_SAIDA / "vendas_silver.csv")
    clientes = ler_csv(SILVER_SAIDA / "clientes_silver.csv")
    produtos = ler_csv(SILVER_SAIDA / "produtos_silver.csv")

    resumo_categoria = calcular_resumo_por_categoria(vendas, produtos)
    vendas_por_mes = calcular_vendas_por_mes(vendas)
    top_clientes = calcular_top_clientes(vendas, clientes)
    resumo_geral = calcular_resumo_geral(vendas)

    salvar_csv(resumo_categoria, SAIDA / "resumo_vendas_categoria.csv", ["categoria", "quantidade_vendida", "valor_total"])
    salvar_csv(vendas_por_mes, SAIDA / "vendas_por_mes.csv", ["mes", "quantidade_vendas", "valor_total"])
    salvar_csv(top_clientes, SAIDA / "top_clientes.csv", ["id_cliente", "nome", "valor_total"])
    salvar_csv(resumo_geral, SAIDA / "resumo_geral.csv", ["total_vendas", "valor_total_geral", "ticket_medio"])

    print(f"resumo_vendas_categoria.csv: {len(resumo_categoria)} linhas")
    print(f"vendas_por_mes.csv:          {len(vendas_por_mes)} linhas")
    print(f"top_clientes.csv:            {len(top_clientes)} linhas")
    print(f"resumo_geral.csv:            {len(resumo_geral)} linha")
    print("\nAgora rode: python lakehouse/gold/verificar_gold.py")


if __name__ == "__main__":
    main()
