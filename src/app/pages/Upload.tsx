import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useVerification } from '../context/VerificationContext';
import { Briefcase, FileText, FileUp, Loader2, User, Zap } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';

type ScanPhase = 'uploading' | 'parsing' | 'analyzing' | 'cross-referencing';

const phases: { key: ScanPhase; label: string }[] = [
  { key: 'uploading', label: 'Uploading document' },
  { key: 'parsing', label: 'Parsing resume structure' },
  { key: 'analyzing', label: 'Running AI analysis' },
  { key: 'cross-referencing', label: 'Cross-referencing claims' },
];

export function Upload() {
  const navigate = useNavigate();
  const { runVerification } = useVerification();
  const reduceMotion = useReducedMotion();
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [phaseIndex, setPhaseIndex] = useState(0);

  const [formData, setFormData] = useState({
    name: '',
    jobDescription: '',
    resumeText: ''
  });

  useEffect(() => {
    if (!loading) {
      setPhaseIndex(0);
      return;
    }

    const intervalMs = reduceMotion ? 1400 : 900;
    const interval = window.setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % phases.length);
    }, intervalMs);

    return () => window.clearInterval(interval);
  }, [loading, reduceMotion]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      toast.success(`Attached: ${e.target.files[0].name}`);
    }
  };

  const startScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file && !formData.resumeText.trim()) {
      toast.error('Resume file or pasted text is required');
      return;
    }

    setLoading(true);
    try {
      await runVerification({
        name: formData.name,
        jobDescription: formData.jobDescription,
        file: file,
        text: formData.resumeText
      });
      toast.success('Verification complete');
      navigate('/summary');
    } catch (error) {
      toast.error('Unable to analyze resume right now.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="max-w-5xl mx-auto space-y-6"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={reduceMotion ? {} : { opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className="fade-in-up">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Resume Verification</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a resume and a job description to run OCR, claim extraction, and AI-backed verification.
        </p>
      </div>

      <form onSubmit={startScan} className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="space-y-5 lg:col-span-3">
          <div className="glass-card rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <User className="w-4 h-4 text-muted-foreground" />
              Candidate Profile
            </div>

            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Candidate Full Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. John Doe"
                className="w-full rounded-lg border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-electric-blue/40"
              />
            </div>

            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Job Description</label>
              <textarea
                required
                value={formData.jobDescription}
                onChange={(e) => setFormData({ ...formData, jobDescription: e.target.value })}
                placeholder="Paste full job description here..."
                className="min-h-36 w-full resize-y rounded-lg border border-border bg-secondary/50 px-3 py-3 text-sm text-foreground outline-none transition-colors focus:border-electric-blue/40"
              />
              <p className="text-xs text-muted-foreground">Used to score compatibility, missing skills, evidence quality, and risk.</p>
            </div>
          </div>

          <div className="glass-card rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <FileText className="w-4 h-4 text-muted-foreground" />
              Candidate Resume
            </div>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="relative w-full cursor-pointer overflow-hidden rounded-xl border-2 border-dashed border-border p-8 text-center transition-all hover:border-electric-blue/40 hover:bg-secondary/40"
            >
              {loading && (
                <div className="pointer-events-none absolute inset-0">
                  <div className="scan-line absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-accent to-transparent opacity-80" />
                </div>
              )}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
                accept=".pdf,.doc,.docx"
              />
              <FileUp className="mx-auto mb-2 h-6 w-6 text-muted-foreground" />
              <p className="text-sm text-foreground">{file ? file.name : 'Drop resume here or click to browse'}</p>
              <p className="mt-1 text-xs text-muted-foreground">PDF, DOC, DOCX supported</p>
            </div>
          </div>

          <div className="glass-card rounded-xl p-5 space-y-2">
            <label className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Paste Resume Text</label>
            <textarea
              value={formData.resumeText}
              onChange={(e) => setFormData({ ...formData, resumeText: e.target.value })}
              placeholder="Optional if you upload a file. Paste resume text here to analyze directly."
              className="min-h-44 w-full resize-y rounded-lg border border-border bg-secondary/50 px-3 py-3 text-sm text-foreground outline-none transition-colors focus:border-electric-blue/40"
            />
            <p className="text-xs text-muted-foreground">If both file and text are provided, pasted text is used first.</p>
          </div>
        </div>

        <div className="space-y-5 lg:col-span-2">
          <div className="glass-card rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Briefcase className="w-4 h-4 text-muted-foreground" />
              Scan Progress
            </div>
            <AnimatePresence mode="wait">
              {loading ? (
                <motion.div
                  key={phases[phaseIndex].key}
                  initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                  animate={reduceMotion ? {} : { opacity: 1, y: 0 }}
                  exit={reduceMotion ? {} : { opacity: 0, y: -6 }}
                  className="space-y-3"
                >
                  <p className="text-sm font-medium text-cyan-accent">{phases[phaseIndex].label}</p>
                  <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                    <div className="h-full bg-electric-blue transition-all duration-700" style={{ width: `${((phaseIndex + 1) / phases.length) * 100}%` }} />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {phases.map((phase, idx) => (
                      <div key={phase.key} className="flex items-center gap-2 text-xs">
                        <span className={`h-1.5 w-1.5 rounded-full ${idx <= phaseIndex ? 'bg-cyan-accent pulse-dot' : 'bg-muted'}`} />
                        <span className={idx <= phaseIndex ? 'text-foreground' : 'text-muted-foreground'}>{phase.label}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Ready to run OCR and verification analysis.</p>
                  <p className="text-xs text-muted-foreground">Your current settings are loaded from local preferences.</p>
                </div>
              )}
            </AnimatePresence>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="glow-blue flex w-full items-center justify-center gap-2 rounded-xl bg-electric-blue px-5 py-3 text-sm font-semibold text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing resume...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                Run Verification Scan
              </>
            )}
          </button>
        </div>
      </form>
    </motion.div>
  );
}
