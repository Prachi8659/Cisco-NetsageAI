import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { CasesPage } from './pages/CasesPage';
import { CaseDetailPage } from './pages/CaseDetailPage';
import { CreateCasePage } from './pages/CreateCasePage';

export const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        {/* Navigation Bar */}
        <Navbar />

        {/* Main Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<CasesPage />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/cases/new" element={<CreateCasePage />} />
            <Route path="/cases/:id" element={<CaseDetailPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* Global Technical Footer */}
        <footer className="border-t border-slate-900 bg-slate-950/60 py-6 text-center text-xs text-slate-400">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-300">NetSage AI</span>
              <span>—</span>
              <span>AI-Assisted Cisco Packet Tracer Troubleshooting Platform</span>
            </div>
            <p className="text-[11px] text-amber-300/80">
              Recommendations only. Cisco network changes are performed manually in Packet Tracer.
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
};

export default App;
