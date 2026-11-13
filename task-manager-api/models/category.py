from sqlalchemy import func, select

from database import db
from utils.clock import utcnow

DEFAULT_COLOR = "#000000"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": str(self.created_at),
        }

    @classmethod
    def find(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def list_all(cls):
        return db.session.execute(select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def count(cls):
        return db.session.scalar(select(func.count(cls.id)))
