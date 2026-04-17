import React, { createContext, useContext, useEffect, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

export type Finding = {
  message: string;
  severity: 'high' | 'medium' | 'low';
};

export type Claim = {
  type: string;
  value: string;
  evidence_count?: number;
};

export type TimelineEntry = {
  start_year: number;
  end_year: number | 'present';
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
  role: string;
  date: string;
  riskScore: number;
  confidence: number;
  verdict: string;
  findings: Finding[];
  claims: Claim[];
  timeline: TimelineEntry[];
  extractedText: string;
  claimViews: ClaimView[];
};

type VerificationInput = {
  name: string;
  role: string;
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

  if (claim.type === 'skill') {
    let status: ClaimView['status'] = 'Likely';
    if (evidenceCount >= 3) status = 'Verified';
    else if (evidenceCount === 1) status = 'Inflated';

    return {
      name: claim.value,
      category: 'Skill Claim',
      claimed: evidenceCount > 0 ? `${evidenceCount} mention${evidenceCount === 1 ? '' : 's'}` : 'Mentioned',
      conf: Math.max(20, Math.min(95, evidenceCount * 25)),
      status,
      reason:
        evidenceCount > 0
          ? `Detected ${evidenceCount} supporting mention${evidenceCount === 1 ? '' : 's'} in the parsed resume text.`
          : 'Detected as a resume claim.',
    };
  }

  return {
    name: claim.value,
    category: toSentenceCase(claim.type),
    claimed: 'Claimed',
    conf: 70,
    status: 'Likely',
    reason: `Detected ${claim.type} claim in the analyzed resume text.`,
  };
}

function normalizeStoredScan(scan: Partial<ScanResult>): ScanResult {
  const claims = Array.isArray(scan.claims) ? scan.claims : [];
  const findings = Array.isArray(scan.findings) ? scan.findings : [];
  const timeline = Array.isArray(scan.timeline) ? scan.timeline : [];
  const claimViews = Array.isArray(scan.claimViews) && scan.claimViews.length > 0 ? scan.claimViews : claims.map(mapClaimToView);

  return {
    id: scan.id ?? `PX-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
    candidateName: scan.candidateName ?? 'Unknown Candidate',
    role: scan.role ?? 'Unspecified Role',
    date: scan.date ?? new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    riskScore: typeof scan.riskScore === 'number' ? scan.riskScore : 0,
    confidence: typeof scan.confidence === 'number' ? scan.confidence : 0,
    verdict: scan.verdict ?? 'unknown',
    findings,
    claims,
    timeline,
    extractedText: scan.extractedText ?? '',
    claimViews,
  };
}

async function extractResumeText(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/extract-text`, {
    method: 'POST',
    body: formData,
  });

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

async function verifyResumeText(text: string) {
  const response = await fetch(`${API_BASE_URL}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Unable to analyze resume.');
  }

  return (await response.json()) as {
    risk_score: number;
    confidence: number;
    verdict: string;
    findings: Finding[];
    claims: Claim[];
    timeline: TimelineEntry[];
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

    const verified = await verifyResumeText(extractedText);
    const claimViews = verified.claims.map(mapClaimToView);

    const scan: ScanResult = {
      id: `PX-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
      candidateName: input.name.trim() || 'Unknown Candidate',
      role: input.role.trim() || 'Unspecified Role',
      date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      riskScore: verified.risk_score,
      confidence: verified.confidence,
      verdict: verified.verdict,
      findings: verified.findings,
      claims: verified.claims,
      timeline: verified.timeline,
      extractedText,
      claimViews,
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
