"""Emissão e verificação de token de acesso assinado com SECRET_KEY."""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from errors import UnauthorizedError

TOKEN_SALT = "loja-auth-token"


class AuthService:
    def __init__(self, secret_key, max_age_seconds):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self._max_age = max_age_seconds

    def emitir_token(self, usuario_id):
        return self._serializer.dumps({"uid": usuario_id})

    def usuario_do_token(self, token):
        try:
            payload = self._serializer.loads(token, max_age=self._max_age)
        except SignatureExpired:
            raise UnauthorizedError("Token expirado")
        except BadSignature:
            raise UnauthorizedError("Token inválido")
        return payload["uid"]
