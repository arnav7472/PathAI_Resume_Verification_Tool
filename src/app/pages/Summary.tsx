import React, { useCallback, useState } from 'react';
import { Link } from 'react-router';
import { AlertCircle, CheckCircle2, TrendingUp, TrendingDown, HelpCircle, Download, Loader2, FileText } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { toRiskLevel, toSentenceCase, useVerification, API_BASE_URL } from '../context/VerificationContext';

function ConfidenceIcon({ conf }: { conf: number }) {
  if (conf >= 70) return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
  if (conf >= 40) return <HelpCircle className="w-4 h-4 text-amber-400" />;
  return <TrendingDown className="w-4 h-4 text-rose-400" />;
}

function RiskIcon({ risk }: { risk: number }) {
  if (risk < 30) return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
  if (risk < 60) return <TrendingUp className="w-4 h-4 text-amber-400" />;
  return <AlertCircle className="w-4 h-4 text-rose-400" />;
}

function DownloadPdfButton({ scan }: { scan: NonNullable<ReturnType<typeof useVerification>['currentScan']> }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = API_BASE_URL ? `${API_BASE_URL}/report/pdf` : '/report/pdf';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: scan.extractedText,
          job_description: scan.jobDescription,
          strictness: scan.strictness,
          cross_reference_sync: scan.crossReferenceSync,
        }),
      });
      if (!res.ok) {
        const err = await res.text().catch(() => 'Unknown error');
        throw new Error(err || 'Failed to generate PDF report');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'verification_report.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setLoading(false);
    }
  }, [scan]);

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={handleDownload}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-lg border border-electric-blue/40 text-electric-blue hover:bg-electric-blue/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Download className="w-3.5 h-3.5" />
        )}
        {loading ? 'Generating...' : 'Download PDF'}
      </button>
      {error && (
        <span className="text-[10px] text-rose-400">{error}</span>
      )}
    </div>
  );
}

export function Summary() {
  const { currentScan } = useVerification();
  const reduceMotion = useReducedMotion();

  if (!currentScan) {
    return (
      <div className="glass-card h-64 rounded-xl border border-border flex flex-col items-center justify-center">
        <p className="text-muted-foreground text-sm mb-4">No active scan results found.</p>
        <Link to="/" className="text-xs font-semibold text-electric-blue hover:underline">Run your first scan</Link>
      </div>
    );
  }

  const riskLevel = toRiskLevel(currentScan.riskScore);

  return (
    <motion.div
      className="space-y-8"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={reduceMotion ? {} : { opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{currentScan.candidateName}</h1>
          <p className="text-sm text-muted-foreground">JD match scan - {currentScan.id}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="text-right">
            <p className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">Confidence Score</p>
            <p className={`text-3xl font-black ${currentScan.confidence > 70 ? 'text-electric-blue' : 'text-amber-400'}`}>
              {currentScan.confidence}%
            </p>
          </div>
          <DownloadPdfButton scan={currentScan} />
        </div>
      </div>

      {/* Executive summary */}
      {currentScan.executiveSummary && (
        <div className="glass-card rounded-xl border border-border p-5">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-electric-blue" />
            <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Executive Summary</h2>
          </div>
          <p className="text-sm text-foreground leading-relaxed">{currentScan.executiveSummary}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card md:col-span-2 rounded-xl border border-border p-6">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground mb-4">Verdict</h2>
          <p className="text-lg text-foreground font-medium mb-2">{toSentenceCase(currentScan.verdict)}</p>

          {/* Risk summary */}
          {currentScan.riskSummary && (
            <div className="flex items-start gap-2 mt-3 p-3 rounded-lg bg-secondary/30">
              <RiskIcon risk={currentScan.riskScore} />
              <p className="text-sm text-foreground">{currentScan.riskSummary}</p>
            </div>
          )}

          {/* Confidence explanation */}
          {currentScan.confidenceExplanation && (
            <div className="flex items-start gap-2 mt-2 p-3 rounded-lg bg-secondary/30">
              <ConfidenceIcon conf={currentScan.confidence} />
              <p className="text-sm text-foreground">{currentScan.confidenceExplanation}</p>
            </div>
          )}

          {/* Risk breakdown */}
          {currentScan.riskBreakdown && (
            <div className="mt-3 p-3 rounded-lg bg-amber-950/10 border border-amber-900/20">
              <p className="text-xs text-amber-200/80 leading-relaxed">{currentScan.riskBreakdown}</p>
            </div>
          )}

          <p className="text-sm text-muted-foreground leading-relaxed mt-3">
            Backend analysis completed for {currentScan.candidateName}. The resume has a {currentScan.compatibilityScore}% compatibility score against the job description, a {riskLevel.toLowerCase()} risk profile, {currentScan.findings.length} finding{currentScan.findings.length === 1 ? '' : 's'}, and {currentScan.claims.length} extracted claim{currentScan.claims.length === 1 ? '' : 's'}.
          </p>
        </div>

        <div className="glass-card rounded-xl border border-border p-6 space-y-4">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Key Indicators</h2>
          <div className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Compatibility</span>
              <span className="text-foreground">{currentScan.compatibilityScore}/100</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Risk Level</span>
              <span className={`font-bold ${
                riskLevel === 'High' ? 'text-rose-500' :
                riskLevel === 'Moderate' ? 'text-amber-500' : 'text-emerald-500'
              }`}>{riskLevel}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Risk Score</span>
              <span className="text-foreground">{currentScan.riskScore}/100</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Strictness</span>
              <span className="text-foreground uppercase">{currentScan.strictness}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Scan Date</span>
              <span className="text-foreground">{currentScan.date}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Timeline Entries</span>
              <span className="text-foreground">{currentScan.timeline.length}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card rounded-xl border border-border p-4">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground mb-3">Matched Skills</h2>
          <p className="text-sm text-emerald-300">{currentScan.matchedSkills.length ? currentScan.matchedSkills.join(', ') : 'No JD skill matches detected.'}</p>
        </div>
        <div className="glass-card rounded-xl border border-border p-4">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground mb-3">Missing Skills</h2>
          <p className="text-sm text-amber-300">{currentScan.missingSkills.length ? currentScan.missingSkills.join(', ') : 'No missing JD skills detected.'}</p>
        </div>
        <div className="glass-card rounded-xl border border-border p-4">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground mb-3">Action Verbs</h2>
          <p className="text-sm text-sky-300">{currentScan.actionVerbs.length ? currentScan.actionVerbs.join(', ') : 'No strong action verbs detected.'}</p>
        </div>
      </div>

      {/* Positive evidence summary */}
      {currentScan.positiveEvidenceSummary && currentScan.positiveEvidenceSummary.length > 0 && (
        <div className="glass-card rounded-xl border border-border p-5">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Positive Evidence</h2>
          </div>
          <div className="space-y-2">
            {currentScan.positiveEvidenceSummary.map((note, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-foreground">
                <span className="text-emerald-400 mt-0.5">•</span>
                <span>{note}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Extraction quality warnings — operational caveats from OCR/parsing */}
      {currentScan.extractionWarnings && currentScan.extractionWarnings.length > 0 && (
        <div className="glass-card rounded-xl border border-amber-900/20 p-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <h2 className="text-xs uppercase font-bold tracking-widest text-amber-300">Extraction Notice</h2>
          </div>
          <ul className="space-y-1">
            {currentScan.extractionWarnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-200/90">
                <span className="text-amber-400 mt-0.5">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-muted-foreground mt-2">
            Low-quality scan may reduce verification accuracy. Several claims may require manual review due to weak supporting evidence.
          </p>
        </div>
      )}

      {/* Confidence reason */}
      {currentScan.confidenceReason && (
        <div className="glass-card rounded-xl border border-border p-5">
          <div className="flex items-center gap-2 mb-2">
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Confidence Details</h2>
          </div>
          <p className="text-sm text-muted-foreground">{currentScan.confidenceReason}</p>
        </div>
      )}

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Findings</h2>
        </div>
        <div className="space-y-2">
          {currentScan.findings.map((finding, i) => (
            <div key={i} className={`p-4 border rounded-xl ${
              finding.severity === 'high' ? 'border-rose-900/20 bg-rose-950/5' :
              finding.severity === 'medium' ? 'border-amber-900/20 bg-amber-950/5' :
              'border-border bg-secondary/40'
            } glass`}>
              <div className="flex justify-between items-start gap-4">
                <div>
                  <p className={`text-sm font-medium ${
                    finding.severity === 'high' ? 'text-rose-200' :
                    finding.severity === 'medium' ? 'text-amber-200' : 'text-foreground'
                  }`}>{finding.message}</p>
                  <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-widest">Verification Finding</p>
                </div>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                   finding.severity === 'high' ? 'border-rose-800 text-rose-500' :
                   finding.severity === 'medium' ? 'border-amber-800 text-amber-500' :
                   'border-border text-muted-foreground'
                }`}>
                  {finding.severity}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
