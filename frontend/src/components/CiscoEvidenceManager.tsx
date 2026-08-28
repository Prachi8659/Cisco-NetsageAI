import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  Plus, 
  Trash2, 
  RefreshCw, 
  AlertTriangle, 
  Copy, 
  Check, 
  Layers, 
  Network, 
  GitBranch, 
  ShieldAlert, 
  FileText,
  Info
} from 'lucide-react';
import type { CiscoEvidence, NormalizedNetworkFacts } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';

interface CiscoEvidenceManagerProps {
  caseId: number | string;
  suggestedDevices?: string[];
}

const COMMON_COMMANDS = [
  'show ip interface brief',
  'show ip route',
  'show vlan brief',
  'show interfaces trunk',
  'show running-config',
  'show access-lists',
  'show ip dhcp binding',
  'show ip dhcp pool',
  'show interfaces',
  'show mac address-table',
];

export const CiscoEvidenceManager: React.FC<CiscoEvidenceManagerProps> = ({
  caseId,
  suggestedDevices = [],
}) => {
  const [evidenceList, setEvidenceList] = useState<CiscoEvidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [device, setDevice] = useState('');
  const [command, setCommand] = useState('show ip interface brief');
  const [rawOutput, setRawOutput] = useState('');
  const [activeViews, setActiveViews] = useState<Record<number, 'raw' | 'parsed'>>({});
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchEvidence = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getEvidence(caseId);
      setEvidenceList(data);
      // Default new items to parsed view if facts exist
      const initialViews: Record<number, 'raw' | 'parsed'> = {};
      data.forEach((e) => {
        initialViews[e.id] = e.parser_status === 'SUCCESS' || e.parser_status === 'PARTIAL' ? 'parsed' : 'raw';
      });
      setActiveViews(initialViews);
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to load Cisco evidence.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, [caseId]);

  const handleAddEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!device.trim() || !command.trim() || !rawOutput.trim()) {
      setError('Please provide Device name, Command string, and paste raw CLI output.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const created = await apiService.createEvidence(caseId, {
        device: device.trim(),
        command: command.trim(),
        raw_output: rawOutput.trim(),
      });
      setEvidenceList([created, ...evidenceList]);
      setActiveViews((prev) => ({
        ...prev,
        [created.id]: created.parser_status === 'SUCCESS' || created.parser_status === 'PARTIAL' ? 'parsed' : 'raw',
      }));
      setRawOutput('');
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to add and parse Cisco evidence.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteEvidence = async (evidenceId: number) => {
    if (!window.confirm('Are you sure you want to remove this evidence record?')) return;
    try {
      await apiService.deleteEvidence(caseId, evidenceId);
      setEvidenceList(evidenceList.filter((e) => e.id !== evidenceId));
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to delete evidence.'));
    }
  };

  const handleReparseEvidence = async (evidenceId: number) => {
    try {
      const parsed = await apiService.parseEvidence(caseId, evidenceId);
      setEvidenceList((prev) =>
        prev.map((e) => (e.id === evidenceId ? { ...e, parser_status: parsed.status, parsed_facts: parsed.facts, warnings: parsed.warnings } : e))
      );
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to re-parse evidence.'));
    }
  };

  const handleCopyRaw = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s === 'SUCCESS') return 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40';
    if (s === 'PARTIAL') return 'bg-amber-950/80 text-amber-300 border-amber-500/40';
    if (s === 'FAILED') return 'bg-rose-950/80 text-rose-300 border-rose-500/40';
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-900 to-blue-900 border border-indigo-700 text-indigo-300 shadow-md">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">Cisco Show-Command Evidence</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800">
                {evidenceList.length} {evidenceList.length === 1 ? 'Record' : 'Records'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Collect, preserve, and deterministically parse real Cisco Packet Tracer command outputs into normalized facts.
            </p>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Evidence Error: </strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Input Form Card */}
      <form onSubmit={handleAddEvidence} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-200 uppercase tracking-wide">
          <Plus className="w-4 h-4 text-indigo-400" />
          <span>Add New Cisco Command Output</span>
        </div>

        {/* Row 1: Target Device & Command Input */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              Device Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={device}
              onChange={(e) => setDevice(e.target.value)}
              placeholder="e.g. R1, Switch0, PC1"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
            />
            {suggestedDevices.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <span className="text-[10px] text-slate-400">Topology:</span>
                {suggestedDevices.map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDevice(d)}
                    className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono transition-colors"
                  >
                    {d}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="md:col-span-2 space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              Cisco Command <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="e.g. show ip interface brief"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
            />
          </div>
        </div>

        {/* Quick Command Selector Pills */}
        <div className="space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Supported Command Presets:</span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {COMMON_COMMANDS.map((cmd) => (
              <button
                key={cmd}
                type="button"
                onClick={() => setCommand(cmd)}
                className={`px-2 py-1 rounded-lg text-[11px] font-mono transition-colors ${
                  command.toLowerCase() === cmd.toLowerCase()
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>

        {/* Monospace Raw Output Textarea */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-200 block">
            Command Output <span className="text-rose-400">*</span>
          </label>
          <textarea
            required
            rows={6}
            value={rawOutput}
            onChange={(e) => setRawOutput(e.target.value)}
            placeholder={`Paste raw Cisco Packet Tracer command output here...\n\nExample:\nInterface              IP-Address      OK? Method Status                Protocol\nGigabitEthernet0/0     192.168.1.1     YES manual up                    up`}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs text-emerald-400 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors font-mono leading-relaxed resize-y"
          />
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02] disabled:opacity-50"
          >
            {submitting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Storing & Parsing Evidence...</span>
              </>
            ) : (
              <>
                <Terminal className="w-4 h-4" />
                <span>Add Cisco Evidence</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Evidence List */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-8 text-center text-xs text-slate-400 space-y-2">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-indigo-400" />
            <p>Loading case evidence records...</p>
          </div>
        ) : evidenceList.length === 0 ? (
          <div className="py-8 px-4 text-center bg-slate-950/40 rounded-2xl border border-slate-800/80 space-y-2">
            <Terminal className="w-8 h-8 text-slate-400 mx-auto" />
            <h4 className="text-xs font-bold text-slate-300">No Cisco Evidence Attached Yet</h4>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Run commands in Cisco Packet Tracer (e.g. <span className="font-mono text-indigo-300">show ip interface brief</span>) and paste the raw output above to parse real network facts.
            </p>
          </div>
        ) : (
          evidenceList.map((item) => {
            const activeTab = activeViews[item.id] || 'parsed';
            const parsedFacts = item.parsed_facts as NormalizedNetworkFacts | null;

            return (
              <div key={item.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-lg transition-all">
                {/* Evidence Item Header */}
                <div className="p-4 bg-slate-950/60 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="px-2.5 py-1 rounded-lg bg-indigo-950 border border-indigo-800 text-indigo-300 font-mono font-bold text-xs">
                      {item.device}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-white">{item.command}</span>
                        <span className={`px-2 py-0.5 text-[9px] font-bold rounded border uppercase ${getStatusBadge(item.parser_status)}`}>
                          {item.parser_status}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        Added: {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Controls */}
                  <div className="flex items-center gap-2 self-end sm:self-center">
                    {/* View Toggle */}
                    <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs">
                      <button
                        type="button"
                        onClick={() => setActiveViews((prev) => ({ ...prev, [item.id]: 'parsed' }))}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          activeTab === 'parsed' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Parsed Facts
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveViews((prev) => ({ ...prev, [item.id]: 'raw' }))}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          activeTab === 'raw' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Raw Output
                      </button>
                    </div>

                    {/* Re-parse */}
                    <button
                      type="button"
                      title="Re-parse evidence output"
                      onClick={() => handleReparseEvidence(item.id)}
                      className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>

                    {/* Delete */}
                    <button
                      type="button"
                      title="Delete evidence record"
                      onClick={() => handleDeleteEvidence(item.id)}
                      className="p-1.5 rounded-lg bg-slate-950 hover:bg-rose-950/60 border border-slate-800 text-slate-400 hover:text-rose-300 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Evidence Content Body */}
                <div className="p-4">
                  {activeTab === 'raw' ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>Original Terminal Output (Unmodified)</span>
                        <button
                          type="button"
                          onClick={() => handleCopyRaw(item.id, item.raw_output)}
                          className="inline-flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
                        >
                          {copiedId === item.id ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy Raw</span>
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                        {item.raw_output}
                      </pre>
                    </div>
                  ) : (
                    /* Parsed Facts Display */
                    <div className="space-y-4">
                      {/* Warnings if any */}
                      {item.warnings && item.warnings.length > 0 && (
                        <div className="p-3 bg-amber-950/40 border border-amber-500/30 rounded-xl space-y-1 text-xs">
                          <div className="flex items-center gap-1.5 font-bold text-amber-300">
                            <Info className="w-3.5 h-3.5 text-amber-400" />
                            <span>Parser Report</span>
                          </div>
                          <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                            {item.warnings.map((w, idx) => (
                              <li key={idx}>{w}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Interfaces */}
                      {parsedFacts?.interfaces && parsedFacts.interfaces.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                            <Network className="w-4 h-4 text-cyan-400" />
                            <span>Parsed Interfaces ({parsedFacts.interfaces.length})</span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs border border-slate-800 rounded-xl overflow-hidden">
                              <thead className="bg-slate-950 text-slate-400 font-bold uppercase text-[10px]">
                                <tr>
                                  <th className="p-2 border-b border-slate-800">Interface</th>
                                  <th className="p-2 border-b border-slate-800">IP Address</th>
                                  <th className="p-2 border-b border-slate-800">Subnet Mask</th>
                                  <th className="p-2 border-b border-slate-800">Status</th>
                                  <th className="p-2 border-b border-slate-800">Protocol</th>
                                  <th className="p-2 border-b border-slate-800">Source</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/80 font-mono text-[11px]">
                                {parsedFacts.interfaces.map((intf, idx) => (
                                  <tr key={idx} className="hover:bg-slate-800/30">
                                    <td className="p-2 font-bold text-blue-300">{intf.name}</td>
                                    <td className="p-2 text-cyan-300">{intf.ip || 'unassigned'}</td>
                                    <td className="p-2 text-slate-400">{intf.mask || '—'}</td>
                                    <td className="p-2">
                                      <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${
                                        intf.status.toUpperCase() === 'UP' ? 'bg-emerald-950 text-emerald-300' : 'bg-rose-950 text-rose-300'
                                      }`}>
                                        {intf.status}
                                      </span>
                                    </td>
                                    <td className="p-2 text-slate-300">{intf.protocol}</td>
                                    <td className="p-2">
                                      <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                                        CISCO_EVIDENCE
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Routes */}
                      {parsedFacts?.routes && parsedFacts.routes.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                            <GitBranch className="w-4 h-4 text-emerald-400" />
                            <span>Parsed Routing Table ({parsedFacts.routes.length})</span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs border border-slate-800 rounded-xl overflow-hidden">
                              <thead className="bg-slate-950 text-slate-400 font-bold uppercase text-[10px]">
                                <tr>
                                  <th className="p-2 border-b border-slate-800">Network</th>
                                  <th className="p-2 border-b border-slate-800">Protocol</th>
                                  <th className="p-2 border-b border-slate-800">Next Hop</th>
                                  <th className="p-2 border-b border-slate-800">Interface</th>
                                  <th className="p-2 border-b border-slate-800">AD/Metric</th>
                                  <th className="p-2 border-b border-slate-800">Source</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/80 font-mono text-[11px]">
                                {parsedFacts.routes.map((r, idx) => (
                                  <tr key={idx} className="hover:bg-slate-800/30">
                                    <td className="p-2 font-bold text-emerald-300">
                                      {r.network} {r.is_default && <span className="text-amber-300 text-[10px]">(default)</span>}
                                    </td>
                                    <td className="p-2 text-slate-300">{r.protocol || 'Direct'}</td>
                                    <td className="p-2 text-cyan-300">{r.next_hop || '—'}</td>
                                    <td className="p-2 text-blue-300">{r.interface || '—'}</td>
                                    <td className="p-2 text-slate-400">
                                      {r.admin_distance !== null && r.admin_distance !== undefined ? `[${r.admin_distance}/${r.metric || 0}]` : '—'}
                                    </td>
                                    <td className="p-2">
                                      <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                                        CISCO_EVIDENCE
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* VLANs */}
                      {parsedFacts?.vlans && parsedFacts.vlans.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                            <Layers className="w-4 h-4 text-indigo-400" />
                            <span>Parsed VLANs ({parsedFacts.vlans.length})</span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {parsedFacts.vlans.map((v, idx) => (
                              <div key={idx} className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-xs font-mono">
                                <div className="flex items-center justify-between">
                                  <span className="text-indigo-300 font-bold">VLAN {v.vlan_id} ({v.name})</span>
                                  <span className="px-1.5 py-0.5 text-[9px] rounded bg-emerald-950 text-emerald-300">{v.status}</span>
                                </div>
                                {v.ports && v.ports.length > 0 && (
                                  <p className="text-[10px] text-slate-400 mt-1 truncate">
                                    Ports: {v.ports.join(', ')}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Trunks */}
                      {parsedFacts?.trunks && parsedFacts.trunks.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                            <Layers className="w-4 h-4 text-purple-400" />
                            <span>Parsed Trunks ({parsedFacts.trunks.length})</span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {parsedFacts.trunks.map((t, idx) => (
                              <div key={idx} className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-xs font-mono space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="text-purple-300 font-bold">{t.port}</span>
                                  <span className="text-slate-400 text-[10px]">Native VLAN: {t.native_vlan || 1}</span>
                                </div>
                                <p className="text-[10px] text-slate-400">
                                  Allowed: {t.allowed_vlans || 'All'} | Encap: {t.encapsulation || '802.1q'}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* ACLs */}
                      {parsedFacts?.acls && parsedFacts.acls.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                            <ShieldAlert className="w-4 h-4 text-amber-400" />
                            <span>Parsed Access Lists ({parsedFacts.acls.length})</span>
                          </div>
                          <div className="space-y-2">
                            {parsedFacts.acls.map((acl, idx) => (
                              <div key={idx} className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-xs font-mono space-y-1.5">
                                <div className="flex items-center justify-between text-amber-300 font-bold">
                                  <span>ACL {acl.acl_name_or_number} ({acl.acl_type})</span>
                                  <span className="text-[10px] text-slate-400">{acl.rules.length} Rules</span>
                                </div>
                                <ul className="space-y-0.5 text-[11px] text-slate-300 pl-2 border-l border-slate-800">
                                  {acl.rules.map((r, rIdx) => (
                                    <li key={rIdx} className={r.action === 'permit' ? 'text-emerald-300' : 'text-rose-300'}>
                                      {r.raw_rule}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* MAC Table */}
                      {parsedFacts?.mac_entries && parsedFacts.mac_entries.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                            <FileText className="w-4 h-4 text-blue-400" />
                            <span>Parsed MAC Address Table ({parsedFacts.mac_entries.length})</span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs border border-slate-800 rounded-xl overflow-hidden font-mono text-[11px]">
                              <thead className="bg-slate-950 text-slate-400 font-bold uppercase text-[10px]">
                                <tr>
                                  <th className="p-2 border-b border-slate-800">VLAN</th>
                                  <th className="p-2 border-b border-slate-800">MAC Address</th>
                                  <th className="p-2 border-b border-slate-800">Type</th>
                                  <th className="p-2 border-b border-slate-800">Port</th>
                                  <th className="p-2 border-b border-slate-800">Source</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/80">
                                {parsedFacts.mac_entries.map((m, idx) => (
                                  <tr key={idx} className="hover:bg-slate-800/30">
                                    <td className="p-2 text-indigo-300">{m.vlan_id || 'All'}</td>
                                    <td className="p-2 text-slate-200">{m.mac_address}</td>
                                    <td className="p-2 text-slate-400">{m.entry_type}</td>
                                    <td className="p-2 text-blue-300">{m.port}</td>
                                    <td className="p-2">
                                      <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                                        CISCO_EVIDENCE
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Fallback if no specific structured fact matched */}
                      {(!parsedFacts || Object.values(parsedFacts).every((v) => !Array.isArray(v) || v.length === 0)) && (
                        <p className="text-xs text-slate-400 italic py-2">
                          No structured network facts extracted from this command. Check the Raw Output tab.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
