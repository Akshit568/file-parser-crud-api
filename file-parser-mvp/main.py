import os
import uuid
import time
from typing import Optional, List

import pandas as pd
from PyPDF2 import PdfReader
import aiofiles

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, func
from sqlalchemy.orm import sessionmaker, declarative_base

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

DATABASE_URL = "sqlite:///./files.db"  

# --- DB  ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class FileModel(Base):
    __tablename__ = "files"
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    status = Column(String, default="uploading")  # uploading | processing | ready | failed
    progress = Column(Integer, default=0)
    parsed_content = Column(JSON, nullable=True)  # store parsed JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(bind=engine)

# --- App ---
app = FastAPI(title="File Parser CRUD - MVP")

# Helper: DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints ---

@app.post("/files", status_code=201)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload file and start background parsing."""
    db = next(get_db())

    # create DB record
    file_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    record = FileModel(id=file_id, filename=file.filename, filepath=dest_path, status="uploading", progress=0)
    db.add(record)
    db.commit()

  
    CHUNK = 1024 * 1024
    async with aiofiles.open(dest_path, "wb") as out_file:
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            await out_file.write(chunk)
          


    record.status = "processing"
    record.progress = 1
    db.add(record); db.commit()

    background_tasks.add_task(parse_file_task, file_id, dest_path)
    return {"file_id": file_id, "status": record.status}


@app.get("/files/{file_id}/progress")
def get_progress(file_id: str):
    db = next(get_db())
    rec = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_id": file_id, "status": rec.status, "progress": rec.progress}


@app.get("/files/{file_id}")
def get_file_content(file_id: str):
    db = next(get_db())
    rec = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    if rec.status != "ready":
        return JSONResponse(status_code=202, content={"message": "File upload or processing in progress. Please try again later."})
    return {"file_id": file_id, "filename": rec.filename, "parsed": rec.parsed_content}


@app.get("/files")
def list_files():
    db = next(get_db())
    rows = db.query(FileModel).all()
    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "filename": r.filename,
            "status": r.status,
            "progress": r.progress,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return result


@app.delete("/files/{file_id}")
def delete_file(file_id: str):
    db = next(get_db())
    rec = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    # delete file from disk
    try:
        os.remove(rec.filepath)
    except Exception:
        pass
    db.delete(rec)
    db.commit()
    return {"deleted": True}

# --- Background parsing task---
def parse_file_task(file_id: str, filepath: str):
    db = SessionLocal()
    rec = db.query(FileModel).filter(FileModel.id == file_id).first()
    try:
        # quick progress update
        rec.progress = 5; db.add(rec); db.commit()

        parsed = None
        lower = filepath.lower()
        if lower.endswith(".csv"):
            # read in chunks to simulate long parsing and update progress
            rows = []
            for i, chunk in enumerate(pd.read_csv(filepath, chunksize=1000)):
                rows.extend(chunk.to_dict(orient="records"))
                # update progress (simulate)
                rec.progress = min(5 + (i+1)*5, 90)
                db.add(rec); db.commit()
                time.sleep(0.1)  
            parsed = rows

        elif lower.endswith((".xls", ".xlsx")):
            df = pd.read_excel(filepath)
            parsed = df.to_dict(orient="records")
            rec.progress = 80; db.add(rec); db.commit()

        elif lower.endswith(".pdf"):
            reader = PdfReader(filepath)
            text_pages = []
            for i, p in enumerate(reader.pages):
                text_pages.append(p.extract_text())
                rec.progress = min(5 + (i+1)*10, 90)
                db.add(rec); db.commit()
                time.sleep(0.05)
            parsed = {"pages": text_pages}

        else:
            parsed = {"note": "unsupported file type"}
            rec.progress = 50; db.add(rec); db.commit()

        # finalize
        rec.parsed_content = parsed
        rec.status = "ready"
        rec.progress = 100
        db.add(rec); db.commit()
    except Exception as e:
        rec.status = "failed"
        rec.progress = 0
        db.add(rec); db.commit()
        print("Parsing failed:", e)
    finally:
        db.close()

