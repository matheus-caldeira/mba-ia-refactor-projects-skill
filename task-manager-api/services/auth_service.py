"""Emissão e verificação de tokens de sessão.

Substitui o antigo ``'fake-jwt-token-' + id``, que era forjável por qualquer um.
O token agora é assinado com a ``SECRET_KEY`` e tem expiração — usa
``itsdangerous``, dependência que já acompanha o Flask (nenhum pacote novo).
"""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from errors import UnauthorizedError

_SALT = 'task-manager-auth'


class AuthService:
    def __init__(self, settings, user_repository):
        self._settings = settings
        self._users = user_repository
        self._serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt=_SALT)

    def issue_token(self, user):
        return self._serializer.dumps({'user_id': user.id, 'role': user.role})

    def verify_token(self, token):
        """Devolve o usuário do token, ou lança ``UnauthorizedError``."""
        if not token:
            raise UnauthorizedError('Token ausente')
        try:
            payload = self._serializer.loads(
                token, max_age=self._settings.TOKEN_TTL_SECONDS
            )
        except SignatureExpired:
            raise UnauthorizedError('Token expirado')
        except BadSignature:
            raise UnauthorizedError('Token inválido')

        user = self._users.get(payload.get('user_id'))
        if user is None or not user.active:
            raise UnauthorizedError('Token inválido')
        return user

    def authenticate(self, email, password):
        """Valida credenciais. Mensagem única para e-mail inexistente ou senha errada."""
        user = self._users.find_by_email(email) if email else None
        if user is None or not user.check_password(password):
            raise UnauthorizedError('Credenciais inválidas')
        return user
