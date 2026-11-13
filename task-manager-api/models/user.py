import hashlib
import hmac
import re

from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from utils.clock import utcnow

ROLE_USER = "user"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
VALID_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
# Papéis que enxergam e gerenciam as tasks de toda a equipe
SUPERVISOR_ROLES = (ROLE_ADMIN, ROLE_MANAGER)

_LEGACY_MD5 = re.compile(r"^[0-9a-f]{32}$")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # Guarda o hash da senha (scrypt com salt); o nome da coluna é mantido
    # para não exigir migração do banco existente.
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=ROLE_USER)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        # Lista de permissão: o hash da senha nunca sai nas respostas.
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Confere a senha. Hash MD5 legado é aceito uma vez e regravado em scrypt."""
        if not self.password or not raw_password:
            return False
        if _LEGACY_MD5.match(self.password):
            # Migração: hashes MD5 gravados pela versão anterior. Só comparação,
            # nunca geração; o hash é substituído no primeiro login bem-sucedido.
            legacy = hashlib.md5(raw_password.encode()).hexdigest()
            if not hmac.compare_digest(self.password, legacy):
                return False
            self.set_password(raw_password)
            return True
        return check_password_hash(self.password, raw_password)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    def is_supervisor(self):
        return self.role in SUPERVISOR_ROLES

    @classmethod
    def find(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def find_by_email(cls, email):
        return db.session.execute(select(cls).where(cls.email == email)).scalar_one_or_none()

    @classmethod
    def list_all(cls, only_id=None):
        query = select(cls).order_by(cls.id)
        if only_id is not None:
            query = query.where(cls.id == only_id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def count(cls):
        return db.session.scalar(select(func.count(cls.id)))
