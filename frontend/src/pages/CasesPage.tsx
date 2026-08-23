import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  PlusCircle, 
  Search, 
  FileCode2, 
  FolderKanban, 
  ShieldAlert, 
  RefreshCw
} from 'lucide-react';
import type { Case } from '../types';
import { apiService } from '../services/api';
import { CaseCard } from '../components/CaseCard';
import { SafetyNotice } from '../components/SafetyNotice';

const CATEGORIES = ['All', 'VLAN', 'Routing', 'Gateway', 'DHCP', 'ACL', 'NAT', 'Interface', 'General'];

export const CasesPage: React.FC = () => {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getCases();
      setCases(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load cases.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const filteredCases = cases.filter((c) => {
    const matchesCategory = selectedCategory === 'All' || c.category.toLowerCase() === selectedCategory.toLowerCase();
    const query = searchQuery.toLowerCase();
    const matchesSearch = 
      c.title.toLowerCase().includes(query) ||
      c.case_number.toLowerCase().includes(query) ||
      c.symptom.toLowerCase().includes(query) ||
      (c.pkt_file?.pkt_filename.toLowerCase().includes(query) ?? false);
    return matchesCategory && matchesSearch;
  });

  const totalPktCases = cases.filter((c) => !!c.pkt_file).length;

  return (
    <div className="space-y-6">
      {/* Safety Notice Banner */}
      <SafetyNotice />

      {/* Hero Stats & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FolderKanban className="w-6 h-6 text-cyan-400" />
            <h1 className="text-2xl font-black text-white tracking-tight">
              Cisco Packet Tracer Troubleshooting Cases
            </h1>
          </div>
          <p className="text-xs text-slate-400">
            Select an active troubleshooting case, inspect network symptoms, upload <span className="text-cyan-300 font-mono font-medium">.pkt</span> topologies, and review diagnostic findings.
          </p>
        </div>

        {/* Quick Stats Counter */}
        <div className="flex items-center gap-3">
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-2.5 text-center min-w-[100px]">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Cases</span>
            <span className="text-lg font-black text-white">{cases.length}</span>
          </div>

          <div className="bg-slate-950/80 border border-cyan-900/40 rounded-xl px-4 py-2.5 text-center min-w-[100px]">
            <span className="text-[10px] uppercase font-bold text-cyan-400 block">.PKT Attached</span>
            <span className="text-lg font-black text-cyan-300">{totalPktCases}</span>
          </div>

          <Link
            to="/cases/new"
            className="flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-cyan-600/20 transition-all hover:scale-[1.02]"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create Case</span>
          </Link>
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/40 border border-slate-800 rounded-xl p-3">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by case #, symptom, or .pkt filename..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {cat}
            </button>
          ))}

          <button
            onClick={fetchCases}
            className="p-2 rounded-lg bg-slate-950/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors shrink-0"
            title="Refresh list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Case Grid or Empty States */}
      {loading ? (
        <div className="py-20 text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading cases from repository...</p>
        </div>
      ) : error ? (
        <div className="p-6 bg-rose-950/40 border border-rose-500/40 rounded-2xl text-center space-y-2">
          <ShieldAlert className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="font-bold text-rose-200 text-sm">Failed to load cases</h3>
          <p className="text-xs text-rose-300">{error}</p>
          <button
            onClick={fetchCases}
            className="mt-2 px-3 py-1.5 bg-rose-900/60 hover:bg-rose-900 text-white rounded-lg text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 mx-auto">
            <FileCode2 className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white">No troubleshooting cases found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              {searchQuery || selectedCategory !== 'All'
                ? 'No cases match your filter criteria. Try adjusting the search or category.'
                : 'Get started by creating your first Cisco Packet Tracer troubleshooting case.'}
            </p>
          </div>
          <Link
            to="/cases/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl text-xs font-bold shadow-md"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create New Case</span>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCases.map((c) => (
            <CaseCard key={c.id} caseItem={c} />
          ))}
        </div>
      )}
    </div>
  );
};
