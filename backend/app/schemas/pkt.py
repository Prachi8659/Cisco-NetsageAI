from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PktFileBase(BaseModel):
    pkt_filename: str
    pkt_file_size: int
    pkt_upload_status: str = "STORED"

class PktFileCreate(PktFileBase):
    pkt_storage_path: str
    sha256_hash: str | None = None

class PktFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    pkt_filename: str
    pkt_storage_path: str
    pkt_file_size: int
    pkt_uploaded_at: datetime
    pkt_upload_status: str
    sha256_hash: str | None = None
