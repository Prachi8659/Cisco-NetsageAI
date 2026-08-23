import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Save, 
  FileCode2, 
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';
import type { SeverityLevel } from '../types';
import { apiService } from '../services/api';
import { SafetyNotice } from '../components/SafetyNotice';

const CATEGORIES = [
  'VLAN',
  'Routing',
  'Gateway',
  'DHCP',
  'DNS',
  'ACL',
  'NAT',
  'Interface',
  'Wireless',
  'General',
];

const SEVERITIES: SeverityLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export const CreateCasePage: React.FC = () => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState('');
  const [caseNumber, setCaseNumber] = useState('');
  const [category, setCategory] = useState('VLAN');
  const [severity, setSeverity] = useState<SeverityLevel>('MEDIUM');
  const [symptom, setSymptom] = useState('');
  const [topologyNotes, setTopologyNotes] = useState('');
  const [selectedPktFile, setSelectedPktFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith('.pkt')) {
        setError(`Invalid file type '${file.name}'. Only .pkt files are allowed.`);
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setError('File exceeds the 50MB size limit.');
        return;
      }
      setError(null);
      setSelectedPktFile(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !symptom.trim()) {
      setError('Please fill in both the Case Title and the Observed Symptom.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      // 1. Create the case
      const createdCase = await apiService.createCase({
        title: title.trim(),
        case_number: caseNumber.trim() ? caseNumber.trim() : undefined,
        category,
        severity,
        symptom: symptom.trim(),
        topology_notes: topologyNotes.trim() ? topologyNotes.trim() : undefined,
      });

      // 2. If a .pkt file was selected, upload it immediately
      if (selectedPktFile) {
        await apiService.uploadPktFile(createdCase.id, selectedPktFile);
      }

      // 3. Navigate to the case detail page
      navigate(`/cases/${createdCase.id}`);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to create troubleshooting case.';
      setError(detail);
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back button & Title */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-xl font-extrabold text-white">Create Troubleshooting Case</h1>
          <p className="text-xs text-slate-400">
            Document a Packet Tracer lab failure, attach topology artifact, and initiate diagnostic workflow.
          </p>
        </div>
      </div>

      <SafetyNotice compact />

      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Submission Error: </strong>
            {error}
          </div>
        </div>
      )}

      {/* Main Form */}
      <form onSubmit={handleSubmit} className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        {/* Row 1: Title & Custom Case ID */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              Case Title <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. VLAN 10 Workstations Isolated from Default Gateway"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              Case ID <span className="text-slate-400 font-normal">(Optional)</span>
            </label>
            <input
              type="text"
              value={caseNumber}
              onChange={(e) => setCaseNumber(e.target.value)}
              placeholder="e.g. CASE-001 (Auto if blank)"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
            />
          </div>
        </div>

        {/* Row 2: Category & Severity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              Problem Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              Severity Level
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as SeverityLevel)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 3: Observed Symptom */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-200 block">
            Observed Symptom / Fault Description <span className="text-rose-400">*</span>
          </label>
          <textarea
            required
            rows={3}
            value={symptom}
            onChange={(e) => setSymptom(e.target.value)}
            placeholder="Describe what is failing. (e.g. PC1 cannot ping default gateway 192.168.10.1. Link lights are green on S1 Fa0/2, but pings timeout with 100% loss.)"
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
          />
        </div>

        {/* Row 4: Topology Notes */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-200 block">
            Topology Notes / Device Designations <span className="text-slate-400 font-normal">(Optional)</span>
          </label>
          <textarea
            rows={2}
            value={topologyNotes}
            onChange={(e) => setTopologyNotes(e.target.value)}
            placeholder="e.g. PC1 (192.168.10.10/24) -> Switch S1 (Fa0/2) -> Router R1 (Gi0/1.10). Expected VLAN: 10."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
          />
        </div>

        {/* Row 5: Initial .pkt File Upload */}
        <div className="p-4 bg-slate-950/60 border border-slate-800/90 rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <FileCode2 className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wide">
              Attach Cisco Packet Tracer (.pkt) Topology
            </h4>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <input
              type="file"
              accept=".pkt"
              id="initialPktUpload"
              onChange={handleFileChange}
              className="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-cyan-950 file:text-cyan-300 hover:file:bg-cyan-900 cursor-pointer"
            />
            {selectedPktFile && (
              <span className="text-xs text-emerald-400 font-mono flex items-center gap-1 shrink-0">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {selectedPktFile.name} ({(selectedPktFile.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400">
            You can also upload or replace the .pkt file at any time from the case detail workspace.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
          <Link
            to="/"
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-blue-600/20 transition-all hover:scale-[1.02] disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{submitting ? 'Creating Case...' : 'Create Case & Continue'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
