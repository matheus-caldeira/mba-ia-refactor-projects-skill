"""Acesso a dados de Task. Toda query é parametrizada pelo ORM."""

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import joinedload

from database import db
from models.task import Task


class TaskRepository:
    def __init__(self, session=None):
        self._session = session

    @property
    def session(self):
        return self._session or db.session

    def get(self, task_id):
        return self.session.get(Task, task_id)

    def list_all(self):
        """Lista tasks com user e category carregados antecipadamente (sem N+1)."""
        stmt = select(Task).options(joinedload(Task.user), joinedload(Task.category))
        return self.session.execute(stmt).unique().scalars().all()

    def list_by_user(self, user_id):
        stmt = select(Task).where(Task.user_id == user_id)
        return self.session.execute(stmt).scalars().all()

    def search(self, query=None, status=None, priority=None, user_id=None):
        stmt = select(Task)
        if query:
            like = f'%{query}%'
            stmt = stmt.where(or_(Task.title.like(like), Task.description.like(like)))
        if status:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)
        return self.session.execute(stmt).scalars().all()

    def count(self):
        return self.session.execute(select(func.count(Task.id))).scalar_one()

    def count_by_status(self, status):
        stmt = select(func.count(Task.id)).where(Task.status == status)
        return self.session.execute(stmt).scalar_one()

    def count_by_priority(self, priority):
        stmt = select(func.count(Task.id)).where(Task.priority == priority)
        return self.session.execute(stmt).scalar_one()

    def count_by_category(self, category_id):
        stmt = select(func.count(Task.id)).where(Task.category_id == category_id)
        return self.session.execute(stmt).scalar_one()

    def count_created_since(self, moment):
        stmt = select(func.count(Task.id)).where(Task.created_at >= moment)
        return self.session.execute(stmt).scalar_one()

    def count_completed_since(self, moment):
        stmt = select(func.count(Task.id)).where(
            Task.status == 'done', Task.updated_at >= moment
        )
        return self.session.execute(stmt).scalar_one()

    def list_with_due_date(self):
        """Só as tasks que podem estar atrasadas — filtro no banco, não em Python."""
        stmt = select(Task).where(
            Task.due_date.isnot(None),
            Task.status.notin_(('done', 'cancelled')),
        )
        return self.session.execute(stmt).scalars().all()

    def productivity_by_user(self):
        """Agregação por usuário em uma única query (GROUP BY), sem N+1.

        Devolve ``{user_id: (total, completed)}``.
        """
        completed = func.sum(
            case((Task.status == 'done', 1), else_=0)
        ).label('completed')
        stmt = (
            select(Task.user_id, func.count(Task.id).label('total'), completed)
            .where(Task.user_id.isnot(None))
            .group_by(Task.user_id)
        )
        rows = self.session.execute(stmt).all()
        return {row.user_id: (int(row.total), int(row.completed or 0)) for row in rows}

    def count_grouped_by_user(self):
        stmt = (
            select(Task.user_id, func.count(Task.id))
            .where(Task.user_id.isnot(None))
            .group_by(Task.user_id)
        )
        return dict(self.session.execute(stmt).all())

    def count_grouped_by_category(self):
        stmt = (
            select(Task.category_id, func.count(Task.id))
            .where(Task.category_id.isnot(None))
            .group_by(Task.category_id)
        )
        return dict(self.session.execute(stmt).all())

    def detach_category(self, category_id):
        stmt = update(Task).where(Task.category_id == category_id).values(category_id=None)
        self.session.execute(stmt)

    def add(self, task):
        self.session.add(task)
        return task

    def delete(self, task):
        self.session.delete(task)

    def delete_by_user(self, user_id):
        for task in self.list_by_user(user_id):
            self.session.delete(task)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
