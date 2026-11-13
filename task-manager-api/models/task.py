from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import selectinload

from database import db
from utils.clock import utcnow

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
VALID_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
# Task encerrada nunca fica atrasada
CLOSED_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
# Prioridades 1 e 2 contam como "alta prioridade" nos relatórios
HIGH_PRIORITY_MAX = 2
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", back_populates="tasks")
    # Excluir a categoria desvincula as tasks (category_id = NULL)
    category = db.relationship("Category", backref="tasks")

    # ---- regras da entidade -------------------------------------------------
    def is_overdue(self, now=None):
        if not self.due_date or self.status in CLOSED_STATUSES:
            return False
        return self.due_date < (now or utcnow())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tags.split(",") if self.tags else [],
        }

    def to_summary_dict(self, now=None):
        """Formato resumido usado em GET /users/<id>/tasks."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": str(self.created_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "overdue": self.is_overdue(now),
        }

    # ---- consultas ----------------------------------------------------------
    @staticmethod
    def _scoped(query, owner_id):
        return query if owner_id is None else query.where(Task.user_id == owner_id)

    @staticmethod
    def _overdue_clause(now):
        return and_(
            Task.due_date.is_not(None),
            Task.due_date < now,
            Task.status.not_in(CLOSED_STATUSES),
        )

    @classmethod
    def find(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def list_with_relations(cls, owner_id=None):
        query = select(cls).options(selectinload(cls.user), selectinload(cls.category)).order_by(cls.id)
        return db.session.execute(cls._scoped(query, owner_id)).scalars().all()

    @classmethod
    def list_for_user(cls, user_id):
        query = select(cls).where(cls.user_id == user_id).order_by(cls.id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        query = select(cls).order_by(cls.id)
        if text:
            pattern = f"%{text}%"
            query = query.where(or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def count(cls, owner_id=None):
        return db.session.scalar(cls._scoped(select(func.count(cls.id)), owner_id))

    @classmethod
    def count_by_status(cls, owner_id=None):
        query = cls._scoped(select(cls.status, func.count(cls.id)).group_by(cls.status), owner_id)
        counts = dict(db.session.execute(query).all())
        return {status: counts.get(status, 0) for status in VALID_STATUSES}

    @classmethod
    def count_by_priority(cls, owner_id=None):
        query = cls._scoped(select(cls.priority, func.count(cls.id)).group_by(cls.priority), owner_id)
        return dict(db.session.execute(query).all())

    @classmethod
    def count_overdue(cls, now, owner_id=None):
        query = cls._scoped(select(func.count(cls.id)).where(cls._overdue_clause(now)), owner_id)
        return db.session.scalar(query)

    @classmethod
    def list_overdue(cls, now, owner_id=None):
        query = cls._scoped(select(cls).where(cls._overdue_clause(now)).order_by(cls.id), owner_id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def count_created_since(cls, since):
        return db.session.scalar(select(func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_done_since(cls, since):
        query = select(func.count(cls.id)).where(cls.status == STATUS_DONE, cls.updated_at >= since)
        return db.session.scalar(query)

    @classmethod
    def totals_by_user(cls):
        """{user_id: (total, concluídas)} em uma única consulta."""
        done = func.sum(case((cls.status == STATUS_DONE, 1), else_=0))
        query = select(cls.user_id, func.count(cls.id), done).group_by(cls.user_id)
        return {user_id: (total, done or 0) for user_id, total, done in db.session.execute(query).all()}

    @classmethod
    def count_by_category(cls, owner_id=None):
        query = select(cls.category_id, func.count(cls.id)).group_by(cls.category_id)
        return dict(db.session.execute(cls._scoped(query, owner_id)).all())
