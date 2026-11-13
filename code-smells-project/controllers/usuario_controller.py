from controllers.acesso import escopo_leitura, exigir_dono_ou_admin
from errors import NotFoundError, UnauthorizedError, ValidationError
from models.usuario_model import validar_novo_usuario


class UsuarioController:
    def __init__(self, usuarios, auth):
        self._usuarios = usuarios
        self._auth = auth

    def listar(self, ator):
        return self._usuarios.listar(somente_id=escopo_leitura(ator))

    def buscar_por_id(self, usuario_id, ator):
        exigir_dono_ou_admin(ator, usuario_id)
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        """Cadastro público: sempre cria cliente; o tipo não vem do payload."""
        valido = validar_novo_usuario(dados)
        return self._usuarios.criar(valido["nome"], valido["email"], valido["senha"])

    def login(self, dados):
        if not isinstance(dados, dict):
            raise ValidationError("Email e senha são obrigatórios")
        email, senha = dados.get("email", ""), dados.get("senha", "")
        if not isinstance(email, str) or not isinstance(senha, str) or not email or not senha:
            raise ValidationError("Email e senha são obrigatórios")
        usuario = self._usuarios.autenticar(email, senha)
        if usuario is None:
            raise UnauthorizedError("Email ou senha inválidos")
        dados_publicos = {campo: usuario[campo] for campo in ("id", "nome", "email", "tipo")}
        return dados_publicos, self._auth.emitir_token(usuario["id"])
