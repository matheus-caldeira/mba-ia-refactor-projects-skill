"""Orquestra os casos de uso de Produto. Sem SQL e sem HTTP."""

from middlewares.errors import NotFoundError, ValidationError
from models import produto_model
from models.produto_model import CATEGORIAS_VALIDAS


def _validar(dados):
    if not dados:
        raise ValidationError("Dados inválidos")
    for campo, rotulo in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")

    nome = dados["nome"]
    preco = dados["preco"]
    estoque = dados["estoque"]

    if not isinstance(preco, (int, float)) or isinstance(preco, bool):
        raise ValidationError("Preço deve ser numérico")
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        raise ValidationError("Estoque deve ser inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if not isinstance(nome, str) or len(nome) < 2:
        raise ValidationError("Nome muito curto")
    if len(nome) > 200:
        raise ValidationError("Nome muito longo")

    return {
        "nome": nome,
        "descricao": dados.get("descricao", ""),
        "preco": preco,
        "estoque": estoque,
        "categoria": dados.get("categoria", "geral"),
    }


def listar():
    return produto_model.listar_todos()


def buscar(produto_id):
    produto = produto_model.buscar_por_id(produto_id)
    if produto is None:
        raise NotFoundError("Produto não encontrado")
    return produto


def _validar_categoria(categoria):
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(
            "Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS))
        )


def criar(dados):
    limpo = _validar(dados)
    _validar_categoria(limpo["categoria"])
    return produto_model.criar(**limpo)


def atualizar(produto_id, dados):
    if produto_model.buscar_por_id(produto_id) is None:
        raise NotFoundError("Produto não encontrado")
    limpo = _validar(dados)
    _validar_categoria(limpo["categoria"])
    produto_model.atualizar(produto_id, **limpo)
    return True


def deletar(produto_id):
    if produto_model.buscar_por_id(produto_id) is None:
        raise NotFoundError("Produto não encontrado")
    produto_model.deletar(produto_id)
    return True


def pesquisar(termo, categoria, preco_min, preco_max):
    def _para_float(valor, rotulo):
        if valor in (None, ""):
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            raise ValidationError(f"{rotulo} deve ser numérico")

    return produto_model.buscar(
        termo=termo,
        categoria=categoria,
        preco_min=_para_float(preco_min, "preco_min"),
        preco_max=_para_float(preco_max, "preco_max"),
    )
