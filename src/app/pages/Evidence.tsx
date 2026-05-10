import React from 'react';
import { Link } from 'react-router';
import { useVerification } from '../context/VerificationContext';

function badgeClasses(status: string) {
  switch (status) {
    case 'verified':
      return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';
    case 'inflated':
      return 'bg-amber-500/10 text-amber-300 border-amber-500/20';
    case 'buzzword':
      return 'bg-rose-500/10 text-rose-300 border-rose-500/20';
    default:
      return 'bg-sky-500/10 text-sky-300 border-sky-500/20';
  }
}

export function Evidence() {
  const { currentScan } = useVerification();

  if (!currentScan) {
    return (
      <div className="glass-card h-64 flex flex-col items-center justify-center border border-border rounded-xl">
        <p className="text-muted-foreground text-sm mb-4">No active scan results found.</p>
        <Link to="/" className="text-xs font-semibold text-electric-blue hover:underline">Run your first scan</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Evidence</h1>
        <p className="text-sm text-muted-foreground max-w-2xl mt-1">
          Claim-to-evidence links, timeline entries, risk findings, and missing evidence warnings for {currentScan.candidateName}.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {currentScan.evidence.length > 0 ? currentScan.evidence.map((item, index) => (
          <div key={`${item.claim}-${index}`} className="glass-card rounded-xl border border-border p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">{item.type}</p>
                <h2 className="text-sm font-semibold text-foreground mt-1">{item.claim}</h2>
              </div>
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${badgeClasses(item.status)}`}>
                {item.status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Confidence</span>
              <span className="text-xs text-foreground font-bold">{item.confidence}%</span>
              <div className="h-1 w-20 rounded-full bg-secondary overflow-hidden">
                <div className="h-full bg-electric-blue" style={{ width: `${Math.max(0, Math.min(100, item.confidence))}%` }} />
              </div>
            </div>
            <div className="space-y-2">
              {item.evidence.length > 0 ? item.evidence.map((snippet, i) => (
                <p key={`${snippet}-${i}`} className="text-xs text-muted-foreground leading-relaxed border-l border-border pl-3">
                  {snippet}
                </p>
              )) : (
                <p className="text-xs text-amber-300">No supporting resume sentence found.</p>
              )}
            </div>
            {item.warning && <p className="text-xs text-amber-300">{item.warning}</p>}
          </div>
        )) : (
          <div className="glass-card rounded-xl border border-border p-4">
            <p className="text-sm text-muted-foreground">No claim evidence was extracted.</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="glass-card p-5 border border-border rounded-xl">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-4">Risk Findings</h3>
          <div className="space-y-3">
            {currentScan.findings.map((finding, i) => (
              <div key={`${finding.message}-${i}`} className="flex gap-4 p-3 border border-border rounded-lg bg-secondary/40">
                <div className="text-[10px] uppercase font-bold text-muted-foreground w-16 pt-1">{finding.severity}</div>
                <p className="text-sm text-foreground flex-1">{finding.message}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-card p-5 border border-border rounded-xl">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-4">Timeline</h3>
          {currentScan.timeline.length > 0 ? (
            <div className="space-y-3">
              {currentScan.timeline.map((entry, index) => (
                <div key={`${entry.start_year}-${entry.end_year}-${index}`} className="rounded-lg border border-border bg-secondary/40 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground">{entry.start_year}</span>
                    <span className="text-xs uppercase tracking-widest text-muted-foreground">to</span>
                    <span className="text-sm text-foreground">{entry.end_year}</span>
                  </div>
                  {entry.evidence && <p className="text-xs text-muted-foreground mt-2">{entry.evidence}</p>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No timeline entries were detected.</p>
          )}
        </section>
      </div>
    </div>
  );
}
