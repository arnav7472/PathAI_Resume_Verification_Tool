import type { ClaimEvidenceSnippet } from "../context/VerificationContext";

export type EvidenceSnippet = { section: string; snippet: string };

export function normalizeEvidence(evidence: unknown): EvidenceSnippet[] {
  if (!Array.isArray(evidence)) return [];

  return (evidence
    .map((item) => {
      if (typeof item === "string") {
        return { section: "resume", snippet: item };
      }

      if (
        item &&
        typeof item === "object" &&
        "section" in item &&
        "snippet" in item
      ) {
        const v = item as { section: unknown; snippet: unknown };
        return {
          section: String(v.section ?? "resume"),
          snippet: String(v.snippet ?? ""),
        };
      }

      return null;
    })
    .filter(Boolean) as EvidenceSnippet[]).filter((s) => s.snippet.trim().length > 0);
}

export function normalizeClaimEvidence(
  evidence: unknown
): ClaimEvidenceSnippet[] {
  return normalizeEvidence(evidence);
}

