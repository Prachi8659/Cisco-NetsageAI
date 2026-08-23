import React from 'react';
import { ShieldAlert } from 'lucide-react';

interface SafetyNoticeProps {
  compact?: boolean;
}

export const SafetyNotice: React.FC<SafetyNoticeProps> = ({ compact = false }) => {
  if (compact) {
    return (
      <div className="bg-amber-950/40 border border-amber-500/30 rounded-lg px-3 py-2 flex items-center gap-2 text-xs text-amber-200">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
        <span>
          <strong className="font-semibold text-amber-300">Safety Rule:</strong> Recommendations only. All configuration changes must be performed manually in Cisco Packet Tracer.
        </span>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-slate-900 via-amber-950/30 to-slate-900 border border-amber-500/40 rounded-xl p-4 shadow-lg shadow-amber-950/10">
      <div className="flex items-start gap-3.5">
        <div className="p-2.5 bg-amber-500/20 rounded-lg border border-amber-500/30 text-amber-400 shrink-0">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-amber-300 tracking-wide uppercase">
              Mandatory Human-in-the-Loop & Safety Architecture
            </h4>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-amber-500/20 text-amber-300 rounded border border-amber-500/30">
              STRICT READ-ONLY
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            NetSage AI provides recommendations only. The system <strong className="text-white">NEVER</strong> automatically connects to, modifies, or configures Cisco devices or Packet Tracer topologies. All corrective actions must be validated by a human reviewer and manually applied in Cisco Packet Tracer.
          </p>
        </div>
      </div>
    </div>
  );
};
