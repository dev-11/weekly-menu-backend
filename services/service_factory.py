from services.storage_service import StorageService
from services.unfurl_service import UnfurlService

from repositories import DynamoDbRepository
import config as c


class ServiceFactory:
    @staticmethod
    def get_storage_service() -> StorageService:
        return StorageService(DynamoDbRepository(c.table_name))

    @staticmethod
    def get_unfurl_service() -> UnfurlService:
        return UnfurlService()
