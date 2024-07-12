from abc import ABC, abstractmethod


class Worker(ABC):
    @abstractmethod
    async def listen(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    async def start(self, item: dict):
        raise NotImplementedError("Subclasses must implement this method.")


class MQueue(ABC):
    @abstractmethod
    async def push(self, item, queue=None):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def pop(self, queue=None):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def len(self):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def set(self, key, value, tll=None):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def expired(self, key, tll):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def get(self, key):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def decr(self, key):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def exists(self, key):
        raise NotImplementedError("Subclasses must implement this method.")
