import React, { createContext, useContext, useEffect, useState } from 'react';

// API_BASE_URL: Use env var if set, else dev fallback, else same-origin (relative path)
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    // Remove trailing slash if present
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:8000';
  }
  // Production + no env var? Use relative path (works when backend serves frontend)
  return '';
};
const API_BASE_URL = getApiBaseUrl();

export type Finding = {
  message: string;
  severity: 'high' | 'medium' | 'low';
};

export type Claim = {
  type: string;
  value: string;
  claim?: string;
  evidence?: string[];
  supporting_evidence?: string;
  confidence?: number;
  status?: 'verified' | 'inflated' | 'buzzword' | 'likely';
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
  status: 'verified' | 'inflated' | 'buzzword' | 'likely';
  confidence: number;
  evidence: string[];
  warning?: string;
};

export type ClaimView = {
  name: string;
  category: string;
  claimed: string;
  conf: number;
  status: 'Verified' | 'Inflated' | 'Buzzword' | 'Likely';
  reason: string;
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
  extractedText: string;
  claimViews: ClaimView[];
  skills: string[];
  actionVerbs: string[];
  matchedSkills: string[];
  missingSkills: string[];
  weakAreas: string[];
  strictness: 'low' | 'medium' | 'high';
  crossReferenceSync: boolean;
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

function mapClaimToView(claim: Claim): ClaimView {
  const evidenceCount = claim.evidence_count ?? 0;
  const rawStatus = claim.status;
  const statusMap = {
    verified: 'Verified',
    inflated: 'Inflated',
    buzzword: 'Buzzword',
    likely: 'Likely',
  } as const;

  if (claim.type === 'skill') {
    let status: ClaimView['status'] = rawStatus ? statusMap[rawStatus] : 'Likely';
    if (!rawStatus) {
      if (evidenceCount >= 3) status = 'Verified';
      else if (evidenceCount === 1) status = 'Inflated';
    }

    return {
      name: claim.claim ?? claim.value,
      category: 'Skill Claim',
      claimed: claim.supporting_evidence || (evidenceCount > 0 ? `${evidenceCount} supporting mention${evidenceCount === 1 ? '' : 's'}` : 'Mentioned'),
      conf: claim.confidence ?? Math.max(20, Math.min(95, evidenceCount * 25)),
      status,
      reason:
        claim.supporting_evidence
          ? claim.supporting_evidence
          : evidenceCount > 0
          ? `Detected ${evidenceCount} supporting mention${evidenceCount === 1 ? '' : 's'} in the parsed resume text.`
          : 'Detected as a resume claim.',
    };
  }

  return {
    name: claim.claim ?? claim.value,
    category: toSentenceCase(claim.type),
    claimed: claim.supporting_evidence || 'Claimed',
    conf: claim.confidence ?? 70,
    status: rawStatus ? statusMap[rawStatus] : 'Likely',
    reason: claim.supporting_evidence || `Detected ${claim.type} claim in the analyzed resume text.`,
  };
}

function normalizeStoredScan(scan: Partial<ScanResult>): ScanResult {
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

async function extractResumeText(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);



  const endpoint = API_BASE_URL ? `${API_BASE_URL}/extract-text` : '/extract-text';
  const response = await fetch(endpoint, { method: 'POST',
    body: formData, });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Unable to extract resume text.');
  }

  const data = (await response.json()) as { text?: string };
  if (!data.text) {
    throw new Error('Backend returned no extracted text.');
  }

  return data.text;
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

  return (await response.json()) as {
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
    const pastedText = input.text?.trim() ?? '';
    const extractedText = pastedText || (input.file ? await extractResumeText(input.file) : '');

    if (!extractedText.trim()) {
      throw new Error('Resume text is required for analysis.');
    }

    const verified = await verifyResumeText(extractedText, input.jobDescription);
    const claimViews = verified.claims.map(mapClaimToView);

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
      claims: verified.claims,
      evidence: verified.evidence,
      timeline: verified.timeline,
      extractedText,
      claimViews,
      skills: verified.skills,
      actionVerbs: verified.action_verbs,
      matchedSkills: verified.matched_skills,
      missingSkills: verified.missing_skills,
      weakAreas: verified.weak_areas,
      strictness: verified.strictness,
      crossReferenceSync: verified.cross_reference_sync,
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
