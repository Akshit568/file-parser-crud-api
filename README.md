# File Parser CRUD API

**FastAPI backend** for uploading, storing, parsing and retrieving files (TXT / CSV / XLS / XLSX / PDF) with asynchronous parsing and progress tracking. This repository implements the hiring task: upload → parse (background) → get progress → fetch parsed JSON → list & delete.
<img width="1917" height="908" alt="p1" src="https://github.com/user-attachments/assets/8c7f2644-db74-442e-b577-229ba51126c0" />

---

## Table of Contents

* [Overview](#overview)
* [Repo layout](#repo-layout)
* [Prerequisites](#prerequisites)
* [Setup (Windows PowerShell)](#setup-windows-powershell)
* [requirements.txt](#requirementstxt)
* [API Documentation](#api-documentation)

  * [Base URL](#base-url)
  * [1) Upload file — `POST /files`](#1-upload-file---post-files)
  * [2) Check progress — `GET /files/{file_id}/progress`](#2-check-progress---get-filesfile_idprogress)
  * [3) Get parsed content — `GET /files/{file_id}`](#3-get-parsed-content---get-filesfile_id)
  * [4) List files — `GET /files`](#4-list-files---get-files)
  * [5) Delete file — `DELETE /files/{file_id}`](#5-delete-file---delete-filesfile_id)
* [Sample requests & responses](#sample-requests--responses)
* [Postman collection (recommended)](#postman-collection-recommended)
* [Screenshots (what to capture & where to add them)](#screenshots-what-to-capture--where-to-add-them)
* [Troubleshooting (common issues)](#troubleshooting-common-issues)
* [Next steps / Bonus ideas](#next-steps--bonus-ideas)
* [License](#license)

---

## Overview

This project provides a simple, production-lean FastAPI service to:

* Accept file uploads (multipart/form-data)
* Store the uploaded file on disk and metadata in SQLite
* Parse file contents asynchronously (background task)
* Persist parsed structured content (JSON) in database
* Expose endpoints for progress, content retrieval, listing, and deletion

Supported file types: `.txt`, `.csv`, `.xls`, `.xlsx`, `.pdf`.

---

## Repo layout

Place these files in your repo root (recommended):

```
file-parser-crud-api/
├─ main.py                  # FastAPI app (endpoints + background parser)
├─ requirements.txt         # Python dependencies
├─ README.md                # this file
├─ uploads/                 # uploaded files (create automatically at runtime)
├─ files.db                 # SQLite DB created at runtime
├─ postman_collection.json  # optional Postman collection
└─ screenshots/             # submission screenshots
```

> **Note:** Add `uploads/` and `files.db` to `.gitignore` so you don't commit uploaded files or DB to GitHub.

---

## Prerequisites

* Windows 11 (or any OS with Python)
* Python 3.13.7 (you indicated you're using this)
* Git (optional)
* Postman or curl for testing

---

## Setup (Windows PowerShell)

Open PowerShell in your project folder (the folder that will contain `main.py`):

```powershell
# 1. Create & activate virtual environment
python -m venv venv

# If activation is blocked by execution policy (common), run:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
uvicorn main:app --reload
```

* API: `http://127.0.0.1:8000`
* Swagger UI: `http://127.0.0.1:8000/docs`

---

## requirements.txt

Make sure `requirements.txt` includes at least:

```
fastapi
uvicorn[standard]
sqlalchemy
aiofiles
python-multipart
pandas
openpyxl
xlrd
PyPDF2
```

`xlrd` is required for some `.xls` files and `openpyxl` for `.xlsx`.

---

## API Documentation

**Base URL:** `http://127.0.0.1:8000`

All examples below use JSON responses unless noted otherwise.

### 1) Upload file — `POST /files`

**Description:** Upload a file (multipart/form-data) and start background parsing.

* **Body (form-data):** `file` (type: File) — field name **must be exactly `file`** (lowercase).

**curl example**
<img width="1918" height="905" alt="p3" src="https://github.com/user-attachments/assets/e89a1fb4-c6d3-4c28-85ff-c8ad51aab927" />


```bash
curl -X POST "http://127.0.0.1:8000/files" -F "file=@C:/path/to/sample.xlsx"
```

**Success (201)**

```json
{ "file_id": "<uuid>", "status": "processing" }
```

**Errors**

* `422 Unprocessable Entity` — missing `file` form field or wrong body type.
* `500` — server error saving file.

---

### 2) Check progress — `GET /files/{file_id}/progress`


Returns current progress and status for upload/parsing.

**curl example**
<img width="1918" height="905" alt="p3" src="https://github.com/user-attachments/assets/a553285e-3fdf-4fd7-865f-1d9658ae4156" />

```bash
curl "http://127.0.0.1:8000/files/<file_id>/progress"
```

**Responses**

* Processing:

```json
{ "file_id": "<uuid>", "status": "processing", "progress": 42 }
```

* Ready:

```json
{ "file_id": "<uuid>", "status": "ready", "progress": 100 }
```

* `404` — file not found

---

### 3) Get parsed content — `GET /files/{file_id}`

If parsing completed, returns parsed JSON. If still processing, returns `202` with a message.

**curl example**

<img width="1918" height="907" alt="get_curl" src="https://github.com/user-attachments/assets/4a353aeb-27e3-4cfc-b6cd-c3e6f4eb3550" />

```bash
curl "http://127.0.0.1:8000/files/<file_id>"
```

**Excel / CSV success**

```json
{
  "file_id": "<uuid>",
  "filename": "sample.xls",
  "parsed": [ {"Col1":"val1","Col2":1}, ... ]
}
```

**TXT success**

```json
{ "file_id":"<uuid>", "filename":"AUTHORS.txt", "parsed": {"text":"full file content"} }
```

**Still processing (202)**

```json
{ "message": "File upload or processing in progress. Please try again later." }
```

---

### 4) List files — `GET /files`

Returns array of file metadata (id, filename, status, progress, created\_at).


**curl example**

<img width="1917" height="967" alt="curf" src="https://github.com/user-attachments/assets/44aa8c6a-6f76-45b0-aabb-32bea940502e" />

```bash
curl "http://127.0.0.1:8000/files"
```

**Response**

```json
[
  {"id":"...","filename":"sample.xls","status":"ready","progress":100,"created_at":"..."},
  ...
]
```

---

### 5) Delete file — `DELETE /files/{file_id}`

Deletes DB entry and removes file from disk.

**curl example**

<img width="1917" height="912" alt="curf_del" src="https://github.com/user-attachments/assets/58f66a79-299a-41dd-87b3-8a3ddfe8518e" />

```bash
curl -X DELETE "http://127.0.0.1:8000/files/<file_id>"
```

**Success**

```json
{ "deleted": true }
```

---

## Sample requests & responses (quick copy-paste)

**1) Upload**

```bash
curl -X POST "http://127.0.0.1:8000/files" -F "file=@C:/Users/hp/Desktop/Meritshot.xls"
```

**Response**

```json
{ "file_id": "eb028abb-7c3f-455a-a4c9-918822e910d9", "status": "processing" }
```

**2) Poll progress**

```bash
curl "http://127.0.0.1:8000/files/eb028abb-7c3f-455a-a4c9-918822e910d9/progress"
```

**Response**

```json
{ "file_id": "...", "status": "ready", "progress": 100 }
```

**3) Fetch parsed content**

```bash
curl "http://127.0.0.1:8000/files/eb028abb-7c3f-455a-a4c9-918822e910d9"
```

**Response**

```json
{
  "file_id": "eb028abb-7c3f-455a-a4c9-918822e910d9",
  "filename": "sample.xls",
  "parsed": [
    {"Unnamed: 0":1,"Unnamed: 1":"hi","Unnamed: 2":67},
    {"Unnamed: 0":2,"Unnamed: 1":"h2","Unnamed: 2":78}
  ]
}
```

**4) List files**

```bash
curl "http://127.0.0.1:8000/files"
```

**5) Delete file**

```bash
curl -X DELETE "http://127.0.0.1:8000/files/eb028abb-7c3f-455a-a4c9-918822e910d9"
```

**Response**

```json
{ "deleted": true }
```

---

## Postman collection (recommended)

Create a Postman collection with these requests and export it as `postman_collection.json`:

* POST `/files` (form-data `file`)
* GET `/files/{{file_id}}/progress`
* GET `/files/{{file_id}}`
* GET `/files`
* DELETE `/files/{{file_id}}`

Include that file in your repo for the reviewer.

---

## Screenshots (what to capture & where to add them)

Create a `screenshots/` folder and add the following images (sample file names suggested):

1. `01_upload.png` — show POST /files body (form-data) and response (file\_id).
2. `02_progress.png` — show GET /files/{file\_id}/progress (processing → ready).
3. `03_parsed_content.png` — show GET /files/{file\_id} response (parsed JSON).
4. `04_list.png` — show GET /files response listing all files.
5. `05_delete.png` — show DELETE /files/{file\_id} response and subsequent GET /files showing it removed.

Add a short caption list in README pointing to each image (example already included above in repo layout section).

---

## Troubleshooting (common issues)

* `422 Unprocessable Entity` — make sure body uses **form-data** and key name is exactly `file` (File type).
* `File not found` — ensure you are using the exact `file_id` returned by upload and that the DB record exists (`GET /files`).
* Excel parse errors — install engines:

  ```bash
  pip install openpyxl xlrd
  ```
* If Postman fails but curl works — double-check Postman body setup (form-data + file key).

---





