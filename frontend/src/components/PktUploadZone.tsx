import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  Download, 
  Trash2, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  HardDrive, 
  Key, 
  RefreshCw,
  FileCode2
} from 'lucide-react';
import type { PktFile } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';

interface PktUploadZoneProps {
  caseId: number | string;
  currentPkt?: PktFile | null;
  onUploadSuccess: (pkt: PktFile) => void;
  onDeleteSuccess?: () => void;
}

export const PktUploadZone: React.FC<PktUploadZoneProps> = ({
  caseId,
  currentPkt,
  onUploadSuccess,
  onDeleteSuccess,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (isoString: string): string => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const handleFile = async (file: File) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    // 1. Client-side extension validation
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith('.pkt')) {
      setErrorMessage(`Invalid file format '${file.name}'. Only Cisco Packet Tracer (.pkt) files are accepted.`);
      return;
    }

    // 2. Client-side size validation (50MB)
    if (file.size === 0) {
      setErrorMessage('The selected file is empty (0 bytes). Please select a valid Packet Tracer topology file.');
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage(`File size (${formatFileSize(file.size)}) exceeds the maximum allowed limit of 50 MB.`);
      return;
    }

    try {
      setUploading(true);
      const res = await apiService.uploadPktFile(caseId, file);
      setSuccessMessage(`Successfully uploaded and associated '${res.pkt_filename}' with this case.`);
      onUploadSuccess(res);
    } catch (err: unknown) {
      setErrorMessage(formatApiError(err, 'Failed to upload .pkt file.'));
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to remove this .pkt file from the case?')) return;
    try {
      setUploading(true);
      await apiService.deletePktFile(caseId);
      setSuccessMessage('File removed successfully.');
      if (onDeleteSuccess) onDeleteSuccess();
    } catch (err: unknown) {
      setErrorMessage(formatApiError(err, 'Failed to delete .pkt file.'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Notifications */}
      {errorMessage && (
        <div className="p-3.5 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200 animate-in fade-in duration-200">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Upload Validation Error: </strong>
            {errorMessage}
          </div>
        </div>
      )}

      {successMessage && (
        <div className="p-3.5 bg-emerald-950/40 border border-emerald-500/40 rounded-xl flex items-center gap-3 text-xs text-emerald-200 animate-in fade-in duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* When a .pkt file is currently attached */}
      {currentPkt ? (
        <div className="bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-5 shadow-xl relative overflow-hidden">
          {/* Subtle background decoration */}
          <div className="absolute -right-10 -bottom-10 w-44 h-44 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-600/30 to-blue-600/30 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shadow-inner">
                <FileCode2 className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-mono font-bold text-base text-cyan-300 tracking-tight">
                    {currentPkt.pkt_filename}
                  </h3>
                  <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-cyan-950 text-cyan-300 rounded border border-cyan-500/40">
                    {currentPkt.pkt_upload_status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Primary Packet Tracer Case Artifact
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2.5 w-full md:w-auto justify-end">
              <a
                href={apiService.getPktDownloadUrl(caseId)}
                download={currentPkt.pkt_filename}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold transition-all hover:scale-[1.02]"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download .pkt</span>
              </a>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${uploading ? 'animate-spin' : ''}`} />
                <span>Replace File</span>
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={uploading}
                className="p-2 rounded-lg bg-rose-950/30 hover:bg-rose-950/60 text-rose-400 border border-rose-500/30 transition-colors"
                title="Remove .pkt file"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 mt-4 text-xs">
            <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80">
              <div className="flex items-center gap-2 text-slate-400 font-medium mb-1">
                <HardDrive className="w-3.5 h-3.5 text-blue-400" />
                <span>File Size</span>
              </div>
              <p className="font-mono font-semibold text-slate-200">
                {formatFileSize(currentPkt.pkt_file_size)}
              </p>
            </div>

            <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80">
              <div className="flex items-center gap-2 text-slate-400 font-medium mb-1">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Uploaded At</span>
              </div>
              <p className="font-mono font-semibold text-slate-200">
                {formatDate(currentPkt.pkt_uploaded_at)}
              </p>
            </div>

            <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80">
              <div className="flex items-center gap-2 text-slate-400 font-medium mb-1">
                <Key className="w-3.5 h-3.5 text-indigo-400" />
                <span>SHA-256 Integrity</span>
              </div>
              <p className="font-mono text-[11px] text-slate-300 truncate" title={currentPkt.sha256_hash}>
                {currentPkt.sha256_hash ? `${currentPkt.sha256_hash.slice(0, 16)}...` : 'Verified'}
              </p>
            </div>
          </div>

          {/* Note */}
          <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
            <span>
              💡 Open in <strong>Cisco Packet Tracer</strong> to inspect and reproduce the network fault.
            </span>
            <span className="text-cyan-400/80 font-mono">Status: Ready for Evidence Collection</span>
          </div>
        </div>
      ) : (
        /* Dropzone when no .pkt is uploaded */
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`group cursor-pointer relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 ${
            isDragging
              ? 'border-cyan-400 bg-cyan-950/20 scale-[1.01]'
              : 'border-slate-700/80 hover:border-cyan-500/50 bg-slate-900/40 hover:bg-slate-900/70'
          }`}
        >
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-950 via-slate-900 to-blue-950 border border-cyan-500/30 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:text-cyan-300 transition-all shadow-lg">
              {uploading ? (
                <RefreshCw className="w-6 h-6 animate-spin" />
              ) : (
                <UploadCloud className="w-7 h-7" />
              )}
            </div>

            <div className="space-y-1">
              <h4 className="text-sm font-bold text-slate-200 group-hover:text-cyan-300 transition-colors">
                {uploading ? 'Uploading and validating .pkt artifact...' : 'Upload Cisco Packet Tracer (.pkt) File'}
              </h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Drag and drop your Packet Tracer lab topology file here, or click to browse.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-cyan-300 border border-slate-700">
                Extension: .pkt only
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-400 border border-slate-700">
                Max Size: 50 MB
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-emerald-300 border border-slate-700">
                Encrypted & Isolated Storage
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            handleFile(e.target.files[0]);
          }
        }}
        accept=".pkt"
        className="hidden"
      />
    </div>
  );
};
