from database import commit, db
from errors import ForbiddenError, UnauthorizedError
from middlewares.auth import issue_token
from models.user import User
from validators import user_validator

INVALID_CREDENTIALS = "Credenciais inválidas"


def login(payload):
    email, password = user_validator.validate_login(payload)
    user = User.find_by_email(email)
    if user is None or not user.check_password(password):
        raise UnauthorizedError(INVALID_CREDENTIALS)
    if not user.active:
        raise ForbiddenError("Usuário inativo")
    if db.session.is_modified(user):  # hash legado regravado no check_password
        commit()
    return {
        "message": "Login realizado com sucesso",
        "user": user.to_dict(),
        "token": issue_token(user),
    }
