from pathlib import Path
from fastapi import HTTPException, status
from app.core.config import settings

class PktValidationError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

def validate_pkt_file(filename: str, file_size: int, content: bytes | None = None) -> None:
    """
    Perform strict validation on the uploaded Packet Tracer file.
    - Validate extension is strictly .pkt
    - Validate file size is > 0 and within configured limit (50MB)
    - Ensure file is not empty or corrupt
    """
    if not filename:
        raise PktValidationError("File upload failed: No filename provided.")

    # Check extension
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.ALLOWED_PKT_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_PKT_EXTENSIONS)
        raise PktValidationError(
            f"Invalid file type '{suffix}'. Only Cisco Packet Tracer ({allowed}) files are supported."
        )

    # Double check for double extensions like file.pkt.exe
    parts = Path(filename).name.split(".")
    if len(parts) > 2:
        final_ext = f".{parts[-1].lower()}"
        if final_ext not in settings.ALLOWED_PKT_EXTENSIONS:
            raise PktValidationError(
                f"Suspicious filename '{filename}'. Must end strictly with .pkt"
            )

    # Check size
    if file_size == 0:
        raise PktValidationError("Uploaded .pkt file is empty (0 bytes). Please upload a valid Cisco Packet Tracer file.")

    if file_size > settings.MAX_PKT_FILE_SIZE_BYTES:
        max_mb = settings.MAX_PKT_FILE_SIZE_BYTES // (1024 * 1024)
        raise PktValidationError(
            f"File size exceeds the maximum allowed limit of {max_mb} MB."
        )

    # Content sanity check if provided
    if content is not None and len(content) == 0:
        raise PktValidationError("Uploaded .pkt file content is empty.")
