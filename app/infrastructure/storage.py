"""File storage utilities"""
import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.infrastructure.config.settings import settings


def ensure_upload_dir() -> Path:
    """Ensure upload directory exists"""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower()


def is_allowed_image_file(filename: str) -> bool:
    """Check if file is an allowed image type"""
    ext = get_file_extension(filename)
    return ext in settings.ALLOWED_IMAGE_EXTENSIONS


async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file and return relative path"""
    if not file.filename:
        raise ValueError("Filename is required")
    
    if not is_allowed_image_file(file.filename):
        raise ValueError(f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}")
    
    # Check file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise ValueError(f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB")
    
    # Generate unique filename
    ext = get_file_extension(file.filename)
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Ensure upload directory exists
    upload_dir = ensure_upload_dir()
    file_path = upload_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Return relative path for URL
    return f"/uploads/{unique_filename}"


def delete_file(file_path: str) -> bool:
    """Delete file from storage"""
    try:
        # Remove /uploads/ prefix if present
        if file_path.startswith("/uploads/"):
            file_path = file_path.replace("/uploads/", "")
        
        upload_dir = ensure_upload_dir()
        full_path = upload_dir / file_path
        
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    except Exception:
        return False



