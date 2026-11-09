"""Acesso a dados de Category. Toda query é parametrizada pelo ORM."""

from sqlalchemy import func, select

from database import db
from models.category import Category


class CategoryRepository:
    def __init__(self, session=None):
        self._session = session

    @property
    def session(self):
        return self._session or db.session

    def get(self, category_id):
        return self.session.get(Category, category_id)

    def list_all(self):
        return self.session.execute(select(Category)).scalars().all()

    def count(self):
        return self.session.execute(select(func.count(Category.id))).scalar_one()

    def add(self, category):
        self.session.add(category)
        return category

    def delete(self, category):
        self.session.delete(category)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
