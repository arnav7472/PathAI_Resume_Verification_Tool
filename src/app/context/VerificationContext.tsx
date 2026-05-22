import React, { createContext, useContext, useEffect, useState } from 'react';

const getApiBaseUrl = () => {
  // Same-origin API: FastAPI serves both the frontend and API endpoints.
  // In development, Vite dev server proxies to the FastAPI backend.
  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:8000';
  }
  return '';
};
const API_BASE_URL = getApiBaseUrl();

export type Finding = {
  message: string;
  severity: 'high' | 'medium' | 'low';
};

export type EvidenceLevel = 'demonstrated' | 'supported' | 'mentioned' | 'weak' | 'missing';

export type ClaimEvidenceSnippet = { section: string; snippet: string };

export type Claim = {
  type: string;
  value: string;
  skill?: string;
  claim?: string;
  evidence?: ClaimEvidenceSnippet[] | string[];
  supporting_evidence?: string;
  confidence?: number;
  status?: 'verified' | 'inflated' | 'buzzword' | 'likely';
  /** Structured verification quality for skill claims */
  evidence_level?: EvidenceLevel;
  evidence_type?: 'direct' | 'indirect' | 'missing';
  evidence_count?: number;
};

export type TimelineEntry = {
  start_year: number;
  end_year: number | 'present';
  evidence?: string;
};

export type EvidenceItem = {
  claim: string;
  type: string;
  skill?: string;
  evidence_level?: EvidenceLevel;
  status: 'verified' | 'inflated' | 'buzzword' | 'likely';
  confidence: number;
  evidence: ClaimEvidenceSnippet[] | string[];
  evidence_type?: string;
  warning?: string;
};

export type ClaimView = {
  name: string;
  category: string;
  claimed: string;
  conf: number;
  status: 'Verified' | 'Inflated' | 'Buzzword' | 'Likely';
  /** New pipeline: human-readable evidence tier */
  evidenceLevel?: EvidenceLevel | string;
  evidences?: ClaimEvidenceSnippet[];
  evidenceType?: string;
  reason: string;
};

export type TimelineAnalysis = {
  overlaps?: string[];
  gaps?: string[];
  suspicious_inflation?: string[];
};

export type SkillTimelineInsight = {
  skill: string;
  first_seen: string | null;
  experience_years_estimate: number | null;
};

export type ScanResult = {
  id: string;
  candidateName: string;
  jobDescription: string;
  date: string;
  riskScore: number;
  confidence: number;
  compatibilityScore: number;
  verdict: string;
  findings: Finding[];
  claims: Claim[];
  evidence: EvidenceItem[];
  timeline: TimelineEntry[];
  timelineAnalysis?: TimelineAnalysis;
  skillTimelineInsights?: SkillTimelineInsight[];
  extractedText: string;
  claimViews: ClaimView[];
  skills: string[];
  actionVerbs: string[];
  matchedSkills: string[];
  missingSkills: string[];
  weakAreas: string[];
  strictness: 'low' | 'medium' | 'high';
  crossReferenceSync: boolean;
  // Explainability layer
  executiveSummary?: string;
  riskSummary?: string;
  confidenceExplanation?: string;
  riskBreakdown?: string;
  positiveEvidenceSummary?: string[];
  confidenceReason?: string;
  // Operational warnings (extraction quality, OCR issues)
  extractionWarnings?: string[];
};

type VerificationInput = {
  name: string;
  jobDescription: string;
  file: File | null;
  text?: string;
};

type VerificationContextType = {
  currentScan: ScanResult | null;
  history: ScanResult[];
  runVerification: (data: VerificationInput) => Promise<void>;
  setCurrentScan: (scan: ScanResult) => void;
};

const VerificationContext = createContext<VerificationContextType | undefined>(undefined);

function toSentenceCase(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function toRiskLevel(riskScore: number) {
  if (riskScore >= 60) return 'High';
  if (riskScore >= 30) return 'Moderate';
  return 'Low';
}

function parseClaimEvidence(claim: Claim): ClaimEvidenceSnippet[] {
  const raw = claim.evidence;
  if (!raw || !Array.isArray(raw)) return [];
  const first = raw[0];
  if (first && typeof first === 'object' && 'snippet' in first) {
    return raw as ClaimEvidenceSnippet[];
  }
  return (raw as string[]).map((s) => ({ section: 'resume', snippet: s }));
}

function mapClaimToView(claim: Claim): ClaimView {
  // Backend evidence tiers are the source of truth; legacy statuses are fallback UI labels.
  const evidenceCount = claim.evidence_count ?? 0;
  const rawStatus = claim.status;
  const statusMap = {
    verified: 'Verified',
    inflated: 'Inflated',
    buzzword: 'Buzzword',
    likely: 'Likely',
  } as const;
  const evidences = parseClaimEvidence(claim);
  const evLevel = claim.evidence_level;

  let status: ClaimView['status'] = rawStatus ? statusMap[rawStatus] : 'Likely';
  if (evLevel === 'demonstrated' || evLevel === 'supported') {
    status = 'Verified';
  } else if (evLevel === 'weak' || evLevel === 'missing') {
    status = 'Inflated';
  } else if (evLevel === 'mentioned') {
    status = 'Likely';
  } else if (!evLevel && claim.type === 'skill') {
    if (evidenceCount >= 3) status = 'Verified';
    else if (evidenceCount === 1) status = 'Inflated';
  }

  const claimedSummary =
    evidences.length > 0
      ? evidences
          .slice(0, 2)
          .map((e) => `${e.section}: ${e.snippet}`)
          .join(' · ')
      : claim.supporting_evidence ||
        (evidenceCount > 0 ? `${evidenceCount} supporting mention${evidenceCount === 1 ? '' : 's'}` : '—');

  let reason: string;
  if (evLevel === 'demonstrated') {
    reason = 'Implementation-style wording found in experience, projects, or achievements.';
  } else if (evLevel === 'supported') {
    reason = 'Technical context outside a bare skills line.';
  } else if (evLevel === 'mentioned') {
    reason = 'Primarily listed as a keyword without strong implementation bullets.';
  } else if (evLevel === 'weak') {
    reason = 'Vague mention with little technical context.';
  } else if (evLevel === 'missing') {
    reason = 'Expected from the job description but not located in parsed sections.';
  } else if (claim.supporting_evidence) {
    reason = claim.supporting_evidence;
  } else {
    reason =
      evidenceCount > 0
        ? `${evidenceCount} supporting mention${evidenceCount === 1 ? '' : 's'} in resume text.`
        : 'Detected claim.';
  }

  if (claim.type === 'skill') {
    return {
      name: claim.skill ?? claim.claim ?? claim.value,
      category: 'Skill Claim',
      claimed: claimedSummary.slice(0, 520),
      conf: claim.confidence ?? Math.max(20, Math.min(95, evidenceCount * 25)),
      status,
      evidenceLevel: evLevel,
      evidences,
      evidenceType: claim.evidence_type,
      reason,
    };
  }

  return {
    name: claim.claim ?? claim.value,
    category: toSentenceCase(claim.type),
    claimed: claimedSummary.slice(0, 520),
    conf: claim.confidence ?? 70,
    status,
    evidenceLevel: evLevel,
    evidences,
    evidenceType: claim.evidence_type,
    reason,
  };
}

function normalizeStoredScan(scan: Partial<ScanResult>): ScanResult {
  // LocalStorage can contain older report shapes, so normalize before rendering.
  const claims = Array.isArray(scan.claims) ? scan.claims : [];
  const findings = Array.isArray(scan.findings) ? scan.findings : [];
  const timeline = Array.isArray(scan.timeline) ? scan.timeline : [];
  const evidence = Array.isArray(scan.evidence) ? scan.evidence : [];
  const claimViews = Array.isArray(scan.claimViews) && scan.claimViews.length > 0 ? scan.claimViews : claims.map(mapClaimToView);

  return {
    id: scan.id ?? `PX-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
    candidateName: scan.candidateName ?? 'Unknown Candidate',
    jobDescription: scan.jobDescription ?? (scan as Partial<ScanResult> & { role?: string }).role ?? '',
    date: scan.date ?? new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    riskScore: typeof scan.riskScore === 'number' ? scan.riskScore : 0,
    confidence: typeof scan.confidence === 'number' ? scan.confidence : 0,
    compatibilityScore: typeof scan.compatibilityScore === 'number' ? scan.compatibilityScore : 0,
    verdict: scan.verdict ?? 'unknown',
    findings,
    claims,
    evidence,
    timeline,
    timelineAnalysis: scan.timelineAnalysis,
    skillTimelineInsights: scan.skillTimelineInsights,
    extractedText: scan.extractedText ?? '',
    claimViews,
    skills: Array.isArray(scan.skills) ? scan.skills : [],
    actionVerbs: Array.isArray(scan.actionVerbs) ? scan.actionVerbs : [],
    matchedSkills: Array.isArray(scan.matchedSkills) ? scan.matchedSkills : [],
    missingSkills: Array.isArray(scan.missingSkills) ? scan.missingSkills : [],
    weakAreas: Array.isArray(scan.weakAreas) ? scan.weakAreas : [],
    strictness: scan.strictness ?? 'medium',
    crossReferenceSync: typeof scan.crossReferenceSync === 'boolean' ? scan.crossReferenceSync : true,
  };
}

async function extractResumeText(file: File): Promise<{ text: string; warnings: string[] }> {
  // File uploads cross the API boundary first; verification always receives text.
  const formData = new FormData();
  formData.append('file', file);



  const endpoint = API_BASE_URL ? `${API_BASE_URL}/extract-text` : '/extract-text';
  const response = await fetch(endpoint, { method: 'POST',
    body: formData, });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Unable to extract resume text.');
  }

  const data = (await response.json()) as { text?: string; warnings?: string[] };
  if (!data.text) {
    throw new Error('Backend returned no extracted text.');
  }

  return { text: data.text, warnings: data.warnings ?? [] };
}

function getScanSettings() {
  const strictness = (localStorage.getItem('pathai_strictness') ?? 'medium').toLowerCase();
  const crossReferenceSync = localStorage.getItem('pathai_cross_reference_sync');
  return {
    strictness: strictness === 'low' || strictness === 'high' ? strictness : 'medium',
    crossReferenceSync: crossReferenceSync === null ? true : crossReferenceSync === 'true',
  };
}

async function verifyResumeText(text: string, jobDescription: string) {
  // Settings are sent with each scan so reports remain reproducible from payload context.
  const settings = getScanSettings();


  const endpoint = API_BASE_URL ? `${API_BASE_URL}/verify` : '/verify';
  const response = await fetch(endpoint, {     method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      job_description: jobDescription,
      strictness: settings.strictness,
      cross_reference_sync: settings.crossReferenceSync,
    }), });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Unable to analyze resume.');
  }

  const data = await response.json() as Record<string, unknown>;
  return data as {
    risk_score: number;
    confidence: number;
    compatibility_score: number;
    verdict: string;
    findings: Finding[];
    claims: Claim[];
    evidence: EvidenceItem[];
    timeline: TimelineEntry[];
    skills: string[];
    action_verbs: string[];
    matched_skills: string[];
    missing_skills: string[];
    weak_areas: string[];
    strictness: 'low' | 'medium' | 'high';
    cross_reference_sync: boolean;
    // Explainability fields (optional — from new pipeline)
    executive_summary?: string;
    risk_summary?: string;
    confidence_explanation?: string;
    risk_breakdown?: string;
    positive_evidence_summary?: string[];
    confidence_reason?: string;
  };
}

export function VerificationProvider({ children }: { children: React.ReactNode }) {
  const [currentScan, setCurrentScan] = useState<ScanResult | null>(null);
  const [history, setHistory] = useState<ScanResult[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem('pathai_history');
    if (!saved) return;

    try {
      const parsed = JSON.parse(saved) as Partial<ScanResult>[];
      setHistory(Array.isArray(parsed) ? parsed.map(normalizeStoredScan) : []);
    } catch (error) {
      console.error('Failed to load history', error);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('pathai_history', JSON.stringify(history));
  }, [history]);

  const runVerification = async (input: VerificationInput) => {
    // Pasted text wins over files to let users bypass OCR/parser uncertainty.
    const pastedText = input.text?.trim() ?? '';
    let extractedText = '';
    let extractionWarnings: string[] = [];

    if (pastedText) {
      extractedText = pastedText;
    } else if (input.file) {
      const result = await extractResumeText(input.file);
      extractedText = result.text;
      extractionWarnings = result.warnings;
    }

    if (!extractedText.trim()) {
      throw new Error('Resume text is required for analysis.');
    }

    const verified = await verifyResumeText(extractedText, input.jobDescription);
    const claimViews = verified.claims.map(mapClaimToView);

    const v = verified as typeof verified & {
      timeline_analysis?: TimelineAnalysis;
      skill_timeline_insights?: SkillTimelineInsight[];
    };
    const scan: ScanResult = {
      id: `PX-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
      candidateName: input.name.trim() || 'Unknown Candidate',
      jobDescription: input.jobDescription.trim(),
      date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      riskScore: verified.risk_score,
      confidence: verified.confidence,
      compatibilityScore: verified.compatibility_score,
      verdict: verified.verdict,
      findings: verified.findings,
      claims: verified.claims as Claim[],
      evidence: verified.evidence as EvidenceItem[],
      timeline: verified.timeline,
      timelineAnalysis: v.timeline_analysis,
      skillTimelineInsights: v.skill_timeline_insights ?? [],
      extractedText,
      claimViews,
      skills: verified.skills,
      actionVerbs: verified.action_verbs,
      matchedSkills: verified.matched_skills,
      missingSkills: verified.missing_skills,
      weakAreas: verified.weak_areas,
      strictness: verified.strictness,
      crossReferenceSync: verified.cross_reference_sync,
      // Explainability layer — pass through from new pipeline
      executiveSummary: verified.executive_summary,
      riskSummary: verified.risk_summary,
      confidenceExplanation: verified.confidence_explanation,
      riskBreakdown: verified.risk_breakdown,
      positiveEvidenceSummary: verified.positive_evidence_summary,
      confidenceReason: verified.confidence_reason,
      // Operational warnings from extraction
      extractionWarnings: extractionWarnings.length > 0 ? extractionWarnings : undefined,
    };

    setCurrentScan(scan);
    setHistory((prev) => [scan, ...prev]);
  };

  return (
    <VerificationContext.Provider value={{ currentScan, history, runVerification, setCurrentScan }}>
      {children}
    </VerificationContext.Provider>
  );
}

export function useVerification() {
  const context = useContext(VerificationContext);
  if (!context) throw new Error('useVerification must be used within a VerificationProvider');
  return context;
}

export { API_BASE_URL, toRiskLevel, toSentenceCase };
