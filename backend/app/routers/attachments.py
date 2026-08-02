import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.models import Attachment, Issue, User
from app.schemas import AttachmentResponse

router = APIRouter(tags=["attachments"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/api/issues/{issue_id}/attachments", response_model=list[AttachmentResponse])
def list_issue_attachments(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return db.query(Attachment).filter(Attachment.issue_id == issue_id).order_by(Attachment.created_at.desc()).all()


@router.post("/api/issues/{issue_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    issue_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    saved_path = UPLOAD_DIR / unique_filename

    contents = await file.read()
    with open(saved_path, "wb") as f:
        f.write(contents)

    attachment = Attachment(
        issue_id=issue_id,
        user_id=current_user.id,
        filename=file.filename or "attachment",
        filepath=f"/uploads/{unique_filename}",
        file_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    log_activity(
        db,
        user_id=current_user.id,
        action="File Uploaded",
        details=f"Uploaded '{attachment.filename}' to Bug #{issue.id}",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    return attachment


@router.get("/api/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    real_path = UPLOAD_DIR / os.path.basename(attachment.filepath)
    if not real_path.exists():
        raise HTTPException(status_code=404, detail="File on disk not found")

    return FileResponse(
        path=real_path,
        filename=attachment.filename,
        media_type=attachment.file_type,
    )


@router.delete("/api/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    real_path = UPLOAD_DIR / os.path.basename(attachment.filepath)
    if real_path.exists():
        try:
            os.remove(real_path)
        except OSError:
            pass

    db.delete(attachment)
    db.commit()
