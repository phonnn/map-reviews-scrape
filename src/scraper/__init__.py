from abc import ABC, abstractmethod


class IScraper(ABC):
    @abstractmethod
    async def scrape(self, url) -> dict:
        raise NotImplementedError("Subclasses must implement this method.")
