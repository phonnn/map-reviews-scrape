from abc import ABC, abstractmethod


class OutputWriter(ABC):
    @abstractmethod
    def write(self, file_path: str, data):
        raise NotImplementedError("Subclasses must implement this method.")
