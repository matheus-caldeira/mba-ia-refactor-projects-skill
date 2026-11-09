"""Casos de uso de Category. Sem HTTP, sem SQL cru."""

import re

from errors import NotFoundError, ValidationError
from models.category import DEFAULT_COLOR, Category

COLOR_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 300


class CategoryController:
    def __init__(self, category_repository, task_repository):
        self._categories = category_repository
        self._tasks = task_repository

    def list(self):
        task_counts = self._tasks.count_grouped_by_category()
        result = []
        for c in self._categories.list_all():
            data = c.to_dict()
            data['task_count'] = task_counts.get(c.id, 0)
            result.append(data)
        return result

    def create(self, data):
        if not data:
            raise ValidationError('Dados inválidos')

        category = Category()
        category.name = self._validate_name(data.get('name'))
        category.description = self._validate_description(data.get('description', ''))
        category.color = self._validate_color(data.get('color', DEFAULT_COLOR))

        self._categories.add(category)
        self._categories.commit()
        return category.to_dict()

    def update(self, category_id, data):
        category = self._require_category(category_id)
        if not data:
            raise ValidationError('Dados inválidos')

        if 'name' in data:
            category.name = self._validate_name(data['name'])
        if 'description' in data:
            category.description = self._validate_description(data['description'])
        if 'color' in data:
            category.color = self._validate_color(data['color'])

        self._categories.commit()
        return category.to_dict()

    def delete(self, category_id):
        category = self._require_category(category_id)
        self._tasks.detach_category(category_id)
        self._categories.delete(category)
        self._categories.commit()
        return {'message': 'Categoria deletada'}

    def _require_category(self, category_id):
        category = self._categories.get(category_id)
        if not category:
            raise NotFoundError('Categoria não encontrada')
        return category

    @staticmethod
    def _validate_name(name):
        if not name or not isinstance(name, str):
            raise ValidationError('Nome é obrigatório')
        if len(name) > MAX_NAME_LENGTH:
            raise ValidationError('Nome muito longo')
        return name

    @staticmethod
    def _validate_description(description):
        if description is None:
            return ''
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError('Descrição inválida')
        return description

    @staticmethod
    def _validate_color(color):
        if not isinstance(color, str) or not COLOR_PATTERN.match(color):
            raise ValidationError('Cor inválida. Use o formato #RRGGBB')
        return color
