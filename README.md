# NetSage AI — AI-Assisted Cisco Packet Tracer Troubleshooting Platform

NetSage AI is an AI-assisted Cisco networking troubleshooting platform designed for Cisco Packet Tracer networking labs. It combines real `.pkt` topology files, actual Cisco show-command evidence parsing, deterministic Python rule verification, AI-assisted diagnosis, and a mandatory **Human-in-the-Loop** verification architecture.

---

## 🛡️ Critical Safety Notice
> **NetSage AI provides recommendations only.**
> Network configuration changes must be performed manually inside Cisco Packet Tracer. The application **NEVER** executes commands on routers/switches, modifies live topologies, or auto-applies fixes.

---

## 🚀 Quick Start

### 1. Backend Setup (FastAPI)
```powershell
# Navigate to project directory
cd "c:\Users\ASUS\OneDrive\Desktop\Cisco Project"

# Install Python dependencies
pip install -r backend/requirements.txt

# Run backend API server
uvicorn backend.app.main:app --reload --port 8000
```
- API Documentation: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Frontend Setup (React + TypeScript + Vite)
```powershell
# Navigate to frontend directory
cd frontend

# Run development server
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

### 3. Run Backend Automated Tests
```powershell
python -m pytest backend/tests -v
```

---

## 📁 Phase 1 Implemented Features
- **Clean Architecture Foundation**: FastAPI backend, React TypeScript frontend, SQLAlchemy database models.
- **Troubleshooting Case Management**: Create and view cases with category, severity, symptom description, and topology notes.
- **Secure `.pkt` File Upload Workflow**:
  - Strict `.pkt` file extension validation.
  - File size validation (max 50 MB limit).
  - Empty file and malicious extension rejection.
  - Collision-resistant and safe server storage in `data/pkt_uploads`.
  - Full database association: `pkt_filename`, `pkt_storage_path`, `pkt_file_size`, `pkt_uploaded_at`, `pkt_upload_status`, `sha256_hash`.
  - Secure `.pkt` download and replace endpoints.
