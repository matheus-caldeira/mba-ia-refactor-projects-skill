"""Relatório de vendas e política de desconto por faixa de faturamento."""

# (limiar de faturamento, percentual de desconto), do maior para o menor
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))
CASAS_DECIMAIS = 2


def calcular_desconto(faturamento):
    for limiar, percentual in FAIXAS_DESCONTO:
        if faturamento > limiar:
            return faturamento * percentual
    return 0


class RelatorioService:
    def __init__(self, pedidos):
        self._pedidos = pedidos

    def vendas(self):
        resumo = self._pedidos.resumo_vendas()
        total_pedidos, faturamento = resumo["total_pedidos"], resumo["faturamento"]
        desconto = calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, CASAS_DECIMAIS),
            "desconto_aplicavel": round(desconto, CASAS_DECIMAIS),
            "faturamento_liquido": round(faturamento - desconto, CASAS_DECIMAIS),
            "pedidos_pendentes": resumo["pendentes"],
            "pedidos_aprovados": resumo["aprovados"],
            "pedidos_cancelados": resumo["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, CASAS_DECIMAIS) if total_pedidos > 0 else 0,
        }
