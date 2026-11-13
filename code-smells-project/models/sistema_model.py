"""Operações de sistema sobre o banco: ping do health check e reset de manutenção."""

# Ordem respeita as FKs: dependentes primeiro.
TABELAS_RESET = ("itens_pedido", "pedidos", "produtos", "usuarios")


class SistemaModel:
    def __init__(self, get_conn):
        self._conn = get_conn

    def ping(self):
        self._conn().execute("SELECT 1").fetchone()
        return True

    def apagar_tudo(self):
        """Chamar dentro de transação."""
        conn = self._conn()
        for tabela in TABELAS_RESET:
            conn.execute(f"DELETE FROM {tabela}")  # nome vem da allow-list acima, nunca do cliente
