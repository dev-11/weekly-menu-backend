from services.storage_service import StorageService

from repositories import DynamoDbRepository
import config as c


class ServiceFactory:
    @staticmethod
    def get_storage_service() -> StorageService:
        return StorageService(DynamoDbRepository(c.table_name))
