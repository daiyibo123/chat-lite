"""图片上传：压缩保存，返回 URL。"""
from __future__ import annotations

import os
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_SIZE = 1280       # 最长边像素
JPEG_QUALITY = 75     # JPEG 压缩质量
MAX_FILE_MB = 10      # 上传上限 MB


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片上传")

    data = await file.read()
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过 {MAX_FILE_MB}MB")

    # 压缩图片
    img = Image.open(BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 等比缩放
    w, h = img.size
    if max(w, h) > MAX_SIZE:
        ratio = MAX_SIZE / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    # 保存为 JPEG
    name = uuid.uuid4().hex[:12] + ".jpg"
    path = UPLOAD_DIR / name
    img.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    return {"url": f"/api/uploads/{name}"}


@router.get("/uploads/{filename}")
async def get_upload(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, media_type="image/jpeg")
