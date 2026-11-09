from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.clock import utcnow

ROLES = ('user', 'admin', 'manager')


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # Guarda o hash derivado por KDF com salt — nunca a senha, nunca MD5.
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        """Serialização por lista de permissão: o hash de senha nunca sai daqui."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        if not self.password:
            return False
        try:
            return check_password_hash(self.password, pwd)
        except ValueError:
            # Hash em formato legado/desconhecido (ex.: MD5 gravado antes da
            # refatoração). Tratado como credencial inválida: o hash antigo é
            # considerado comprometido e exige redefinição de senha.
            return False

    def is_admin(self):
        return self.role == 'admin'
