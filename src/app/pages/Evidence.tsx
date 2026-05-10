import React, { useMemo } from 'react';
import { Link } from 'react-router';
import type { ClaimEvidenceSnippet, EvidenceItem, EvidenceLevel } from '../context/VerificationContext';
import { useVerification } from '../context/VerificationContext';

function legacyBadgeClasses(status: string) {
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

function levelBadgeClasses(level?: EvidenceLevel | string) {
  switch (level) {
    case 'demonstrated':
      return 'bg-emerald-500/15 text-emerald-200 border-emerald-500/25';
    case 'supported':
      return 'bg-sky-500/15 text-sky-200 border-sky-500/25';
    case 'mentioned':
      return 'bg-amber-500/15 text-amber-200 border-amber-500/25';
    case 'weak':
      return 'bg-orange-500/15 text-orange-200 border-orange-500/25';
    case 'missing':
      return 'bg-rose-500/15 text-rose-200 border-rose-500/25';
    default:
      return 'bg-muted/30 text-muted-foreground border-border';
  }
}

function confidenceBarClass(pct: number) {
  if (pct >= 85) return 'bg-emerald-500';
  if (pct >= 70) return 'bg-sky-500';
  if (pct >= 45) return 'bg-amber-500';
  if (pct >= 20) return 'bg-orange-500';
  return 'bg-rose-500';
}

function normalizeSnippets(evidence: EvidenceItem['evidence']): ClaimEvidenceSnippet[] {
  if (!evidence?.length) return [];
  const first = evidence[0];
  if (typeof first === 'string') {
    return (evidence as string[]).map((s) => ({ section: 'resume', snippet: s }));
  }
  return evidence as ClaimEvidenceSnippet[];
}

function sectionLabel(section: string) {
  return section.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Evidence() {
  const { currentScan } = useVerification();

  const overlapWarnings = useMemo(() => {
    const ta = currentScan?.timelineAnalysis;
    if (!ta?.overlaps?.length) return [] as string[];
    return ta.overlaps;
  }, [currentScan]);

  if (!currentScan) {
    return (
      <div className="glass-card h-64 flex flex-col items-center justify-center border border-border rounded-xl">
        <p className="text-muted-foreground text-sm mb-4">No active scan results found.</p>
        <Link to="/" className="text-xs font-semibold text-electric-blue hover:underline">
          Run your first scan
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Evidence</h1>
        <p className="text-sm text-muted-foreground max-w-2xl mt-1">
          Sentence-level snippets grouped by resume section, confidence bands, and explainable status tiers for{' '}
          {currentScan.candidateName}.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {currentScan.evidence.length > 0 ? (
          currentScan.evidence.map((item, index) => {
            const rows = normalizeSnippets(item.evidence);
            const level = item.evidence_level;
            const pct = Math.max(0, Math.min(100, item.confidence));

            return (
              <div key={`${item.claim}-${index}`} className="glass-card rounded-xl border border-border p-3 space-y-2.5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">{item.type}</p>
                    <h2 className="text-sm font-semibold text-foreground mt-0.5 break-words">
                      {item.skill ?? item.claim}
                    </h2>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    {level && (
                      <span
                        className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${levelBadgeClasses(level)}`}
                      >
                        {level}
                      </span>
                    )}
                    <span
                      className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${legacyBadgeClasses(item.status)}`}
                    >
                      {item.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] text-muted-foreground uppercase font-bold">Confidence</span>
                  <span className="text-xs text-foreground font-bold">{pct}%</span>
                  <div className="h-1 flex-1 min-w-[4rem] max-w-[120px] rounded-full bg-secondary overflow-hidden">
                    <div className={`h-full ${confidenceBarClass(pct)}`} style={{ width: `${pct}%` }} />
                  </div>
                  {item.evidence_type && (
                    <span className="text-[10px] px-1.5 py-0 rounded border border-border text-muted-foreground uppercase font-bold">
                      {item.evidence_type}
                    </span>
                  )}
                </div>

                <div className="space-y-2">
                  {rows.length > 0 ? (
                    rows.map((row, i) => (
                      <div key={`${row.snippet}-${i}`} className="border-l-2 border-electric-blue/40 pl-2.5 py-0.5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground mb-0.5">
                          {sectionLabel(row.section)}
                        </div>
                        <p className="text-xs text-foreground/90 leading-snug">&ldquo;{row.snippet}&rdquo;</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-amber-300">No sentence-level snippet — claim may be inferred only.</p>
                  )}
                </div>

                {item.warning ? <p className="text-xs text-amber-300/90 pt-0.5">{item.warning}</p> : null}
              </div>
            );
          })
        ) : (
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

        <section className="glass-card p-5 border border-border rounded-xl space-y-4">
          <div>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3">Timeline</h3>
            {currentScan.timeline.length > 0 ? (
              <div className="space-y-3">
                {currentScan.timeline.map((entry, index) => (
                  <div key={`${entry.start_year}-${entry.end_year}-${index}`} className="rounded-lg border border-border bg-secondary/40 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-foreground">{entry.start_year}</span>
                      <span className="text-[10px] uppercase tracking-widest text-muted-foreground">to</span>
                      <span className="text-sm text-foreground">{entry.end_year}</span>
                    </div>
                    {entry.evidence && <p className="text-xs text-muted-foreground mt-2 line-clamp-3">{entry.evidence}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No timeline entries were detected.</p>
            )}
          </div>

          {overlapWarnings.length > 0 && (
            <div>
              <h4 className="text-[10px] font-bold text-amber-300/90 uppercase tracking-widest mb-2">Continuity / overlap</h4>
              <ul className="text-xs text-muted-foreground space-y-1.5 list-disc pl-4">
                {overlapWarnings.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}

          {currentScan.skillTimelineInsights && currentScan.skillTimelineInsights.length > 0 && (
            <div>
              <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2">Skill → earliest signal</h4>
              <div className="flex flex-wrap gap-2">
                {currentScan.skillTimelineInsights.slice(0, 12).map((s) => (
                  <span
                    key={s.skill}
                    className="text-[11px] rounded border border-border bg-secondary/60 px-2 py-1 text-foreground"
                    title={s.experience_years_estimate != null ? `≈ ${s.experience_years_estimate} yr span in text` : ''}
                  >
                    {s.skill}
                    {s.first_seen ? ` · ${s.first_seen}` : ''}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
