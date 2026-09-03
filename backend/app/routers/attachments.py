import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import Attachment, Issue, User, UserRole
from app.schemas import AttachmentResponse

router = APIRouter(tags=["attachments"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@router.get(
    "/api/issues/{issue_id}/attachments",
    response_model=list[AttachmentResponse],
    summary="List attachments for an issue",
    description="Retrieve all file attachments and screenshots associated with a specific defect.",
    responses={
        200: {"description": "List of attachments", "model": list[AttachmentResponse]},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def list_issue_attachments(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List attachments for an issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")
    return db.query(Attachment).filter(Attachment.issue_id == issue_id).order_by(Attachment.created_at.desc()).all()


@router.post(
    "/api/issues/{issue_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload attachment for an issue",
    description="Upload a screenshot, error log, or document (up to 25MB) to attach to a defect ticket.",
    responses={
        201: {"description": "File uploaded successfully", "model": AttachmentResponse},
        400: {"description": "File empty or exceeds size limit", "model": ErrorResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
async def upload_attachment(
    issue_id: int,
    file: UploadFile = File(..., description="Multipart file upload (up to 25MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file attachment for an issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File exceeds maximum allowed size of 25MB (got {file_size / (1024*1024):.1f}MB)")

    raw_filename = file.filename or "attachment"
    clean_filename = os.path.basename(raw_filename)
    ext = os.path.splitext(clean_filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    saved_path = UPLOAD_DIR / unique_filename

    with open(saved_path, "wb") as f:
        f.write(contents)

    attachment = Attachment(
        issue_id=issue_id,
        user_id=current_user.id,
        filename=clean_filename,
        filepath=f"/uploads/{unique_filename}",
        file_type=file.content_type or "application/octet-stream",
        file_size=file_size,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    log_activity(
        db,
        user_id=current_user.id,
        action="File Uploaded",
        details=f"Uploaded '{attachment.filename}' ({file_size // 1024} KB) to Bug #{issue.id}",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    return attachment


@router.get(
    "/api/attachments/{attachment_id}/download",
    summary="Download attachment file",
    description="Stream and download an attachment file by its ID.",
    responses={
        200: {"description": "File stream"},
        404: {"description": "Attachment or file on disk not found", "model": ErrorResponse},
    },
)
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download an attachment file safely."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Attachment #{attachment_id} not found")

    file_basename = os.path.basename(attachment.filepath)
    real_path = (UPLOAD_DIR / file_basename).resolve()

    # Prevent directory traversal attacks
    if not str(real_path).startswith(str(UPLOAD_DIR.resolve())) or not real_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File on disk not found or inaccessible")

    return FileResponse(
        path=real_path,
        filename=attachment.filename,
        media_type=attachment.file_type,
    )


@router.delete(
    "/api/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete attachment",
    description="Delete an attachment from database and disk. Permitted for uploader, project lead, or Admin.",
    responses={
        204: {"description": "Attachment deleted successfully"},
        403: {"description": "Not authorized to delete this attachment", "model": ErrorResponse},
        404: {"description": "Attachment not found", "model": ErrorResponse},
    },
)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an attachment."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Attachment #{attachment_id} not found")

    is_uploader = attachment.user_id == current_user.id
    is_admin = current_user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    is_project_owner = attachment.issue.project.owner_id == current_user.id if attachment.issue and attachment.issue.project else False

    if not (is_uploader or is_admin or is_project_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this attachment")

    file_basename = os.path.basename(attachment.filepath)
    real_path = (UPLOAD_DIR / file_basename).resolve()
    if real_path.exists() and str(real_path).startswith(str(UPLOAD_DIR.resolve())):
        try:
            os.remove(real_path)
        except OSError:
            pass

    db.delete(attachment)
    db.commit()
