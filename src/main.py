import sqlite3
import secrets
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Header, Request, BackgroundTasks
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

class RegisterBody(BaseModel):
    name: str

class FlashcardBody(BaseModel):
    category: str
    question: str
    answer: str

conn = sqlite3.connect("flashcards.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        owner TEXT NOT NULL
    )
""")

conn.commit()

def create_api_key(owner: str) -> str:
    key = secrets.token_hex(16)
    cursor.execute(
        "INSERT INTO api_keys (key, owner) VALUES (?, ?)",
        (key, owner)
    )
    conn.commit()
    return key

async def verify_api_key(x_api_key: str=Header()):
    cursor.execute("SELECT * FROM api_keys WHERE key = ?", (x_api_key,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return result

def get_api_key(request: Request) -> str:
    return request.headers.get("x-api-key", "unknown")

limiter = Limiter(key_func=get_api_key)
app.state.limiter = limiter


@app.post("/register")
async def register(body: RegisterBody, background_tasks: BackgroundTasks):
    key = create_api_key(body.name)
    background_tasks.add_task(log_request, "new api key", "a key")
    return {"api_key": key, "message": "Save this key. You won't be able to see this again"}


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later"}
    )

def log_request(route: str, api_key: str):
    with open("requests.log", "a") as f:
        f.write(f"{datetime.datetime.now()} - {route} - {api_key}\n")

@app.get("/secret-data", dependencies=[Depends(verify_api_key)])
async def get_secret_data():
    return {"message": "You have access!"}

@app.get("/flashcards", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_flashcards(request: Request):
    cursor.execute("SELECT * FROM flashcards")
    flashcards = cursor.fetchall()
    return [{"id": f[0], "category": f[1], "question": f[2], "answer": f[3]} for f in flashcards]

@app.post("/flashcards", dependencies=[Depends(verify_api_key)])
async def add_flashcard(flashcard: FlashcardBody):
    cursor.execute(
        "INSERT INTO flashcards (category, question, answer) VALUES (?, ?, ?)",
        (flashcard.category, flashcard.question, flashcard.answer)
    )
    conn.commit()
    return {"message": "Added Flashcard!"}

@app.delete("/flashcards/{flashcard_id}", dependencies = [Depends(verify_api_key)])
async def delete_flashcard(flashcard_id: int, background_tasks: BackgroundTasks):
    cursor.execute(
        "SELECT * FROM flashcards WHERE id = ?", (flashcard_id,)
    )
    flashcard = cursor.fetchone()

    if flashcard is None:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    cursor.execute("DELETE FROM flashcards WHERE id = ?", (flashcard_id,))
    conn.commit()

    background_tasks.add_task(log_request, "Deleted flashcard", str(flashcard_id))

    return {"message": f"Deleted Flashcard {flashcard_id}!"}

def main():
    import uvicorn
    uvicorn.run("resolution_week5_Asurant.main:app", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()