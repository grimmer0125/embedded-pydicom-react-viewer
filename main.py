from fastapi import FastAPI
# from Typing import Optional
from typing import Optional
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/build", StaticFiles(directory="build"), name="build")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}
