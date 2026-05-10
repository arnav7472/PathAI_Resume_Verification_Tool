import React from 'react';
import { Link } from 'react-router';
import { AlertCircle } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { toRiskLevel, toSentenceCase, useVerification } from '../context/VerificationContext';

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
        <div className="text-right">
          <p className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">Confidence Score</p>
          <p className={`text-3xl font-black ${currentScan.confidence > 70 ? 'text-electric-blue' : 'text-amber-400'}`}>
            {currentScan.confidence}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card md:col-span-2 rounded-xl border border-border p-6">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground mb-4">Verdict</h2>
          <p className="text-lg text-foreground font-medium mb-2">{toSentenceCase(currentScan.verdict)}</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
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
