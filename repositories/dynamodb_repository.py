import boto3
from botocore.exceptions import ClientError

import logging

logger = logging.getLogger(__name__)


class DynamoDbRepository:
    def __init__(self, table_name):
        """DynamoDB repo, needs a table name to operate on."""
        self._table = boto3.resource("dynamodb").Table(table_name)

    def get(self, week_start):
        response = self._table.get_item(Key={"weekStart": week_start})
        return response.get("Item")

    def list_all(self):
        items = []
        response = self._table.scan()
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        return items

    def save_or_update(self, week):
        try:
            self._table.put_item(Item=week)
        except ClientError as ce:
            logger.exception(f"Error saving week {week.get('weekStart')}: {ce}")
            return False
        return True
