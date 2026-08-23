import re
import uuid
import hashlib
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """
    Sanitize the input filename by stripping path separators and non-standard characters.
    Preserves valid characters and extension.
    """
    base_name = Path(filename).name
    # Replace unsafe characters with underscore, keeping alphanumeric, dots, hyphens, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_\.-]', '_', base_name)
    return sanitized or "unnamed_file.pkt"

def generate_safe_storage_filename(original_filename: str, case_id: int | str) -> str:
    """
    Generate a collision-resistant, safe filename on the server using case ID and UUID.
    Format: case_{case_id}_{uuid}.pkt
    """
    safe_id = str(case_id).replace("/", "_").replace("\\", "_")
    unique_suffix = uuid.uuid4().hex[:12]
    return f"case_{safe_id}_{unique_suffix}.pkt"

def calculate_sha256(content: bytes) -> str:
    """Calculate SHA256 hex digest for content integrity verification."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()
