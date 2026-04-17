import React from 'react';
import { Link } from 'react-router';
import { AlertCircle } from 'lucide-react';
import { toRiskLevel, toSentenceCase, useVerification } from '../context/VerificationContext';

export function Summary() {
  const { currentScan } = useVerification();

  if (!currentScan) {
    return (
      <div className="h-64 flex flex-col items-center justify-center border border-slate-900 rounded bg-slate-900/10">
        <p className="text-slate-500 text-sm mb-4">No active scan results found.</p>
        <Link to="/" className="text-xs font-bold text-indigo-500 hover:underline">Run your first scan</Link>
      </div>
    );
  }

  const riskLevel = toRiskLevel(currentScan.riskScore);

  return (
    <div className="space-y-10">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-xl font-bold text-white">{currentScan.candidateName}</h1>
          <p className="text-sm text-slate-500">{currentScan.role} • {currentScan.id}</p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase font-bold text-slate-500">Confidence Score</p>
          <p className={`text-3xl font-black ${currentScan.confidence > 70 ? 'text-white' : 'text-amber-500'}`}>
            {currentScan.confidence}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 border border-slate-900 bg-slate-900/20 p-6 rounded">
          <h2 className="text-xs uppercase font-bold text-slate-500 mb-4">Verdict</h2>
          <p className="text-lg text-white font-medium mb-2">{toSentenceCase(currentScan.verdict)}</p>
          <p className="text-sm text-slate-400 leading-relaxed">
            Backend analysis completed for {currentScan.candidateName}. The result currently shows a {riskLevel.toLowerCase()} risk profile with {currentScan.findings.length} finding{currentScan.findings.length === 1 ? '' : 's'} and {currentScan.claims.length} extracted claim{currentScan.claims.length === 1 ? '' : 's'}.
          </p>
        </div>

        <div className="border border-slate-900 bg-slate-900/20 p-6 rounded space-y-4">
          <h2 className="text-xs uppercase font-bold text-slate-500">Key Indicators</h2>
          <div className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Risk Level</span>
              <span className={`font-bold ${
                riskLevel === 'High' ? 'text-rose-500' :
                riskLevel === 'Moderate' ? 'text-amber-500' : 'text-emerald-500'
              }`}>{riskLevel}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Risk Score</span>
              <span className="text-slate-300">{currentScan.riskScore}/100</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Scan Date</span>
              <span className="text-slate-300">{currentScan.date}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Timeline Entries</span>
              <span className="text-slate-300">{currentScan.timeline.length}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-slate-500" />
          <h2 className="text-xs uppercase font-bold text-slate-500">Findings</h2>
        </div>
        <div className="space-y-2">
          {currentScan.findings.map((finding, i) => (
            <div key={i} className={`p-4 border rounded ${
              finding.severity === 'high' ? 'border-rose-900/20 bg-rose-950/5' :
              finding.severity === 'medium' ? 'border-amber-900/20 bg-amber-950/5' :
              'border-slate-800 bg-slate-900/20'
            }`}>
              <div className="flex justify-between items-start">
                <div>
                  <p className={`text-sm font-medium ${
                    finding.severity === 'high' ? 'text-rose-200' :
                    finding.severity === 'medium' ? 'text-amber-200' : 'text-slate-200'
                  }`}>{finding.message}</p>
                  <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest">Verification Finding</p>
                </div>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                   finding.severity === 'high' ? 'border-rose-800 text-rose-500' :
                   finding.severity === 'medium' ? 'border-amber-800 text-amber-500' :
                   'border-slate-800 text-slate-500'
                }`}>
                  {finding.severity}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
