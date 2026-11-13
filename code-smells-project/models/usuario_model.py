"""Usuário: invariantes, hash de senha e acesso parametrizado à tabela `usuarios`."""
import re
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from errors import ConflictError, ValidationError

TIPO_CLIENTE = "cliente"
TIPO_ADMIN = "admin"
SENHA_MIN_CARACTERES = 6
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Lista de permissão: a senha (hash) nunca sai deste módulo.
CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
_SELECT = "SELECT " + ", ".join(CAMPOS_PUBLICOS) + " FROM usuarios"

# Hash válido usado quando o e-mail não existe, para o tempo de resposta não revelar quais e-mails existem.
_HASH_FICTICIO = generate_password_hash("senha-inexistente")


def validar_novo_usuario(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not all(isinstance(v, str) for v in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")
    nome, email = nome.strip(), email.strip().lower()
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not EMAIL_REGEX.match(email):
        raise ValidationError("Email inválido")
    if len(senha) < SENHA_MIN_CARACTERES:
        raise ValidationError(f"Senha deve ter pelo menos {SENHA_MIN_CARACTERES} caracteres")
    return {"nome": nome, "email": email, "senha": senha}


def _to_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS} if row else None


class UsuarioModel:
    def __init__(self, get_conn):
        self._conn = get_conn

    def listar(self, somente_id=None):
        if somente_id is None:
            rows = self._conn().execute(_SELECT + " ORDER BY id").fetchall()
        else:
            rows = self._conn().execute(_SELECT + " WHERE id = ?", (somente_id,)).fetchall()
        return [_to_dict(r) for r in rows]

    def buscar_por_id(self, usuario_id):
        return _to_dict(self._conn().execute(_SELECT + " WHERE id = ?", (usuario_id,)).fetchone())

    def buscar_por_email(self, email):
        return _to_dict(self._conn().execute(_SELECT + " WHERE email = ?", (email,)).fetchone())

    def criar(self, nome, email, senha, tipo=TIPO_CLIENTE):
        try:
            cursor = self._conn().execute(
                "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
        except sqlite3.IntegrityError:
            raise ConflictError("Email já cadastrado")
        return cursor.lastrowid

    def autenticar(self, email, senha):
        """Busca só por e-mail e verifica o hash em código. None se as credenciais não conferem."""
        row = self._conn().execute(
            "SELECT id, senha_hash FROM usuarios WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        senha_hash = row["senha_hash"] if row else _HASH_FICTICIO
        if not check_password_hash(senha_hash, senha) or row is None:
            return None
        return self.buscar_por_id(row["id"])

    def contar(self):
        return self._conn().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
