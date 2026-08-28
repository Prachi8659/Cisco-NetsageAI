import React, { useState } from 'react';
import { 
  Sparkles, 
  Play, 
  RefreshCw, 
  AlertTriangle, 
  AlertOctagon, 
  CheckCircle2, 
  ShieldAlert, 
  Layers, 
  Wrench, 
  FileText,
  Activity,
  Bot
} from 'lucide-react';
import type { AiDiagnosisResult } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';

interface AiDiagnosisPanelProps {
  caseId: number | string;
}

export const AiDiagnosisPanel: React.FC<AiDiagnosisPanelProps> = ({ caseId }) => {
  const [result, setResult] = useState<AiDiagnosisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunAiDiagnosis = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiService.diagnoseWithAi(caseId);
      setResult(res);
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to run AI diagnosis.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-900 via-fuchsia-900 to-indigo-900 border border-purple-500/40 text-purple-200 shadow-md">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                AI-Assisted Network Diagnosis
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">
                Independent Reasoning
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Evidence-first holistic LLM reasoning analyzing .pkt facts, Cisco CLI evidence, and symptoms.
            </p>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={handleRunAiDiagnosis}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-fuchsia-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-600/20 transition-all hover:scale-[1.02] disabled:opacity-50 self-start sm:self-center"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>AI Analyzing Evidence...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Run AI Diagnosis</span>
            </>
          )}
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">AI Service Error: </strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Results View */}
      {result ? (
        <div className="space-y-4">
          {/* Status: AI_UNAVAILABLE */}
          {result.status === 'AI_UNAVAILABLE' && (
            <div className="p-5 bg-amber-950/20 border border-amber-500/30 rounded-xl space-y-2 text-xs text-amber-200">
              <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
                <span>AI Service Unavailable</span>
              </div>
              <p className="text-slate-300 leading-relaxed">
                {result.explanation || 'Configure the AI provider (AI_API_KEY) in the backend environment to enable AI-assisted network diagnosis.'}
              </p>
              <div className="pt-1 text-[11px] text-slate-400">
                Notice: The deterministic <span className="text-purple-300 font-semibold">Python Rule Engine</span> remains fully functional and operates independently.
              </div>
            </div>
          )}

          {/* Status: INSUFFICIENT_EVIDENCE */}
          {result.status === 'INSUFFICIENT_EVIDENCE' && (
            <div className="p-5 bg-amber-950/20 border border-amber-500/30 rounded-xl space-y-2 text-xs text-amber-200">
              <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <span>Insufficient Evidence for AI Diagnosis</span>
              </div>
              <p className="text-slate-300 leading-relaxed">
                {result.explanation || 'The available Packet Tracer and Cisco evidence is not sufficient to definitively determine the root cause without guessing.'}
              </p>
              {result.recommended_correction && (
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 font-mono">
                  Recommended Action: {result.recommended_correction}
                </div>
              )}
            </div>
          )}

          {/* Status: FAILED */}
          {result.status === 'FAILED' && (
            <div className="p-5 bg-rose-950/30 border border-rose-500/40 rounded-xl space-y-2 text-xs text-rose-200">
              <div className="flex items-center gap-2 text-rose-300 font-bold text-sm">
                <AlertOctagon className="w-5 h-5 text-rose-400" />
                <span>AI Diagnosis Inconclusive / Failed</span>
              </div>
              <p className="text-slate-300 leading-relaxed">
                {result.explanation}
              </p>
            </div>
          )}

          {/* Status: SUCCESS */}
          {result.status === 'SUCCESS' && (
            <div className="space-y-4">
              {/* Top Row: Meta bar */}
              <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold text-[10px] uppercase tracking-wider flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    Diagnosis Success
                  </span>
                  {result.fault_type && (
                    <span className="px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-bold text-[10px]">
                      {result.fault_type}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2.5 text-xs">
                  {result.affected_device && (
                    <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800 rounded">
                      Device: {result.affected_device} {result.affected_interface ? `• ${result.affected_interface}` : ''}
                    </span>
                  )}
                  <span className="px-2 py-0.5 text-[10px] font-bold bg-slate-800 text-cyan-300 rounded border border-slate-700">
                    {result.confidence}% Confidence
                  </span>
                </div>
              </div>

              {/* Root Cause Card */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2 shadow-md">
                <div className="flex items-center gap-2 text-[11px] font-bold text-purple-300 uppercase tracking-wider">
                  <Bot className="w-4 h-4 text-purple-400" />
                  <span>Identified Root Cause</span>
                </div>
                <p className="text-xs text-white font-semibold leading-relaxed">
                  {result.root_cause}
                </p>
              </div>

              {/* Supporting Evidence List */}
              {result.evidence && result.evidence.length > 0 && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <Activity className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Observable Supporting Evidence</span>
                  </div>
                  <ul className="space-y-1 text-xs text-slate-200">
                    {result.evidence.map((item: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2 font-mono text-[11px] text-emerald-400">
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Technical Explanation */}
              {result.explanation && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-1.5 text-xs text-slate-300 leading-relaxed">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <FileText className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Technical Impact Explanation</span>
                  </div>
                  <p>{result.explanation}</p>
                </div>
              )}

              {/* Recommended Manual Correction in Packet Tracer */}
              {result.recommended_correction && (
                <div className="p-4 bg-gradient-to-r from-purple-950/40 to-indigo-950/40 rounded-xl border border-purple-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-purple-300">
                    <Wrench className="w-3.5 h-3.5 text-purple-400" />
                    <span>Recommended Manual Correction (Packet Tracer)</span>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed font-mono">
                    {result.recommended_correction}
                  </p>
                </div>
              )}

              {/* Reasoning Summary */}
              {result.reasoning_summary && (
                <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-2">
                  <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-slate-300">Reasoning Summary: </strong>
                    <span>{result.reasoning_summary}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Empty Prompt State */
        <div className="py-6 px-4 text-center bg-slate-950/40 rounded-xl border border-slate-800/80 space-y-2">
          <Sparkles className="w-8 h-8 text-purple-400 mx-auto" />
          <h4 className="text-xs font-bold text-slate-300">Ready for AI Root Cause Analysis</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Click <span className="text-purple-300 font-semibold">Run AI Diagnosis</span> above to initiate independent, evidence-first AI troubleshooting.
          </p>
        </div>
      )}
    </div>
  );
};
