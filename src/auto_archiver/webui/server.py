from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


DATA_FILE = Path("collections.json")

app = FastAPI(title="Auto Archiver Collection Manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class UrlItem(BaseModel):
    url: str
    status: Optional[str] = None


class Collection(BaseModel):
    name: str
    items: List[UrlItem] = []


@app.on_event("startup")
def ensure_data_file() -> None:
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]")


def _load() -> list[dict]:
    return json.loads(DATA_FILE.read_text())


def _save(data: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2))


@app.get("/collections")
def list_collections() -> list[dict]:
    return _load()


@app.post("/collections")
def create_collection(collection: Collection) -> dict:
    data = _load()
    data.append(collection.dict())
    _save(data)
    return collection.dict()


@app.get("/collections/{index}")
def get_collection(index: int) -> dict:
    data = _load()
    if index >= len(data):
        raise HTTPException(status_code=404, detail="Collection not found")
    return data[index]


@app.put("/collections/{index}")
def update_collection(index: int, collection: Collection) -> dict:
    data = _load()
    if index >= len(data):
        raise HTTPException(status_code=404, detail="Collection not found")
    data[index] = collection.dict()
    _save(data)
    return collection.dict()


@app.delete("/collections/{index}")
def delete_collection(index: int) -> dict:
    data = _load()
    if index >= len(data):
        raise HTTPException(status_code=404, detail="Collection not found")
    removed = data.pop(index)
    _save(data)
    return removed


static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":  # pragma: no cover
    main()
