"""Produto: invariantes da entidade e acesso parametrizado à tabela `produtos`."""
from numbers import Real

from errors import ValidationError

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
NOME_MIN_CARACTERES = 2
NOME_MAX_CARACTERES = 200

CAMPOS_PUBLICOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")
_SELECT = "SELECT " + ", ".join(CAMPOS_PUBLICOS) + " FROM produtos"


def _eh_numero(valor):
    return isinstance(valor, Real) and not isinstance(valor, bool)


def validar_produto(dados):
    """Valida o payload de criação/atualização (mesma regra nos dois casos)."""
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao") or ""
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if not _eh_numero(preco):
        raise ValidationError("Preço deve ser numérico")
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        raise ValidationError("Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN_CARACTERES:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX_CARACTERES:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def _to_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS} if row else None


class ProdutoModel:
    def __init__(self, get_conn):
        self._conn = get_conn

    def listar(self):
        return [_to_dict(r) for r in self._conn().execute(_SELECT + " ORDER BY id").fetchall()]

    def buscar_por_id(self, produto_id):
        return _to_dict(self._conn().execute(_SELECT + " WHERE id = ?", (produto_id,)).fetchone())

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        sql = _SELECT + " WHERE 1=1"
        params = []
        if termo:
            sql += " AND (nome LIKE ? OR descricao LIKE ?)"
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            sql += " AND categoria = ?"
            params.append(categoria)
        if preco_min is not None:
            sql += " AND preco >= ?"
            params.append(preco_min)
        if preco_max is not None:
            sql += " AND preco <= ?"
            params.append(preco_max)
        return [_to_dict(r) for r in self._conn().execute(sql + " ORDER BY id", params).fetchall()]

    def criar(self, dados):
        cursor = self._conn().execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (dados["nome"], dados["descricao"], dados["preco"], dados["estoque"], dados["categoria"]),
        )
        return cursor.lastrowid

    def atualizar(self, produto_id, dados):
        self._conn().execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (dados["nome"], dados["descricao"], dados["preco"], dados["estoque"], dados["categoria"], produto_id),
        )

    def remover(self, produto_id):
        self._conn().execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def possui_pedidos(self, produto_id):
        row = self._conn().execute(
            "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
        ).fetchone()
        return row is not None

    def buscar_por_ids(self, ids):
        ids = list(ids)
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self._conn().execute(_SELECT + f" WHERE id IN ({placeholders})", ids).fetchall()
        return {row["id"]: _to_dict(row) for row in rows}

    def baixar_estoque(self, produto_id, quantidade):
        """Baixa atômica: só decrementa se houver saldo. Retorna False se não havia."""
        cursor = self._conn().execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
        return cursor.rowcount == 1

    def devolver_estoque(self, produto_id, quantidade):
        self._conn().execute(
            "UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id)
        )

    def contar(self):
        return self._conn().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
