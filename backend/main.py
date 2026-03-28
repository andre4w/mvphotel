import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from dotenv import load_dotenv

from database import init_db, get_db
from models import HotelRegister, HotelLogin, HotelUpdate, ChatMessage, AnswerQuestion, Token
from auth import hash_password, verify_password, create_access_token, get_current_hotel
from scraper import scrape_website
from ai import get_chat_response

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Hotel AI Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=Token)
async def register(data: HotelRegister, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT id FROM hotels WHERE email = ?", (data.email,)) as cur:
        if await cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

    hotel_token = str(uuid.uuid4()).replace("-", "")
    pw_hash = hash_password(data.password)

    async with db.execute(
        """INSERT INTO hotels (name, email, phone, website_url, password_hash, hotel_token)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data.name, data.email, data.phone, data.website_url, pw_hash, hotel_token),
    ) as cur:
        hotel_id = cur.lastrowid

    await db.commit()
    token = create_access_token({"sub": hotel_id})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
async def login(data: HotelLogin, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM hotels WHERE email = ?", (data.email,)) as cur:
        hotel = await cur.fetchone()

    if not hotel or not verify_password(data.password, hotel["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": hotel["id"]})
    return {"access_token": token, "token_type": "bearer"}


# ─── Hotel profile ────────────────────────────────────────────────────────────

@app.get("/hotel/me")
async def get_me(hotel=Depends(get_current_hotel)):
    return {
        "id": hotel["id"],
        "name": hotel["name"],
        "email": hotel["email"],
        "phone": hotel["phone"],
        "website_url": hotel["website_url"],
        "hotel_token": hotel["hotel_token"],
        "scan_status": hotel["scan_status"],
        "scan_error": hotel["scan_error"],
    }


@app.put("/hotel/me")
async def update_me(
    data: HotelUpdate,
    hotel=Depends(get_current_hotel),
    db: aiosqlite.Connection = Depends(get_db),
):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [hotel["id"]]
    await db.execute(f"UPDATE hotels SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return {"message": "Updated successfully"}


# ─── Scraping ─────────────────────────────────────────────────────────────────

async def run_scrape(hotel_id: int, website_url: str):
    """Background task: scrape and store hotel website content."""
    async with aiosqlite.connect(os.getenv("DATABASE_URL", "./hotel_platform.db")) as db:
        # Mark as running
        await db.execute(
            "UPDATE hotels SET scan_status = 'running', scan_error = NULL WHERE id = ?",
            (hotel_id,),
        )
        await db.commit()

        try:
            pages = await scrape_website(website_url)

            if not pages:
                await db.execute(
                    "UPDATE hotels SET scan_status = 'error', scan_error = ? WHERE id = ?",
                    ("No pages could be scraped. Check that the URL is accessible.", hotel_id),
                )
                await db.commit()
                return

            # Delete old content
            await db.execute("DELETE FROM scraped_content WHERE hotel_id = ?", (hotel_id,))

            # Insert new content
            for page in pages:
                await db.execute(
                    "INSERT INTO scraped_content (hotel_id, url, title, content) VALUES (?, ?, ?, ?)",
                    (hotel_id, page["url"], page["title"], page["content"]),
                )

            await db.execute(
                "UPDATE hotels SET scan_status = 'done', scan_error = NULL WHERE id = ?",
                (hotel_id,),
            )
            await db.commit()

        except Exception as e:
            await db.execute(
                "UPDATE hotels SET scan_status = 'error', scan_error = ? WHERE id = ?",
                (str(e)[:500], hotel_id),
            )
            await db.commit()


@app.post("/hotel/scan")
async def start_scan(
    background_tasks: BackgroundTasks,
    hotel=Depends(get_current_hotel),
    db: aiosqlite.Connection = Depends(get_db),
):
    if not hotel["website_url"]:
        raise HTTPException(status_code=400, detail="No website URL configured")
    if hotel["scan_status"] == "running":
        raise HTTPException(status_code=409, detail="Scan already in progress")

    background_tasks.add_task(run_scrape, hotel["id"], hotel["website_url"])
    return {"message": "Scan started"}


@app.get("/hotel/scan/status")
async def scan_status(hotel=Depends(get_current_hotel), db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "SELECT COUNT(*) as count FROM scraped_content WHERE hotel_id = ?", (hotel["id"],)
    ) as cur:
        row = await cur.fetchone()
    pages_count = row["count"] if row else 0

    return {
        "status": hotel["scan_status"],
        "error": hotel["scan_error"],
        "pages_scraped": pages_count,
    }


# ─── Snippet ──────────────────────────────────────────────────────────────────

@app.get("/hotel/snippet")
async def get_snippet(hotel=Depends(get_current_hotel)):
    snippet = f"""<!-- Hotel AI Chat Widget -->
<script>
  window.HotelAIConfig = {{ hotelToken: "{hotel['hotel_token']}" }};
</script>
<script src="{BACKEND_URL}/widget.js" async></script>
<!-- End Hotel AI Chat Widget -->"""
    return {"snippet": snippet}


# ─── Unanswered questions ─────────────────────────────────────────────────────

@app.get("/hotel/notifications")
async def get_notifications(
    hotel=Depends(get_current_hotel), db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute(
        """SELECT * FROM unanswered_questions WHERE hotel_id = ?
           ORDER BY created_at DESC LIMIT 100""",
        (hotel["id"],),
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@app.post("/hotel/notifications/{question_id}/answer")
async def answer_question(
    question_id: int,
    data: AnswerQuestion,
    hotel=Depends(get_current_hotel),
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute(
        """UPDATE unanswered_questions
           SET answer = ?, answered = 1
           WHERE id = ? AND hotel_id = ?""",
        (data.answer, question_id, hotel["id"]),
    )
    await db.commit()
    return {"message": "Answer saved"}


# ─── Public Chat API (used by widget) ────────────────────────────────────────

@app.post("/chat")
async def chat(data: ChatMessage, db: aiosqlite.Connection = Depends(get_db)):
    # Validate hotel token
    async with db.execute(
        "SELECT * FROM hotels WHERE hotel_token = ?", (data.hotel_token,)
    ) as cur:
        hotel = await cur.fetchone()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    # Ensure session exists
    async with db.execute(
        "SELECT id FROM chat_sessions WHERE session_id = ?", (data.session_id,)
    ) as cur:
        session = await cur.fetchone()

    if not session:
        await db.execute(
            "INSERT INTO chat_sessions (hotel_id, session_id, language) VALUES (?, ?, ?)",
            (hotel["id"], data.session_id, data.language),
        )
        await db.commit()

    # Load conversation history
    async with db.execute(
        """SELECT role, content FROM chat_messages
           WHERE session_id = ? ORDER BY created_at ASC""",
        (data.session_id,),
    ) as cur:
        history = [dict(r) for r in await cur.fetchall()]

    # Load scraped content
    async with db.execute(
        "SELECT title, content FROM scraped_content WHERE hotel_id = ?",
        (hotel["id"],),
    ) as cur:
        pages = await cur.fetchall()

    hotel_content = "\n\n---\n\n".join(
        f"PAGE: {p['title'] or p['url'] if 'url' in p.keys() else p['title']}\n{p['content']}"
        for p in pages
    )

    # Also include manually added Q&A
    async with db.execute(
        """SELECT question, answer FROM unanswered_questions
           WHERE hotel_id = ? AND answered = 1""",
        (hotel["id"],),
    ) as cur:
        answered_qa = await cur.fetchall()

    if answered_qa:
        qa_text = "\n\n--- MANUALLY ADDED Q&A ---\n" + "\n".join(
            f"Q: {qa['question']}\nA: {qa['answer']}" for qa in answered_qa
        )
        hotel_content += qa_text

    # Get AI response
    try:
        response_text, cannot_answer = await get_chat_response(
            hotel_name=hotel["name"],
            hotel_email=hotel["email"],
            hotel_phone=hotel["phone"] or "",
            hotel_content=hotel_content,
            conversation_history=history,
            user_message=data.message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    # Store messages
    await db.execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
        (data.session_id, "user", data.message),
    )
    await db.execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
        (data.session_id, "assistant", response_text),
    )

    # Store unanswered question notification
    if cannot_answer:
        await db.execute(
            """INSERT INTO unanswered_questions (hotel_id, question, language, session_id)
               VALUES (?, ?, ?, ?)""",
            (hotel["id"], data.message, data.language, data.session_id),
        )

    await db.commit()

    return {
        "response": response_text,
        "cannot_answer": cannot_answer,
        "hotel_email": hotel["email"],
        "hotel_phone": hotel["phone"],
    }


# ─── Serve widget.js ──────────────────────────────────────────────────────────

@app.get("/widget.js")
async def serve_widget():
    widget_path = os.path.join(os.path.dirname(__file__), "..", "widget", "widget.js")
    widget_path = os.path.abspath(widget_path)
    if not os.path.exists(widget_path):
        raise HTTPException(status_code=404, detail="Widget not found")
    return FileResponse(widget_path, media_type="application/javascript")


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
