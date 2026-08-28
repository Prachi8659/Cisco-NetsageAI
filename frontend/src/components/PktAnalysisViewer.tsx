import React, { useState } from 'react';
import { 
  Play, 
  RefreshCw, 
  Server, 
  Network, 
  Layers, 
  ShieldAlert, 
  AlertTriangle, 
  Cpu, 
  Info,
  GitBranch,
  FileCode2
} from 'lucide-react';
import type { PktAnalysisResult, FactSource, AnalysisStatus } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';

interface PktAnalysisViewerProps {
  caseId: number | string;
  hasPktFile: boolean;
  onAnalysisComplete?: (result: PktAnalysisResult) => void;
}

export const PktAnalysisViewer: React.FC<PktAnalysisViewerProps> = ({
  caseId,
  hasPktFile,
  onAnalysisComplete,
}) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<PktAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'topology' | 'devices' | 'interfaces' | 'vlans_routes'>('topology');

  const handleAnalyze = async () => {
    if (!hasPktFile) {
      setError('Please upload a Cisco Packet Tracer (.pkt) file before running analysis.');
      return;
    }

    try {
      setAnalyzing(true);
      setError(null);
      const res = await apiService.analyzePktFile(caseId);
      setResult(res);
      if (onAnalysisComplete) {
        onAnalysisComplete(res);
      }
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to analyze .pkt file.'));
    } finally {
      setAnalyzing(false);
    }
  };

  const getStatusBadge = (status: AnalysisStatus) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-emerald-950 text-emerald-300 border-emerald-500/40';
      case 'PARTIAL':
        return 'bg-amber-950 text-amber-300 border-amber-500/40';
      case 'UNAVAILABLE':
        return 'bg-slate-800 text-slate-300 border-slate-700';
      case 'FAILED':
        return 'bg-rose-950 text-rose-300 border-rose-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getSourceBadge = (source: FactSource) => {
    switch (source) {
      case 'PKT_EXTRACTED':
        return 'bg-cyan-950 text-cyan-300 border-cyan-500/40';
      case 'UNKNOWN':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      case 'INSUFFICIENT_EVIDENCE':
        return 'bg-amber-950 text-amber-400 border-amber-500/40';
      default:
        return 'bg-blue-950 text-blue-300 border-blue-800';
    }
  };

  const facts = result?.facts;
  const hasExtractedData = facts && (facts.devices.length > 0 || facts.connections.length > 0 || facts.interfaces.length > 0);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      {/* Header & Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Packet Tracer (.pkt) Topology Analysis
              </h3>
              {result && (
                <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${getStatusBadge(result.status)}`}>
                  {result.status}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic extraction of devices, interfaces, IP addresses, and topology connections.
            </p>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={analyzing || !hasPktFile}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/20 transition-all hover:scale-[1.02] disabled:opacity-50 shrink-0"
        >
          {analyzing ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Analyzing .pkt Structure...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              <span>{result ? 'Re-Analyze .pkt' : 'Analyze .pkt'}</span>
            </>
          )}
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3.5 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Analysis Error: </strong>
            {error}
          </div>
        </div>
      )}

      {/* When no analysis has run yet */}
      {!result && !analyzing && (
        <div className="py-6 px-4 text-center bg-slate-950/40 rounded-xl border border-slate-800/80 space-y-2">
          <FileCode2 className="w-6 h-6 text-slate-400 mx-auto" />
          <p className="text-xs text-slate-400">
            {hasPktFile
              ? 'Click "Analyze .pkt" to extract normalized network facts and topology from the uploaded file.'
              : 'Please upload a Cisco Packet Tracer (.pkt) file above to enable topology extraction.'}
          </p>
        </div>
      )}

      {/* Analysis Result Display */}
      {result && (
        <div className="space-y-4">
          {/* Status & Warning Notice */}
          {result.warnings && result.warnings.length > 0 && (
            <div className="p-3.5 bg-slate-950/80 border border-amber-500/30 rounded-xl space-y-1.5 text-xs">
              <div className="flex items-center gap-2 text-amber-300 font-bold">
                <Info className="w-4 h-4 text-amber-400" />
                <span>Extraction & Compatibility Report</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-slate-300 text-[11px] pl-1">
                {result.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* If data was extracted, show navigation tabs */}
          {hasExtractedData ? (
            <div className="space-y-3">
              {/* Tab Navigation */}
              <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
                <button
                  type="button"
                  onClick={() => setActiveTab('topology')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    activeTab === 'topology'
                      ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>Topology Connections ({facts.connections.length})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('devices')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    activeTab === 'devices'
                      ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  <Server className="w-3.5 h-3.5" />
                  <span>
                    Network Devices ({facts.devices.filter(d => d.is_network_device !== false).length}
                    {facts.devices.some(d => d.is_network_device === false)
                      ? ` + ${facts.devices.filter(d => d.is_network_device === false).length} Infra`
                      : ''})
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('interfaces')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    activeTab === 'interfaces'
                      ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>Interfaces ({facts.interfaces.length})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('vlans_routes')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    activeTab === 'vlans_routes'
                      ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>VLANs & Routes ({facts.vlans.length + facts.routes.length})</span>
                </button>
              </div>

              {/* Tab 1: Topology Connections */}
              {activeTab === 'topology' && (
                <div className="space-y-2.5">
                  {facts.connections.length === 0 ? (
                    <p className="text-xs text-slate-400 py-3 text-center">No physical connections extracted.</p>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {facts.connections.map((conn, idx) => (
                        <div key={idx} className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 flex items-center justify-between gap-3 text-xs">
                          <div className="flex items-center gap-2">
                            <div className="p-1.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800 font-mono font-bold text-[11px]">
                              {conn.device_a}
                            </div>
                            <span className="text-[11px] text-slate-400 font-mono">({conn.interface_a})</span>
                          </div>

                          <div className="flex flex-col items-center">
                            <span className="text-[10px] text-cyan-400 font-mono font-semibold">
                              {conn.status}
                            </span>
                            <span className="w-12 h-0.5 bg-gradient-to-r from-blue-500 to-cyan-500 rounded my-0.5" />
                            <span className="text-[9px] text-slate-400">{conn.link_type || 'Copper'}</span>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] text-slate-400 font-mono">({conn.interface_b})</span>
                            <div className="p-1.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800 font-mono font-bold text-[11px]">
                              {conn.device_b}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Devices */}
              {activeTab === 'devices' && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-slate-800 rounded-xl overflow-hidden">
                    <thead className="bg-slate-950 text-slate-400 font-bold uppercase text-[10px]">
                      <tr>
                        <th className="p-2.5 border-b border-slate-800">Device Name</th>
                        <th className="p-2.5 border-b border-slate-800">Classification</th>
                        <th className="p-2.5 border-b border-slate-800">Model</th>
                        <th className="p-2.5 border-b border-slate-800">Default Gateway</th>
                        <th className="p-2.5 border-b border-slate-800">Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 text-slate-200 font-mono text-[11px]">
                      {facts.devices.map((dev, idx) => {
                        const gw = facts.gateways.find(g => g.device === dev.name)?.gateway_ip;
                        const isNetwork = dev.is_network_device !== false;
                        return (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="p-2.5 font-bold text-cyan-300">{dev.name}</td>
                            <td className="p-2.5">
                              <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                                isNetwork
                                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/30'
                                  : 'bg-amber-950/80 text-amber-300 border border-amber-500/30'
                              }`}>
                                {isNetwork ? `Network: ${dev.device_type}` : 'Infrastructure Object'}
                              </span>
                            </td>
                            <td className="p-2.5 text-slate-400">{dev.model || 'Generic'}</td>
                            <td className="p-2.5 text-amber-300">{gw || 'N/A'}</td>
                            <td className="p-2.5">
                              <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded border ${getSourceBadge(dev.source)}`}>
                                {dev.source}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Tab 3: Interfaces */}
              {activeTab === 'interfaces' && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-slate-800 rounded-xl overflow-hidden">
                    <thead className="bg-slate-950 text-slate-400 font-bold uppercase text-[10px]">
                      <tr>
                        <th className="p-2.5 border-b border-slate-800">Device</th>
                        <th className="p-2.5 border-b border-slate-800">Interface</th>
                        <th className="p-2.5 border-b border-slate-800">IP Address</th>
                        <th className="p-2.5 border-b border-slate-800">Subnet Mask</th>
                        <th className="p-2.5 border-b border-slate-800">Physical Link</th>
                        <th className="p-2.5 border-b border-slate-800">Status</th>
                        <th className="p-2.5 border-b border-slate-800">VLAN</th>
                        <th className="p-2.5 border-b border-slate-800">Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 text-slate-200 font-mono text-[11px]">
                      {facts.interfaces.map((intf, idx) => {
                        const statusUpper = intf.status.toUpperCase();
                        let statusColor = 'bg-slate-800 text-slate-300 border border-slate-700';
                        if (statusUpper === 'UP') statusColor = 'bg-emerald-950 text-emerald-300 border border-emerald-500/40';
                        else if (statusUpper === 'DOWN') statusColor = 'bg-rose-950 text-rose-300 border border-rose-500/40';
                        else if (statusUpper === 'ADMINISTRATIVELY_DOWN') statusColor = 'bg-amber-950 text-amber-300 border border-amber-500/40';

                        return (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="p-2.5 font-bold text-blue-300">{intf.device}</td>
                            <td className="p-2.5 text-slate-200">{intf.name}</td>
                            <td className="p-2.5 text-cyan-300">{intf.ip || 'unassigned'}</td>
                            <td className="p-2.5 text-slate-400">{intf.mask || 'unassigned'}</td>
                            <td className="p-2.5">
                              <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${
                                intf.is_connected
                                  ? 'bg-blue-950 text-blue-300 border border-blue-500/40'
                                  : 'bg-slate-900 text-slate-400 border border-slate-800'
                              }`}>
                                {intf.is_connected ? 'Connected' : 'Not Connected'}
                              </span>
                            </td>
                            <td className="p-2.5">
                              <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${statusColor}`}>
                                {intf.status}
                              </span>
                            </td>
                            <td className="p-2.5 text-indigo-300">{intf.vlan_id ? `VLAN ${intf.vlan_id}` : '—'}</td>
                            <td className="p-2.5">
                              <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded border ${getSourceBadge(intf.source)}`}>
                                {intf.source}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Tab 4: VLANs & Routes */}
              {activeTab === 'vlans_routes' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* VLANs */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 space-y-2">
                    <h4 className="text-xs font-bold text-slate-300 uppercase">Extracted VLANs</h4>
                    {facts.vlans.length === 0 ? (
                      <p className="text-[11px] text-slate-400 italic">No specific VLAN declarations found.</p>
                    ) : (
                      <ul className="space-y-1 text-xs font-mono">
                        {facts.vlans.map((v, idx) => (
                          <li key={idx} className="p-1.5 bg-slate-900 rounded flex items-center justify-between text-[11px]">
                            <span className="text-indigo-300 font-bold">VLAN {v.vlan_id} ({v.name})</span>
                            <span className="text-slate-400 text-[10px]">{v.device}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Routes */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 space-y-2">
                    <h4 className="text-xs font-bold text-slate-300 uppercase">Extracted Routes</h4>
                    {facts.routes.length === 0 ? (
                      <p className="text-[11px] text-slate-400 italic">No routing table entries embedded.</p>
                    ) : (
                      <ul className="space-y-1 text-xs font-mono">
                        {facts.routes.map((r, idx) => (
                          <li key={idx} className="p-1.5 bg-slate-900 rounded flex items-center justify-between text-[11px]">
                            <span className="text-emerald-300 font-bold">{r.network}</span>
                            <span className="text-slate-400 text-[10px]">via {r.next_hop || 'direct'} ({r.device})</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* When raw proprietary encryption prevents direct XML recovery */
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-300">
                <ShieldAlert className="w-4 h-4 text-cyan-400" />
                <span>Evidence-First Architecture Policy</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Because this file is in proprietary encrypted Packet Tracer binary format, internal XML topology was not directly recoverable without external proprietary keys. In compliance with NetSage AI integrity guidelines, <strong className="text-slate-200">zero synthetic facts have been fabricated</strong>.
              </p>
              <div className="pt-2 flex items-center gap-2 text-[11px] text-cyan-400 font-mono">
                <span>➡ Next step: Provide Cisco show-command outputs in Stage 2 to parse active facts.</span>
              </div>
            </div>
          )}

          {/* Footer Source Attribution */}
          <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
            <span>Authoritative Source: <strong className="text-cyan-400">{result.source}</strong></span>
            <span>Extracted at: {new Date(result.extracted_at).toLocaleTimeString()}</span>
          </div>
        </div>
      )}
    </div>
  );
};
