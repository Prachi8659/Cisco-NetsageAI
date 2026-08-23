from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from backend.app.core.config import settings
from backend.app.core.security import sanitize_filename, generate_safe_storage_filename, calculate_sha256
from backend.app.services.pkt.validator import validate_pkt_file

class PktStorageService:
    def __init__(self, storage_dir: Path = settings.PKT_STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_pkt_file(self, case_id: int | str, upload_file: UploadFile) -> dict:
        """
        Safely validate and store an uploaded .pkt file.
        Returns metadata dict containing:
        - original_filename
        - safe_filename
        - absolute_storage_path
        - file_size
        - sha256_hash
        """
        raw_filename = upload_file.filename or "network.pkt"
        clean_original_filename = sanitize_filename(raw_filename)

        # Read content asynchronously in chunks or memory
        content = await upload_file.read()
        file_size = len(content)

        # Validate file
        validate_pkt_file(
            filename=clean_original_filename,
            file_size=file_size,
            content=content
        )

        # Generate isolated, safe storage filename
        safe_name = generate_safe_storage_filename(clean_original_filename, case_id)
        target_path = self.storage_dir / safe_name

        # Ensure no path traversal outside storage directory
        resolved_path = target_path.resolve()
        if not str(resolved_path).startswith(str(self.storage_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid storage path attempt."
            )

        # Write to disk
        with open(target_path, "wb") as f:
            f.write(content)

        # Calculate hash for audit trail and integrity
        sha256 = calculate_sha256(content)

        return {
            "original_filename": clean_original_filename,
            "safe_filename": safe_name,
            "storage_path": str(target_path),
            "file_size": file_size,
            "sha256_hash": sha256,
        }

    def get_file_path(self, storage_path_str: str) -> Path:
        """
        Verify and return a safe Path object for an existing stored file.
        """
        file_path = Path(storage_path_str).resolve()
        # Path traversal guard
        if not str(file_path).startswith(str(self.storage_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to requested file."
            )

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested .pkt file was not found on server storage."
            )

        return file_path

pkt_storage_service = PktStorageService()
