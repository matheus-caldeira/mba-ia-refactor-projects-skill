from database import transaction
from errors import ConflictError, NotFoundError, ValidationError
from models.produto_model import validar_produto


def _preco_opcional(valor, nome):
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"{nome} inválido")


class ProdutoController:
    def __init__(self, get_conn, produtos):
        self._conn = get_conn
        self._produtos = produtos

    def listar(self):
        return self._produtos.listar()

    def buscar_por_id(self, produto_id):
        produto = self._produtos.buscar_por_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def buscar(self, termo, categoria, preco_min, preco_max):
        return self._produtos.buscar(
            termo or None,
            categoria or None,
            _preco_opcional(preco_min, "preco_min"),
            _preco_opcional(preco_max, "preco_max"),
        )

    def criar(self, dados):
        return self._produtos.criar(validar_produto(dados))

    def atualizar(self, produto_id, dados):
        self.buscar_por_id(produto_id)
        self._produtos.atualizar(produto_id, validar_produto(dados))

    def remover(self, produto_id):
        with transaction(self._conn()):
            self.buscar_por_id(produto_id)
            if self._produtos.possui_pedidos(produto_id):
                raise ConflictError("Produto possui pedidos e não pode ser removido")
            self._produtos.remover(produto_id)
