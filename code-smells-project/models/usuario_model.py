"""Entidade Usuário: hash de senha e serialização sem campo sensível."""

from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db

# `senha` deliberadamente ausente: a serialização é lista de permissão (AP-03).
CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")


def serializar(row):
    if row is None:
        return None
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}


def listar_todos():
    rows = get_db().execute("SELECT * FROM usuarios").fetchall()
    return [serializar(row) for row in rows]


def buscar_por_id(usuario_id):
    row = get_db().execute(
        "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return serializar(row)


def buscar_por_email(email):
    """Retorna a row crua (com hash) — uso interno da autenticação."""
    return get_db().execute(
        "SELECT * FROM usuarios WHERE email = ?", (email,)
    ).fetchone()


def existe_email(email):
    return buscar_por_email(email) is not None


def criar(nome, email, senha, tipo="cliente"):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, generate_password_hash(senha), tipo),
    )
    db.commit()
    return cursor.lastrowid


def verificar_credenciais(email, senha):
    """Busca só por e-mail e confere o hash em Python, nunca no SQL (P-03)."""
    row = buscar_por_email(email)
    if row is None or not check_password_hash(row["senha"], senha):
        return None
    return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
