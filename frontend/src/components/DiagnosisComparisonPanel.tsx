import React, { useState } from 'react';
import { 
  GitCompare, 
  Play, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Cpu, 
  Sparkles, 
  ShieldCheck, 
  Wrench, 
  HelpCircle
} from 'lucide-react';
import type { DiagnosisComparisonResult, ComparisonStatus } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';

interface DiagnosisComparisonPanelProps {
  caseId: number | string;
}

export const DiagnosisComparisonPanel: React.FC<DiagnosisComparisonPanelProps> = ({ caseId }) => {
  const [result, setResult] = useState<DiagnosisComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunComparison = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiService.compareDiagnosis(caseId);
      setResult(res);
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to run diagnosis comparison.'));
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeConfig = (status: ComparisonStatus) => {
    switch (status) {
      case 'AGREEMENT':
        return {
          bg: 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300',
          badge: 'bg-emerald-950 text-emerald-300 border-emerald-500/40',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
          label: 'CONSENSUS ACHIEVED',
          accent: 'from-emerald-900/40 via-teal-900/30 to-slate-950'
        };
      case 'DISAGREEMENT':
        return {
          bg: 'bg-amber-950/40 border-amber-500/50 text-amber-300',
          badge: 'bg-amber-950 text-amber-300 border-amber-500/40',
          icon: <AlertTriangle className="w-5 h-5 text-amber-400" />,
          label: 'DIVERGENT FINDINGS',
          accent: 'from-amber-900/40 via-orange-900/30 to-slate-950'
        };
      case 'AI_ONLY':
        return {
          bg: 'bg-purple-950/40 border-purple-500/50 text-purple-300',
          badge: 'bg-purple-950 text-purple-300 border-purple-500/40',
          icon: <Sparkles className="w-5 h-5 text-purple-400" />,
          label: 'NOVEL FAULT (AI ONLY)',
          accent: 'from-purple-900/40 via-indigo-900/30 to-slate-950'
        };
      case 'PYTHON_ONLY':
        return {
          bg: 'bg-blue-950/40 border-blue-500/50 text-blue-300',
          badge: 'bg-blue-950 text-blue-300 border-blue-500/40',
          icon: <Cpu className="w-5 h-5 text-blue-400" />,
          label: 'RULE DETECTED (PYTHON ONLY)',
          accent: 'from-blue-900/40 via-cyan-900/30 to-slate-950'
        };
      default:
        return {
          bg: 'bg-slate-900 border-slate-700 text-slate-300',
          badge: 'bg-slate-800 text-slate-400 border-slate-700',
          icon: <HelpCircle className="w-5 h-5 text-slate-400" />,
          label: 'INSUFFICIENT EVIDENCE',
          accent: 'from-slate-900 to-slate-950'
        };
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-900 via-purple-900 to-cyan-900 border border-indigo-500/40 text-indigo-200 shadow-md">
            <GitCompare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                AI vs Python Diagnosis Comparison Engine
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800">
                Phase 6 Cross-Validation
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Independent consensus evaluation comparing deterministic rules against Gemini AI diagnosis.
            </p>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={handleRunComparison}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02] disabled:opacity-50 self-start sm:self-center"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Comparing Engines...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Compare Python vs AI</span>
            </>
          )}
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Comparison Error: </strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Results View */}
      {result ? (
        <div className="space-y-5">
          {/* Main Verdict Card */}
          {(() => {
            const cfg = getStatusBadgeConfig(result.status);
            return (
              <div className={`p-5 rounded-2xl border ${cfg.bg} bg-gradient-to-br ${cfg.accent} shadow-xl space-y-3`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    {cfg.icon}
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                    {result.aligned_fault_type && (
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-950/80 text-white border border-slate-800">
                        {result.aligned_fault_type}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {result.aligned_device && (
                      <span className="px-2.5 py-0.5 text-[10px] font-mono font-bold bg-slate-950/80 text-cyan-300 border border-cyan-800/60 rounded">
                        Target: {result.aligned_device} {result.aligned_interface ? `• ${result.aligned_interface}` : ''}
                      </span>
                    )}
                    <span className="px-2.5 py-0.5 text-[10px] font-bold bg-slate-950 text-cyan-400 rounded border border-slate-800">
                      {result.confidence_score}% Confidence
                    </span>
                  </div>
                </div>

                <div className="space-y-1 pt-1">
                  <h4 className="text-sm font-bold text-white tracking-tight">
                    {result.verdict_title}
                  </h4>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    {result.explanation}
                  </p>
                </div>
              </div>
            );
          })()}

          {/* Side-by-Side Engine Evaluation Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left Box: Python Deterministic Rule Engine */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 shadow-md flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Python Rule Engine
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-purple-300 font-semibold">
                    Deterministic Rules
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {result.python_summary}
                </p>
              </div>

              {result.python_result && result.python_result.faults_detected.length > 0 ? (
                <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Detected Faults:</span>
                  <div className="space-y-1">
                    {result.python_result.faults_detected.map((f, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-slate-900 border border-purple-500/20 text-[11px] text-purple-200 font-mono">
                        • {f.fault_type} on {f.device} ({f.suggested_correction})
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-2 rounded-lg bg-slate-900/60 text-[11px] text-slate-400 italic">
                  0 deterministic rule violations flagged.
                </div>
              )}
            </div>

            {/* Right Box: Gemini AI Diagnosis */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 shadow-md flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Gemini AI Diagnosis
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-cyan-300 font-semibold">
                    Holistic LLM
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {result.ai_summary}
                </p>
              </div>

              {result.ai_result && result.ai_result.recommended_correction ? (
                <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">AI Recommended Action:</span>
                  <div className="p-2 rounded-lg bg-slate-900 border border-cyan-500/20 text-[11px] text-cyan-200 font-mono">
                    {result.ai_result.recommended_correction}
                  </div>
                </div>
              ) : (
                <div className="p-2 rounded-lg bg-slate-900/60 text-[11px] text-slate-400 italic">
                  No AI recommended correction available.
                </div>
              )}
            </div>
          </div>

          {/* Recommended Action / Packet Tracer Remediation */}
          <div className="p-4 bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-950 rounded-xl border border-indigo-500/30 space-y-2">
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-indigo-300">
              <Wrench className="w-3.5 h-3.5 text-indigo-400" />
              <span>Synthesized Remediation (Packet Tracer Action)</span>
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-mono">
              {result.recommended_action}
            </p>
          </div>

          {/* Mandatory Human Review Notice */}
          <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-slate-300">Human-in-the-Loop Safeguard: </strong>
              <span>
                NetSage AI performs automated diagnosis comparison for advisory review only. Configuration adjustments must be verified and executed manually within Cisco Packet Tracer.
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="py-6 px-4 text-center bg-slate-950/40 rounded-xl border border-slate-800/80 space-y-2">
          <GitCompare className="w-8 h-8 text-indigo-400 mx-auto" />
          <h4 className="text-xs font-bold text-slate-300">Ready for Cross-Engine Verification</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Click <span className="text-indigo-300 font-semibold">Compare Python vs AI</span> above to evaluate consensus, identify discrepancies, or uncover novel faults.
          </p>
        </div>
      )}
    </div>
  );
};
