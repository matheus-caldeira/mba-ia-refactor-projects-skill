"""Acesso a dados de User. Toda query é parametrizada pelo ORM."""

from sqlalchemy import func, select

from database import db
from models.user import User


class UserRepository:
    def __init__(self, session=None):
        self._session = session

    @property
    def session(self):
        return self._session or db.session

    def get(self, user_id):
        return self.session.get(User, user_id)

    def list_all(self):
        return self.session.execute(select(User)).scalars().all()

    def find_by_email(self, email):
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalars().first()

    def count(self):
        return self.session.execute(select(func.count(User.id))).scalar_one()

    def add(self, user):
        self.session.add(user)
        return user

    def delete(self, user):
        self.session.delete(user)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
