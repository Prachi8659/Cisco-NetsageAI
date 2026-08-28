import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  FileCode2, 
  Terminal, 
  Cpu, 
  Sparkles, 
  CheckSquare, 
  ShieldCheck, 
  Activity, 
  AlertOctagon, 
  Layers, 
  RefreshCw
} from 'lucide-react';
import type { Case, PktFile } from '../types';
import { apiService } from '../services/api';
import { PktUploadZone } from '../components/PktUploadZone';
import { PktAnalysisViewer } from '../components/PktAnalysisViewer';
import { CiscoEvidenceManager } from '../components/CiscoEvidenceManager';
import { PythonRuleAnalysis } from '../components/PythonRuleAnalysis';
import { AiDiagnosisPanel } from '../components/AiDiagnosisPanel';
import { DiagnosisComparisonPanel } from '../components/DiagnosisComparisonPanel';
import { HumanReviewPanel } from '../components/HumanReviewPanel';
import { SafetyNotice } from '../components/SafetyNotice';
import { formatApiError } from '../utils/error';

export const CaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCase = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getCaseById(id);
      setCaseData(data);
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to load case details.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCase();
  }, [id]);

  const handlePktUploaded = (pkt: PktFile) => {
    if (caseData) {
      setCaseData({ ...caseData, pkt_file: pkt });
    }
  };

  const handlePktDeleted = () => {
    if (caseData) {
      setCaseData({ ...caseData, pkt_file: null });
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
        <p className="text-xs text-slate-400">Loading troubleshooting workspace...</p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="max-w-3xl mx-auto py-12">
        <div className="p-6 bg-rose-950/40 border border-rose-500/40 rounded-2xl text-center space-y-3">
          <AlertOctagon className="w-8 h-8 text-rose-400 mx-auto" />
          <h2 className="text-base font-bold text-rose-200">Case Not Found or Inaccessible</h2>
          <p className="text-xs text-rose-300">{error || 'The requested case could not be retrieved.'}</p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Cases Directory</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex items-center gap-2.5">
            <span className="font-mono font-bold text-sm text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-lg border border-cyan-800/60">
              {caseData.case_number}
            </span>
            <h1 className="text-lg font-black text-white tracking-tight">{caseData.title}</h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 text-xs font-bold uppercase rounded-lg border bg-slate-800 text-slate-300 border-slate-700">
            {caseData.status}
          </span>
          <span className="px-2.5 py-1 text-xs font-bold rounded-lg border bg-blue-950 text-blue-300 border-blue-800">
            {caseData.category}
          </span>
          <span className="px-2.5 py-1 text-xs font-bold rounded-lg border bg-amber-950 text-amber-300 border-amber-800">
            {caseData.severity}
          </span>
        </div>
      </div>

      {/* Safety Notice */}
      <SafetyNotice />

      {/* Grid: Left Column (Case Details & PKT File Artifact) + Right Column (Pipeline Stage Roadmap) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Main Artifact & Case Context */}
        <div className="lg:col-span-2 space-y-6">
          {/* 1. Primary Packet Tracer .pkt Artifact Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileCode2 className="w-5 h-5 text-cyan-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Cisco Packet Tracer (.pkt) Case Artifact
                </h2>
              </div>
              <span className="text-[11px] text-slate-400">
                Primary Case Topology
              </span>
            </div>

            {/* Pkt Upload & Management Component */}
            <PktUploadZone
              caseId={caseData.id}
              currentPkt={caseData.pkt_file}
              onUploadSuccess={handlePktUploaded}
              onDeleteSuccess={handlePktDeleted}
            />
          </div>

          {/* 2. Packet Tracer .pkt Topology & Facts Analysis Viewer */}
          <PktAnalysisViewer
            caseId={caseData.id}
            hasPktFile={!!caseData.pkt_file}
          />

          {/* 3. Cisco Show-Command Evidence Collection & Parser */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
            <CiscoEvidenceManager
              caseId={caseData.id}
            />
          </div>

          {/* 4. Python Rule-Based Fault Detection */}
          <PythonRuleAnalysis
            caseId={caseData.id}
          />

          {/* 5. AI-Assisted Network Diagnosis */}
          <AiDiagnosisPanel
            caseId={caseData.id}
          />

          {/* 6. AI vs Python Diagnosis Comparison Engine */}
          <DiagnosisComparisonPanel
            caseId={caseData.id}
          />

          {/* 7. Human Review & Remediation Verification */}
          <HumanReviewPanel
            caseId={caseData.id}
            onCaseUpdated={fetchCase}
          />

          {/* 8. Symptom & Observed Fault Details */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-amber-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Observed Network Symptom
                </h2>
              </div>
              <span className="text-[11px] text-amber-400/90 font-mono">Fault Report</span>
            </div>

            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 font-mono text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
              {caseData.symptom}
            </div>

            {/* Topology Notes if available */}
            {caseData.topology_notes && (
              <div className="space-y-1.5 pt-2">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wide">
                  Topology Notes & Device Designations:
                </h4>
                <div className="bg-slate-950/50 border border-slate-800/60 rounded-xl p-3 font-mono text-xs text-slate-400 leading-relaxed whitespace-pre-wrap">
                  {caseData.topology_notes}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Troubleshooting Workflow Roadmap */}
        <div className="space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                Troubleshooting Workflow
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Multi-stage evidence parsing, rule verification, and human review.
              </p>
            </div>

            {/* Steps Timeline */}
            <div className="space-y-3 text-xs">
              {/* Step 1: PKT Upload */}
              <div className={`p-3 rounded-xl border flex items-start gap-3 transition-colors ${
                caseData.pkt_file
                  ? 'bg-cyan-950/20 border-cyan-500/40 text-cyan-200'
                  : 'bg-slate-950/40 border-slate-800 text-slate-400'
              }`}>
                <div className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${
                  caseData.pkt_file ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-800 text-slate-400'
                }`}>
                  <FileCode2 className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold">1. .PKT Topology Upload</span>
                    {caseData.pkt_file && (
                      <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-1.5 py-0.2 rounded">
                        Done
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {caseData.pkt_file ? caseData.pkt_file.pkt_filename : 'Awaiting .pkt topology file upload'}
                  </p>
                </div>
              </div>

              {/* Step 2: Cisco Evidence */}
              <div className="p-3 rounded-xl border bg-indigo-950/20 border-indigo-500/40 text-indigo-200 flex items-start gap-3 transition-colors">
                <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 shrink-0 mt-0.5">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold">2. Cisco Show Evidence</span>
                    <span className="text-[10px] font-bold text-indigo-300 bg-indigo-950/80 px-1.5 py-0.2 rounded border border-indigo-800">
                      Done / Ready
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Collect show ip interface brief, show ip route, show vlan brief from Packet Tracer.
                  </p>
                </div>
              </div>

              {/* Step 3: Python Rule Engine */}
              <div className="p-3 rounded-xl border bg-purple-950/20 border-purple-500/40 text-purple-200 flex items-start gap-3 transition-colors">
                <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-400 shrink-0 mt-0.5">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold">3. Python Deterministic Rules</span>
                    <span className="text-[10px] font-bold text-purple-300 bg-purple-950/80 px-1.5 py-0.2 rounded border border-purple-800">
                      Done / Active
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Evaluate 7 deterministic fault rules (Duplicate IP, Gateway, Subnet, Interface, VLAN, Route, Link).
                  </p>
                </div>
              </div>

              {/* Step 4: AI Diagnosis & Comparison */}
              <div className="p-3 rounded-xl border bg-gradient-to-r from-fuchsia-950/30 to-indigo-950/30 border-fuchsia-500/40 text-fuchsia-200 flex items-start gap-3 transition-colors">
                <div className="p-1.5 rounded-lg bg-fuchsia-500/20 text-fuchsia-400 shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold">4. AI Diagnosis & Comparison</span>
                    <span className="text-[10px] font-bold text-fuchsia-300 bg-fuchsia-950/80 px-1.5 py-0.2 rounded border border-fuchsia-800">
                      Done / Active
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Independent Gemini reasoning and cross-engine consensus / divergence verification.
                  </p>
                </div>
              </div>

              {/* Step 5: Human Review */}
              <div className="p-3 rounded-xl border bg-emerald-950/20 border-emerald-500/40 text-emerald-200 flex items-start gap-3 transition-colors">
                <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
                  <CheckSquare className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold">5. Mandatory Human Review</span>
                    <span className="text-[10px] font-bold text-emerald-300 bg-emerald-950/80 px-1.5 py-0.2 rounded border border-emerald-800">
                      Active
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    ACCEPT / REJECT / NEEDS_REVIEW decision with audit logging.
                  </p>
                </div>
              </div>

              {/* Step 6: Manual PT Fix & Verification */}
              <div className="p-3 rounded-xl border bg-cyan-950/20 border-cyan-500/40 text-cyan-200 flex items-start gap-3 transition-colors">
                <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 shrink-0 mt-0.5">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold">6. Manual Fix & Verification</span>
                    <span className="text-[10px] font-bold text-cyan-300 bg-cyan-950/80 px-1.5 py-0.2 rounded border border-cyan-800">
                      Active
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Apply manual CLI commands in Packet Tracer and verify with 'Verify After Fix'.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
