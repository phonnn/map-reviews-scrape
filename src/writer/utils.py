from typing import Iterable

from flask_sqlalchemy.model import Model

from src.datastore.utils import model_to_list


def convert_data_to_csv(func):
    def wrapper(self, file_path: str, data: Iterable[Model]):
        converted_data = [model_to_list(item, 'url', 'location', 'reviewer', 'content') for item in data]
        return func(self, file_path, converted_data)

    return wrapper
