from database import db
from models.clock import utcnow

VALID_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
CLOSED_STATUSES = ('done', 'cancelled')
MIN_PRIORITY = 1
MAX_PRIORITY = 5


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    @staticmethod
    def validate_status(new_status):
        return new_status in VALID_STATUSES

    @staticmethod
    def validate_priority(p):
        return MIN_PRIORITY <= p <= MAX_PRIORITY

    def is_overdue(self):
        """Regra de negócio única de "atrasada" — antes duplicada em 6 lugares."""
        if not self.due_date:
            return False
        if self.status in CLOSED_STATUSES:
            return False
        return self.due_date < utcnow()

    def days_overdue(self):
        if not self.is_overdue():
            return 0
        return (utcnow() - self.due_date).days

    def set_tags(self, tags):
        if isinstance(tags, list):
            self.tags = ','.join(tags)
        else:
            self.tags = tags
