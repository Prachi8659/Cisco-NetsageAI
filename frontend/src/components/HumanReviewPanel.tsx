import React, { useState, useEffect } from 'react';
import { 
  CheckSquare, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  ShieldCheck, 
  Wrench, 
  RefreshCw, 
  Clock, 
  UserCheck, 
  History, 
  AlertTriangle, 
  Send, 
  HelpCircle 
} from 'lucide-react';
import type { HumanReviewRecord, ReviewDecision, VerificationStatus } from '../types';
import { apiService } from '../services/api';
import { formatApiError } from '../utils/error';
import { formatLocalDateTime } from '../utils/date';

interface HumanReviewPanelProps {
  caseId: number | string;
  onCaseUpdated?: () => void;
}

export const HumanReviewPanel: React.FC<HumanReviewPanelProps> = ({ caseId, onCaseUpdated }) => {
  const [reviews, setReviews] = useState<HumanReviewRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Review Form State
  const [decision, setDecision] = useState<ReviewDecision>('ACCEPT');
  const [reviewerName, setReviewerName] = useState('Network Operator');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);

  // Remediation Confirm State
  const [remediationNotes, setRemediationNotes] = useState('');
  const [confirmingRemediation, setConfirmingRemediation] = useState(false);

  // Verification State
  const [verifying, setVerifying] = useState(false);
  const [verificationVerdict, setVerificationVerdict] = useState<string | null>(null);

  const fetchReviews = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getCaseReviews(caseId);
      setReviews(data);
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to load review history.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, [caseId]);

  const latestReview = reviews.length > 0 ? reviews[0] : null;

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmittingReview(true);
      setError(null);
      await apiService.submitHumanReview(caseId, {
        decision,
        reviewer_name: reviewerName,
        reviewer_notes: reviewerNotes,
      });
      setReviewerNotes('');
      await fetchReviews();
      if (onCaseUpdated) onCaseUpdated();
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to submit review decision.'));
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleConfirmRemediation = async () => {
    if (!latestReview) return;
    try {
      setConfirmingRemediation(true);
      setError(null);
      await apiService.confirmRemediation(caseId, latestReview.id, remediationNotes);
      setRemediationNotes('');
      await fetchReviews();
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to confirm remediation.'));
    } finally {
      setConfirmingRemediation(false);
    }
  };

  const handleVerifyRemediation = async () => {
    if (!latestReview) return;
    try {
      setVerifying(true);
      setError(null);
      setVerificationVerdict(null);
      const res = await apiService.verifyRemediation(caseId, latestReview.id);
      setVerificationVerdict(res.verdict_message);
      await fetchReviews();
      if (onCaseUpdated) onCaseUpdated();
    } catch (err: unknown) {
      setError(formatApiError(err, 'Failed to run remediation verification.'));
    } finally {
      setVerifying(false);
    }
  };

  const getDecisionBadge = (dec: ReviewDecision) => {
    switch (dec) {
      case 'ACCEPT':
        return 'bg-emerald-950 text-emerald-300 border-emerald-500/40';
      case 'REJECT':
        return 'bg-rose-950 text-rose-300 border-rose-500/40';
      case 'NEEDS_REVIEW':
        return 'bg-amber-950 text-amber-300 border-amber-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getVerificationBadge = (vStatus: VerificationStatus) => {
    switch (vStatus) {
      case 'RESOLVED':
        return {
          bg: 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
          label: 'RESOLVED'
        };
      case 'STILL_PRESENT':
        return {
          bg: 'bg-rose-950/40 border-rose-500/40 text-rose-300',
          icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
          label: 'STILL PRESENT'
        };
      case 'INSUFFICIENT_EVIDENCE':
        return {
          bg: 'bg-amber-950/40 border-amber-500/40 text-amber-300',
          icon: <HelpCircle className="w-4 h-4 text-amber-400" />,
          label: 'INSUFFICIENT EVIDENCE'
        };
      default:
        return {
          bg: 'bg-slate-900 border-slate-700 text-slate-400',
          icon: <Clock className="w-4 h-4 text-slate-400" />,
          label: 'PENDING VERIFICATION'
        };
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-900 via-teal-900 to-slate-900 border border-emerald-500/40 text-emerald-200 shadow-md">
            <CheckSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                Human Review & Remediation Verification
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                Phase 7 Safety & Audit
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Human-in-the-Loop decision gateway, manual Packet Tracer remediation logging, and deterministic verification.
            </p>
          </div>
        </div>

        {/* Safety Badge */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-300 self-start sm:self-center">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Recommendation-Only Safeguard</span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-500/40 rounded-xl flex items-start gap-3 text-xs text-rose-200 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-semibold text-rose-300">Review Error: </strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Section 1: Submit Human Review Decision Form */}
      <form onSubmit={handleSubmitReview} className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
          <div className="flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              1. Record Human Review Decision
            </h4>
          </div>
          <span className="text-[10px] font-mono text-slate-400">Operator Gateway</span>
        </div>

        <div className="space-y-3 text-xs">
          {/* Decision Buttons */}
          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold block text-[11px]">
              Select Review Decision:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <button
                type="button"
                onClick={() => setDecision('ACCEPT')}
                className={`py-2 px-3 rounded-xl border font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                  decision === 'ACCEPT'
                    ? 'bg-emerald-600/30 border-emerald-500 text-emerald-200 shadow-md shadow-emerald-950'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>ACCEPT (Confirm)</span>
              </button>

              <button
                type="button"
                onClick={() => setDecision('NEEDS_REVIEW')}
                className={`py-2 px-3 rounded-xl border font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                  decision === 'NEEDS_REVIEW'
                    ? 'bg-amber-600/30 border-amber-500 text-amber-200 shadow-md shadow-amber-950'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <AlertCircle className="w-4 h-4 text-amber-400" />
                <span>NEEDS REVIEW</span>
              </button>

              <button
                type="button"
                onClick={() => setDecision('REJECT')}
                className={`py-2 px-3 rounded-xl border font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                  decision === 'REJECT'
                    ? 'bg-rose-600/30 border-rose-500 text-rose-200 shadow-md shadow-rose-950'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <XCircle className="w-4 h-4 text-rose-400" />
                <span>REJECT (Dismiss)</span>
              </button>
            </div>
          </div>

          {/* Reviewer Name & Notes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="space-y-1">
              <label className="text-slate-400 font-medium block text-[11px]">
                Reviewer / Operator Handle:
              </label>
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                placeholder="e.g. Senior Network Engineer"
                required
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-400 font-medium block text-[11px]">
                Reviewer Notes / Rationale:
              </label>
              <input
                type="text"
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="e.g. Checked show commands, approved for manual Packet Tracer fix."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={submittingReview}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-950 transition-all hover:scale-[1.01] disabled:opacity-50"
            >
              {submittingReview ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Recording Decision...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Submit Review Decision</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Section 2: Active Review Context & Remediation / Verification Actions */}
      {latestReview && (
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4 text-indigo-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                2. Manual Remediation Confirmation & Verification
              </h4>
            </div>
            <span className="text-[10px] font-mono text-indigo-300">Active Review #{latestReview.id}</span>
          </div>

          {/* Current Decision Summary Card */}
          <div className="p-3.5 bg-slate-900/90 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase rounded border ${getDecisionBadge(latestReview.decision)}`}>
                Decision: {latestReview.decision}
              </span>
              <span className="text-slate-300 font-semibold">
                by {latestReview.reviewer_name}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {latestReview.remediation_confirmed ? (
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold text-[10px] flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  Remediation Confirmed
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold text-[10px] flex items-center gap-1">
                  <Clock className="w-3 h-3 text-amber-400" />
                  Awaiting Fix Confirmation
                </span>
              )}

              {(() => {
                const vConfig = getVerificationBadge(latestReview.verification_status);
                return (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${vConfig.bg}`}>
                    {vConfig.icon}
                    <span>{vConfig.label}</span>
                  </span>
                );
              })()}
            </div>
          </div>

          {/* Remediation Confirmation Controls */}
          {!latestReview.remediation_confirmed ? (
            <div className="p-3.5 bg-gradient-to-r from-indigo-950/30 to-slate-900 rounded-xl border border-indigo-500/30 space-y-3 text-xs">
              <p className="text-slate-300 font-medium">
                Confirm that you have manually executed the recommended CLI commands in Cisco Packet Tracer:
              </p>
              <input
                type="text"
                value={remediationNotes}
                onChange={(e) => setRemediationNotes(e.target.value)}
                placeholder="e.g. Executed 'no shutdown' on PC0 Fa0/0 and verified link lights turned green."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={handleConfirmRemediation}
                disabled={confirmingRemediation}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold shadow-md shadow-indigo-950 transition-all disabled:opacity-50"
              >
                {confirmingRemediation ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving Confirmation...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Confirm Manual Fix Applied</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="p-3.5 bg-emerald-950/20 border border-emerald-500/30 rounded-xl space-y-1 text-xs text-emerald-200">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 font-bold text-emerald-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Manual Fix Confirmed by Operator</span>
                </div>
                {latestReview.remediation_applied_at && (
                  <span className="text-[10px] text-emerald-400/90 font-mono">
                    {formatLocalDateTime(latestReview.remediation_applied_at)}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-300">
                {latestReview.remediation_notes || 'Operator confirmed execution of manual remediation in Cisco Packet Tracer.'}
              </p>
            </div>
          )}

          {/* Section 3: Verify After Fix Action */}
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-800/80">
            <div className="space-y-0.5">
              <span className="text-xs font-bold text-white block">3. Deterministic Verification After Fix</span>
              <p className="text-[11px] text-slate-400">
                Re-evaluates deterministic Python rules against updated .pkt topology and CLI show evidence.
              </p>
            </div>

            <button
              type="button"
              onClick={handleVerifyRemediation}
              disabled={verifying}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-950 transition-all hover:scale-[1.01] disabled:opacity-50 shrink-0"
            >
              {verifying ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Evaluating Rules...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Verify After Fix</span>
                </>
              )}
            </button>
          </div>

          {/* Verification Verdict Banner if available */}
          {verificationVerdict && (
            <div className="p-4 bg-slate-900 border border-cyan-500/30 rounded-xl space-y-1 text-xs animate-in fade-in">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm">
                  <ShieldCheck className="w-5 h-5 text-cyan-400" />
                  <span>Verification Outcome</span>
                </div>
                {latestReview.verified_at && (
                  <span className="text-[10px] text-cyan-400/80 font-mono">
                    {formatLocalDateTime(latestReview.verified_at)}
                  </span>
                )}
              </div>
              <p className="text-slate-200 leading-relaxed font-mono text-[11px]">
                {verificationVerdict}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Section 4: Audit Trail History */}
      <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-slate-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              4. Review & Remediation Audit Trail
            </h4>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            {reviews.length} Logged Action{reviews.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading ? (
          <div className="py-6 text-center text-xs text-slate-400">
            <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-slate-500" />
            Loading audit history...
          </div>
        ) : reviews.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500 italic">
            No review or verification actions recorded yet for this case.
          </div>
        ) : (
          <div className="space-y-2.5">
            {reviews.map((rev) => (
              <div key={rev.id} className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded border ${getDecisionBadge(rev.decision)}`}>
                      {rev.decision}
                    </span>
                    <span className="font-semibold text-slate-200">
                      {rev.reviewer_name}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span>{formatLocalDateTime(rev.created_at)}</span>
                  </div>
                </div>

                {rev.reviewer_notes && (
                  <p className="text-[11px] text-slate-300 italic">
                    "{rev.reviewer_notes}"
                  </p>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/60 text-[10px]">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">
                      Fix Status: <strong className={rev.remediation_confirmed ? 'text-emerald-400' : 'text-amber-400'}>{rev.remediation_confirmed ? 'Confirmed Applied' : 'Pending'}</strong>
                    </span>
                    {rev.remediation_applied_at && (
                      <span className="text-slate-500 font-mono text-[9px]">
                        ({formatLocalDateTime(rev.remediation_applied_at)})
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">
                      Verification: <strong className={rev.verification_status === 'RESOLVED' ? 'text-emerald-400' : 'text-slate-300'}>{rev.verification_status}</strong>
                    </span>
                    {rev.verified_at && (
                      <span className="text-slate-500 font-mono text-[9px]">
                        ({formatLocalDateTime(rev.verified_at)})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
