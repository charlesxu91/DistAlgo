from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, Tuple


class MemoryCheckpointStore:
    def __init__(self):
        self._entries: Dict[Tuple[str, int], Any] = {}

    def save(self, algorithm: str, iteration: int, state: Any) -> None:
        self._entries[(algorithm, iteration)] = state

    def load(self, algorithm: str, iteration: int) -> Any:
        return self._entries[(algorithm, iteration)]

    def exists(self, algorithm: str, iteration: int) -> bool:
        return (algorithm, iteration) in self._entries


class FileCheckpointStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, algorithm: str, iteration: int, state: Any) -> None:
        path = self._path(algorithm, iteration)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump(state, handle)

    def load(self, algorithm: str, iteration: int) -> Any:
        with self._path(algorithm, iteration).open("rb") as handle:
            return pickle.load(handle)

    def exists(self, algorithm: str, iteration: int) -> bool:
        return self._path(algorithm, iteration).exists()

    def _path(self, algorithm: str, iteration: int) -> Path:
        return self.root / algorithm / f"iteration-{iteration}.pkl"
