from repositories import DynamoDbRepository


class StorageService:
    def __init__(self, repo: DynamoDbRepository):
        """Service to store/read week menus."""
        self._repo = repo

    def get_week(self, week_start):
        return self._repo.get(week_start)

    def list_weeks(self):
        return self._repo.list_all()

    def save_week(self, week):
        return self._repo.save_or_update(week)
