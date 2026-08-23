import React from 'react';
import { Link } from 'react-router-dom';
import { FileCode2, ArrowRight } from 'lucide-react';
import type { Case } from '../types';

interface CaseCardProps {
  caseItem: Case;
}

export const CaseCard: React.FC<CaseCardProps> = ({ caseItem }) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-rose-950/70 text-rose-300 border-rose-500/40';
      case 'HIGH':
        return 'bg-orange-950/70 text-orange-300 border-orange-500/40';
      case 'MEDIUM':
        return 'bg-amber-950/70 text-amber-300 border-amber-500/40';
      default:
        return 'bg-blue-950/70 text-blue-300 border-blue-500/40';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return 'bg-emerald-950 text-emerald-300 border-emerald-500/40';
      case 'REVIEW_REQUIRED':
        return 'bg-purple-950 text-purple-300 border-purple-500/40';
      case 'INVESTIGATING':
        return 'bg-cyan-950 text-cyan-300 border-cyan-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-lg transition-all duration-200 hover:-translate-y-0.5 group flex flex-col justify-between">
      <div>
        {/* Header: Case Number + Status */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/50">
            {caseItem.case_number}
          </span>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${getStatusBadge(caseItem.status)}`}>
              {caseItem.status}
            </span>
          </div>
        </div>

        {/* Title */}
        <h3 className="font-bold text-base text-slate-100 group-hover:text-cyan-300 transition-colors line-clamp-1 mb-1.5">
          {caseItem.title}
        </h3>

        {/* Symptom Preview */}
        <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-4">
          {caseItem.symptom}
        </p>
      </div>

      {/* Footer Info */}
      <div className="pt-3 border-t border-slate-800/80 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${getSeverityBadge(caseItem.severity)}`}>
              {caseItem.severity}
            </span>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-slate-800 text-slate-300 rounded border border-slate-700">
              {caseItem.category}
            </span>
          </div>

          {/* PKT file attached badge */}
          {caseItem.pkt_file ? (
            <div className="flex items-center gap-1.5 text-xs text-cyan-400 font-mono" title={caseItem.pkt_file.pkt_filename}>
              <FileCode2 className="w-3.5 h-3.5 text-cyan-400" />
              <span className="truncate max-w-[110px]">{caseItem.pkt_file.pkt_filename}</span>
            </div>
          ) : (
            <span className="text-[11px] text-slate-400 italic">No .pkt attached</span>
          )}
        </div>

        {/* Action Link */}
        <Link
          to={`/cases/${caseItem.id}`}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-slate-800/80 hover:bg-gradient-to-r hover:from-cyan-600 hover:to-blue-600 text-slate-200 hover:text-white text-xs font-semibold transition-all group-hover:shadow-md"
        >
          <span>Open Troubleshooting Workspace</span>
          <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
        </Link>
      </div>
    </div>
  );
};
