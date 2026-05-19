import React from "react";
import type { ClaimEvidenceSnippet } from "../context/VerificationContext";
import { normalizeEvidence } from "../utils/evidence";

export function EvidenceSnippets({
  evidence,
  emptyMessage = "No supporting evidence found in parsed resume sections.",
  header,
}: {
  evidence: unknown;
  emptyMessage?: string;
  header?: string;
}) {
  const rows: ClaimEvidenceSnippet[] = normalizeEvidence(evidence);

  if (!rows.length) {
    return (
      <div className="rounded-lg border border-border bg-secondary/30 p-3">
        {header ? (
          <p className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground mb-2">
            {header}
          </p>
        ) : null}
        <p className="text-xs text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {rows.map((row, i) => (
        <div key={`${row.section}-${row.snippet}-${i}`} className="border-l-2 border-electric-blue/40 pl-2.5 py-0.5">
          <div className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground mb-0.5">
            {row.section.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </div>
          <p className="text-xs text-foreground/90 leading-snug">&ldquo;{row.snippet}&rdquo;</p>
        </div>
      ))}
    </div>
  );
}

