from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class InsertOneResult:
    inserted_id: Any


@dataclass
class InsertManyResult:
    inserted_ids: list[Any]


@dataclass
class UpdateResult:
    matched_count: int
    modified_count: int
    upserted_id: Any = None


@dataclass
class DeleteResult:
    deleted_count: int


def _get_nested(document: dict, dotted_key: str) -> Any:
    value: Any = document
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _set_nested(document: dict, dotted_key: str, value: Any) -> None:
    target = document
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def _matches_operator(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "$gt":
        return actual is not None and actual > expected
    if operator == "$gte":
        return actual is not None and actual >= expected
    if operator == "$lt":
        return actual is not None and actual < expected
    if operator == "$lte":
        return actual is not None and actual <= expected
    if operator == "$ne":
        return actual != expected
    if operator == "$in":
        return actual in expected
    if operator == "$nin":
        return actual not in expected
    return False


def _matches(document: dict, query: dict | None) -> bool:
    if not query:
        return True

    for key, expected in query.items():
        if key == "$or":
            return any(_matches(document, option) for option in expected)
        if key == "$and":
            return all(_matches(document, option) for option in expected)

        actual = _get_nested(document, key)
        if isinstance(expected, dict) and any(str(op).startswith("$") for op in expected):
            if not all(_matches_operator(actual, op, value) for op, value in expected.items()):
                return False
        elif actual != expected:
            return False
    return True


def _base_document_from_filter(query: dict | None) -> dict:
    document: dict = {}
    for key, value in (query or {}).items():
        if key.startswith("$") or isinstance(value, dict):
            continue
        _set_nested(document, key, copy.deepcopy(value))
    return document


class MemoryCursor:
    def __init__(self, documents: list[dict]):
        self._documents = documents

    def __iter__(self):
        return iter(copy.deepcopy(self._documents))

    def __len__(self) -> int:
        return len(self._documents)

    def sort(self, key_or_list, direction: int | None = None) -> "MemoryCursor":
        if isinstance(key_or_list, list):
            sort_keys = key_or_list
        else:
            sort_keys = [(key_or_list, direction or 1)]
        documents = self._documents
        for key, order in reversed(sort_keys):
            documents = sorted(
                documents,
                key=lambda item: (_get_nested(item, key) is None, _get_nested(item, key)),
                reverse=order == -1,
            )
        return MemoryCursor(documents)

    def limit(self, count: int) -> "MemoryCursor":
        if count and count > 0:
            return MemoryCursor(self._documents[:count])
        return MemoryCursor(self._documents)


class MemoryCollection:
    def __init__(self, database: "MemoryDatabase", name: str):
        self.database = database
        self.name = name

    @property
    def _documents(self) -> list[dict]:
        return self.database._collections.setdefault(self.name, [])

    def insert_one(self, document: dict) -> InsertOneResult:
        with self.database._lock:
            stored = copy.deepcopy(document)
            stored.setdefault("_id", uuid.uuid4().hex)
            self._documents.append(stored)
            return InsertOneResult(stored["_id"])

    def insert_many(self, documents: list[dict]) -> InsertManyResult:
        inserted_ids = []
        for document in documents:
            inserted_ids.append(self.insert_one(document).inserted_id)
        return InsertManyResult(inserted_ids)

    def find(self, query: dict | None = None, *args, sort=None, limit: int = 0, **kwargs) -> MemoryCursor:
        with self.database._lock:
            matches = [copy.deepcopy(doc) for doc in self._documents if _matches(doc, query)]
        cursor = MemoryCursor(matches)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return cursor

    def find_one(self, query: dict | None = None, *args, sort=None, **kwargs) -> dict | None:
        cursor = self.find(query, sort=sort, limit=1)
        documents = list(cursor)
        return documents[0] if documents else None

    def count_documents(self, query: dict | None = None) -> int:
        with self.database._lock:
            return sum(1 for doc in self._documents if _matches(doc, query))

    def delete_many(self, query: dict | None = None) -> DeleteResult:
        with self.database._lock:
            original_count = len(self._documents)
            self.database._collections[self.name] = [
                doc for doc in self._documents if not _matches(doc, query)
            ]
            return DeleteResult(original_count - len(self.database._collections[self.name]))

    def update_one(self, query: dict, update: dict, upsert: bool = False) -> UpdateResult:
        return self._update(query, update, upsert=upsert, many=False)

    def update_many(self, query: dict, update: dict, upsert: bool = False) -> UpdateResult:
        return self._update(query, update, upsert=upsert, many=True)

    def replace_one(self, query: dict, replacement: dict, upsert: bool = False) -> UpdateResult:
        with self.database._lock:
            for index, document in enumerate(self._documents):
                if _matches(document, query):
                    next_document = copy.deepcopy(replacement)
                    next_document.setdefault("_id", document.get("_id", uuid.uuid4().hex))
                    self._documents[index] = next_document
                    return UpdateResult(1, 1)
            if upsert:
                stored = copy.deepcopy(replacement)
                stored.setdefault("_id", _base_document_from_filter(query).get("_id", uuid.uuid4().hex))
                self._documents.append(stored)
                return UpdateResult(0, 0, stored["_id"])
        return UpdateResult(0, 0)

    def _update(self, query: dict, update: dict, upsert: bool, many: bool) -> UpdateResult:
        matched = 0
        modified = 0
        with self.database._lock:
            for document in self._documents:
                if not _matches(document, query):
                    continue
                matched += 1
                self._apply_update(document, update)
                modified += 1
                if not many:
                    break

            if matched == 0 and upsert:
                new_document = _base_document_from_filter(query)
                new_document.setdefault("_id", uuid.uuid4().hex)
                self._apply_update(new_document, update, include_set_on_insert=True)
                self._documents.append(new_document)
                return UpdateResult(0, 0, new_document["_id"])

        return UpdateResult(matched, modified)

    def _apply_update(self, document: dict, update: dict, include_set_on_insert: bool = False) -> None:
        if not any(key.startswith("$") for key in update):
            document.clear()
            document.update(copy.deepcopy(update))
            document.setdefault("_id", uuid.uuid4().hex)
            return

        for key, value in update.get("$set", {}).items():
            _set_nested(document, key, copy.deepcopy(value))

        for key, value in update.get("$inc", {}).items():
            current = _get_nested(document, key) or 0
            _set_nested(document, key, current + value)

        for key, value in update.get("$min", {}).items():
            current = _get_nested(document, key)
            _set_nested(document, key, value if current is None else min(current, value))

        for key, value in update.get("$max", {}).items():
            current = _get_nested(document, key)
            _set_nested(document, key, value if current is None else max(current, value))

        if include_set_on_insert:
            for key, value in update.get("$setOnInsert", {}).items():
                if _get_nested(document, key) is None:
                    _set_nested(document, key, copy.deepcopy(value))


class MemoryDatabase:
    def __init__(self):
        self._collections: dict[str, list[dict]] = {}
        self._lock = threading.RLock()

    def __getitem__(self, name: str) -> MemoryCollection:
        return MemoryCollection(self, name)

    def list_collection_names(self) -> list[str]:
        return sorted(self._collections)
