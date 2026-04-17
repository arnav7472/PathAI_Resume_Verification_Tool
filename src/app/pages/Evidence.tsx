import React from 'react';
import { Link } from 'react-router';
import { useVerification } from '../context/VerificationContext';

export function Evidence() {
  const { currentScan } = useVerification();

  if (!currentScan) {
    return (
      <div className="h-64 flex flex-col items-center justify-center border border-slate-900 rounded bg-slate-900/10">
        <p className="text-slate-500 text-sm mb-4">No active scan results found.</p>
        <Link to="/" className="text-xs font-bold text-indigo-500 hover:underline">Run your first scan</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-white">Evidence</h1>
      <p className="text-xs text-slate-500 max-w-lg">
        Backend findings, extracted claims, and timeline entries used to summarize the resume analysis for {currentScan.candidateName}.
      </p>

      <div className="space-y-3">
        {currentScan.findings.map((finding, i) => (
          <div key={i} className="flex gap-4 p-4 border border-slate-900 rounded bg-slate-900/10">
            <div className="text-[10px] uppercase font-bold text-slate-600 w-16 pt-1">{finding.severity}</div>
            <div className="flex-1">
              <p className="text-sm text-slate-300">{finding.message}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 p-6 border border-slate-900 rounded bg-indigo-950/5">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Extracted Claims</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {currentScan.claims.length > 0 ? currentScan.claims.map((claim, index) => (
            <div key={`${claim.type}-${claim.value}-${index}`} className="space-y-1 rounded border border-slate-900 bg-slate-900/20 p-4">
              <p className="text-[10px] text-slate-600 font-bold uppercase">{claim.type}</p>
              <p className="text-sm text-white">{claim.value}</p>
              {typeof claim.evidence_count === 'number' && (
                <p className="text-xs text-slate-500">Evidence count: {claim.evidence_count}</p>
              )}
            </div>
          )) : (
            <p className="text-sm text-slate-500">No claims were extracted from this resume.</p>
          )}
        </div>
      </div>

      <div className="mt-8 p-6 border border-slate-900 rounded bg-slate-900/10">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Timeline</h3>
        {currentScan.timeline.length > 0 ? (
          <div className="space-y-3">
            {currentScan.timeline.map((entry, index) => (
              <div key={`${entry.start_year}-${entry.end_year}-${index}`} className="flex items-center justify-between rounded border border-slate-900 bg-slate-900/20 p-4">
                <span className="text-sm text-white">{entry.start_year}</span>
                <span className="text-xs uppercase tracking-widest text-slate-600">to</span>
                <span className="text-sm text-white">{entry.end_year}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No timeline entries were detected.</p>
        )}
      </div>
    </div>
  );
}
