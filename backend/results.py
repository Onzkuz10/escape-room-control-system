"""Persistent game results, kept separately from settings and transient events."""
import json
from pathlib import Path


class ResultStore:
    def __init__(self, path: Path):
        self.path = path
        self.results = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []

    def add(self, result):
        records = [*self.results, result]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)
        self.results = records
