import React, { useState } from 'react';
import { 
  Cpu, 
  Play, 
  RefreshCw, 
  AlertOctagon, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldCheck, 
  Layers, 
  Info,
  Wrench
} from 'lucide-react';
import type { RuleEngineResult, RuleFinding, RuleSeverity } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';

interface PythonRuleAnalysisProps {
  caseId: number | string;
}

const SEVERITY_COLORS: Record<RuleSeverity, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: 'bg-rose-950/80', text: 'text-rose-300', border: 'border-rose-500/50' },
  HIGH: { bg: 'bg-orange-950/80', text: 'text-orange-300', border: 'border-orange-500/50' },
  MEDIUM: { bg: 'bg-amber-950/80', text: 'text-amber-300', border: 'border-amber-500/50' },
  LOW: { bg: 'bg-blue-950/80', text: 'text-blue-300', border: 'border-blue-500/50' },
};

export const PythonRuleAnalysis: React.FC<PythonRuleAnalysisProps> = ({
  caseId,
}) => {
  const [result, setResult] = useState<RuleEngineResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunAnalysis = async () => {
    try {
      setRunning(true);
      setError(null);
      const res = await apiService.diagnoseWithRules(caseId);
      setResult(res);
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to run Python rule analysis.'));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-900 via-purple-900 to-blue-900 border border-indigo-600/40 text-indigo-300 shadow-md">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                Python Rule-Based Fault Detection
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800">
                7 Deterministic Rules
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Evaluates aggregated .pkt facts and Cisco CLI evidence against 7 verified networking fault rules.
            </p>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={handleRunAnalysis}
          disabled={running}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02] disabled:opacity-50 self-start sm:self-center"
        >
          {running ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Evaluating Rules...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Run Python Analysis</span>
            </>
          )}
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Rule Engine Error: </strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Results Body */}
      {result ? (
        <div className="space-y-5">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-slate-400 text-[11px] block">Rules Evaluated</span>
                <span className="text-sm font-bold text-white font-mono">{result.total_rules_evaluated} Rules</span>
              </div>
              <Layers className="w-5 h-5 text-indigo-400" />
            </div>

            <div className={`rounded-xl p-3.5 border flex items-center justify-between ${
              result.faults_detected.length > 0 
                ? 'bg-rose-950/30 border-rose-500/40 text-rose-300' 
                : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
            }`}>
              <div>
                <span className="text-[11px] block opacity-80">Faults Detected</span>
                <span className="text-sm font-bold font-mono">
                  {result.faults_detected.length} {result.faults_detected.length === 1 ? 'Fault' : 'Faults'}
                </span>
              </div>
              {result.faults_detected.length > 0 ? (
                <AlertOctagon className="w-5 h-5 text-rose-400" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              )}
            </div>

            <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-slate-400 text-[11px] block">Clean Rules</span>
                <span className="text-sm font-bold text-emerald-400 font-mono">
                  {result.no_fault_rules.length} Passed
                </span>
              </div>
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            </div>
          </div>

          {/* Faults List */}
          {result.faults_detected.length > 0 ? (
            <div className="space-y-3.5">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>Detected Network Faults ({result.faults_detected.length})</span>
              </div>

              {result.faults_detected.map((fault: RuleFinding, idx: number) => {
                const colors = SEVERITY_COLORS[fault.severity] || SEVERITY_COLORS.HIGH;

                return (
                  <div 
                    key={idx} 
                    className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 shadow-md hover:border-slate-700 transition-colors"
                  >
                    {/* Top Row: Severity, Title, Device */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded border uppercase ${colors.bg} ${colors.text} ${colors.border}`}>
                          {fault.severity}
                        </span>
                        <h4 className="text-xs font-bold text-white">
                          {fault.fault_type}
                        </h4>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800 rounded">
                          {fault.device} {fault.interface ? `• ${fault.interface}` : ''}
                        </span>
                        <span className="px-1.5 py-0.5 text-[9px] font-bold bg-slate-800 text-slate-300 rounded border border-slate-700">
                          {(fault.confidence * 100).toFixed(0)}% Confidence
                        </span>
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-slate-200 leading-relaxed">
                      {fault.description}
                    </p>

                    {/* Evidence Quote */}
                    <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800/80 space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                        <span>Supporting Evidence</span>
                        <span className="px-1.5 py-0.2 rounded bg-slate-800 text-indigo-300 border border-indigo-900/60 font-mono text-[9px]">
                          SOURCE: {fault.source}
                        </span>
                      </div>
                      <p className="font-mono text-[11px] text-emerald-400">
                        {fault.evidence}
                      </p>
                    </div>

                    {/* Suggested Correction */}
                    <div className="p-3 bg-indigo-950/30 rounded-lg border border-indigo-500/20 space-y-1">
                      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-300">
                        <Wrench className="w-3 h-3 text-indigo-400" />
                        <span>Recommended Correction (Packet Tracer)</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {fault.suggested_correction}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Clean State */
            <div className="p-5 bg-emerald-950/20 border border-emerald-500/30 rounded-xl flex items-center gap-3.5 text-xs text-emerald-200">
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              <div>
                <strong className="font-bold text-emerald-300 block text-xs">
                  No Faults Detected by Python Rule Engine
                </strong>
                <span className="text-[11px] text-slate-300">
                  All 7 deterministic rules (Duplicate IP, Subnet Mask, Gateway, Interface Status, VLAN, Route, and Link Consistency) evaluated cleanly against available network facts.
                </span>
              </div>
            </div>
          )}

          {/* Passing Rules List */}
          {result.no_fault_rules.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Verified Clean Rule Checks:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {result.no_fault_rules.map((rName) => (
                  <span 
                    key={rName}
                    className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-slate-300 border border-slate-800 flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    {rName}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Insufficient Evidence Section if any */}
          {result.insufficient_evidence.length > 0 && (
            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5 text-xs">
              <div className="flex items-center gap-1.5 text-amber-300 font-bold text-[11px]">
                <Info className="w-3.5 h-3.5 text-amber-400" />
                <span>Insufficient Evidence Notes</span>
              </div>
              <ul className="list-disc list-inside text-slate-400 text-[11px] space-y-0.5">
                {result.insufficient_evidence.map((ie, idx) => (
                  <li key={idx}>{ie.description}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        /* Empty Prompt State before running */
        <div className="py-6 px-4 text-center bg-slate-950/40 rounded-xl border border-slate-800/80 space-y-2">
          <Cpu className="w-8 h-8 text-slate-400 mx-auto" />
          <h4 className="text-xs font-bold text-slate-300">Ready to Evaluate Network Facts</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Click <span className="text-indigo-300 font-semibold">Run Python Analysis</span> above to execute all 7 deterministic fault detection rules over your case facts.
          </p>
        </div>
      )}
    </div>
  );
};
