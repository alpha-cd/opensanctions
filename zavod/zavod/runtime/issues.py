import orjson
from banal import is_mapping
from datetime import datetime
from typing import Any, Dict, Generator, Optional, TypedDict, BinaryIO, cast

from zavod.meta import Dataset
from zavod.archive import dataset_resource_path, get_dataset_resource
from zavod.archive import ISSUES_LOG


class Issue(TypedDict):
    id: int
    timestamp: datetime
    level: str
    module: Optional[str]
    dataset: str
    message: Optional[str]
    entity_id: Optional[str]
    entity_schema: Optional[str]
    data: Dict[str, Any]


class DatasetIssues(object):
    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
        self.path = dataset_resource_path(dataset.name, ISSUES_LOG)
        self.fh: Optional[BinaryIO] = None

    def write(self, event: Dict[str, Any]) -> None:
        if self.fh is None:
            self.fh = open(self.path, "ab")
        data = dict(event)
        for key, value in data.items():
            if hasattr(value, "to_dict"):
                value = value.to_dict()
            if isinstance(value, set):
                value = list(value)
            data[key] = value

        data.pop("_record", None)
        report_issue = data.pop("report_issue", True)
        if not report_issue:
            return
        now = datetime.utcnow().isoformat()
        record = {
            "timestamp": data.pop("timestamp", now),
            "module": data.pop("logger", None),
            "level": data.pop("level"),
            "message": data.pop("event", None),
            "dataset": self.dataset.name,
        }
        entity = data.pop("entity", None)
        if is_mapping(entity):
            record["entity"] = entity
        elif isinstance(entity, str):
            record["entity"] = {"id": entity}
        record["data"] = data
        out = orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE)
        self.fh.write(out)

    def clear(self) -> None:
        self.close()
        self.path.unlink(missing_ok=True)

    def close(self) -> None:
        if self.fh is not None:
            self.fh.close()
        self.fh = None

    def all(self) -> Generator[Issue, None, None]:
        self.close()
        for scope in self.dataset.leaves:
            path = get_dataset_resource(scope, ISSUES_LOG)
            if path is None or not path.is_file():
                continue
            with open(path, "rb") as fh:
                for line in fh:
                    yield cast(Issue, orjson.loads(line))

    def by_level(self) -> Dict[str, int]:
        levels: Dict[str, int] = {}
        for issue in self.all():
            level = issue.get("level")
            if level is not None:
                levels[level] = levels.get(level, 0) + 1
        return levels