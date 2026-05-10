"use client"

import { useState, useRef, useCallback } from "react"
import { Shell } from "@/components/shell"
import {
  Upload,
  FileText,
  Briefcase,
  Zap,
  ChevronRight,
  X,
  CheckCircle2,
  SlidersHorizontal,
} from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

type ScanPhase =
  | "idle"
  | "uploading"
  | "parsing"
  | "analyzing"
  | "cross-referencing"
  | "done"

const phases: ScanPhase[] = ["uploading", "parsing", "analyzing", "cross-referencing", "done"]

const phaseLabels: Record<ScanPhase, string> = {
  idle: "",
  uploading: "Uploading document...",
  parsing: "Parsing resume structure...",
  analyzing: "Running AI analysis...",
  "cross-referencing": "Cross-referencing claims...",
  done: "Verification complete",
}

export default function UploadPage() {
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [jobDesc, setJobDesc] = useState("")
  const [strictness, setStrictness] = useState<"lenient" | "standard" | "strict">("standard")
  const [crossRef, setCrossRef] = useState(true)
  const [phase, setPhase] = useState<ScanPhase>("idle")
  const [phaseIndex, setPhaseIndex] = useState(0)
  const [progress, setProgress] = useState(0)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }, [])

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) setFile(f)
  }

  const runScan = () => {
    if (!file) return
    setPhase("uploading")
    setPhaseIndex(0)
    setProgress(0)

    let idx = 0
    const advance = () => {
      idx++
      if (idx < phases.length) {
        setPhase(phases[idx])
        setPhaseIndex(idx)
        setProgress(Math.round((idx / (phases.length - 1)) * 100))
        setTimeout(advance, 900 + Math.random() * 600)
      }
    }
    setTimeout(advance, 900)
  }

  const isScanning = phase !== "idle" && phase !== "done"
  const isDone = phase === "done"

  return (
    <Shell>
      <div className="px-8 py-8 max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8 fade-in-up">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
            <span>Workspace</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-foreground">New Verification</span>
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Resume Verification</h1>
          <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
            Upload a resume and optionally provide a job description to begin AI-powered claim verification.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Drop zone */}
          <div className="lg:col-span-3 space-y-5">
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => !file && fileRef.current?.click()}
              className={cn(
                "relative rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer overflow-hidden",
                file
                  ? "border-border cursor-default"
                  : dragging
                  ? "border-electric-blue bg-electric-blue/5 scale-[1.01]"
                  : "border-border hover:border-primary/40 hover:bg-secondary/40"
              )}
            >
              <input ref={fileRef} type="file" className="hidden" accept=".pdf,.doc,.docx,.txt" onChange={handleFile} />

              {/* Scan overlay */}
              {isScanning && (
                <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden">
                  <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-accent to-transparent opacity-70 scan-line" />
                  <div className="absolute inset-0 bg-background/60" />
                </div>
              )}

              {!file ? (
                <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
                  <div className="w-14 h-14 rounded-xl bg-secondary border border-border flex items-center justify-center mb-5">
                    <Upload className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <p className="text-sm font-medium text-foreground mb-1">
                    Drop resume here or <span className="text-electric-blue">browse</span>
                  </p>
                  <p className="text-xs text-muted-foreground">PDF, DOC, DOCX, TXT — max 10 MB</p>
                </div>
              ) : (
                <div className="p-5">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg bg-secondary border border-border flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5 text-electric-blue" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {(file.size / 1024).toFixed(1)} KB · {file.type || "document"}
                      </p>

                      {/* Progress */}
                      {(isScanning || isDone) && (
                        <div className="mt-3 space-y-2">
                          <div className="h-1 rounded-full bg-secondary overflow-hidden">
                            <div
                              className="h-full rounded-full bg-electric-blue transition-all duration-700 ease-out"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {isDone
                              ? "✓ Analysis complete"
                              : phaseLabels[phase]}
                          </p>
                        </div>
                      )}

                      {/* Phase steps */}
                      {(isScanning || isDone) && (
                        <div className="mt-3 grid grid-cols-2 gap-1.5">
                          {phases.slice(0, -1).map((p, i) => (
                            <div key={p} className="flex items-center gap-1.5">
                              <div className={cn(
                                "w-1.5 h-1.5 rounded-full transition-colors",
                                i < phaseIndex ? "bg-cyan-accent" : i === phaseIndex ? "bg-electric-blue pulse-dot" : "bg-muted"
                              )} />
                              <span className={cn(
                                "text-[10px] capitalize",
                                i <= phaseIndex ? "text-foreground" : "text-muted-foreground"
                              )}>{p}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    {!isScanning && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); setPhase("idle") }}
                        className="shrink-0 p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Job description */}
            <div className="glass-card rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Job Description</span>
                <span className="ml-auto text-[10px] text-muted-foreground bg-secondary px-2 py-0.5 rounded">Optional</span>
              </div>
              <textarea
                value={jobDesc}
                onChange={(e) => setJobDesc(e.target.value)}
                placeholder="Paste the job description here to enable role-specific claim matching and skill gap analysis..."
                rows={6}
                className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none leading-relaxed"
              />
              <div className="flex items-center justify-between pt-1 border-t border-border">
                <span className="text-xs text-muted-foreground">{jobDesc.length} characters</span>
                {jobDesc && (
                  <button onClick={() => setJobDesc("")} className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                    Clear
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Config panel */}
          <div className="lg:col-span-2 space-y-5">
            <div className="glass-card rounded-xl p-5 space-y-5">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Scan Configuration</span>
              </div>

              {/* Strictness */}
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Strictness Level</p>
                <div className="space-y-1.5">
                  {(["lenient", "standard", "strict"] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setStrictness(s)}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 border",
                        strictness === s
                          ? "bg-secondary border-electric-blue/40 text-foreground"
                          : "border-transparent text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                      )}
                    >
                      <div className={cn(
                        "w-2 h-2 rounded-full shrink-0",
                        s === "lenient" ? "bg-chart-4" : s === "standard" ? "bg-electric-blue" : "bg-destructive"
                      )} />
                      <span className="capitalize font-medium">{s}</span>
                      <span className="ml-auto text-[10px] text-muted-foreground">
                        {s === "lenient" ? "Broad match" : s === "standard" ? "Balanced" : "Exact match"}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Cross-reference toggle */}
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Options</p>
                <div className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-secondary/60">
                  <div>
                    <p className="text-sm font-medium text-foreground">Cross-reference Sync</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">Validate claims against external sources</p>
                  </div>
                  <button
                    onClick={() => setCrossRef(!crossRef)}
                    className={cn(
                      "relative w-9 h-5 rounded-full transition-colors duration-200 shrink-0",
                      crossRef ? "bg-electric-blue" : "bg-secondary border border-border"
                    )}
                  >
                    <span className={cn(
                      "absolute top-0.5 w-4 h-4 rounded-full bg-foreground shadow transition-all duration-200",
                      crossRef ? "left-4" : "left-0.5"
                    )} />
                  </button>
                </div>
              </div>

              {/* Summary */}
              <div className="rounded-lg bg-secondary/40 border border-border p-3 space-y-1.5">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Scan Summary</p>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Mode</span>
                    <span className="text-foreground capitalize">{strictness}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cross-reference</span>
                    <span className={crossRef ? "text-cyan-accent" : "text-muted-foreground"}>{crossRef ? "Enabled" : "Disabled"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Job matching</span>
                    <span className={jobDesc ? "text-cyan-accent" : "text-muted-foreground"}>{jobDesc ? "Active" : "None"}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action */}
            {isDone ? (
              <Link
                href="/dashboard"
                className="flex items-center justify-center gap-2 w-full py-3 px-5 rounded-xl bg-electric-blue text-background font-semibold text-sm transition-all duration-200 hover:opacity-90 glow-blue"
              >
                <CheckCircle2 className="w-4 h-4" />
                View Results
                <ChevronRight className="w-4 h-4" />
              </Link>
            ) : (
              <button
                onClick={runScan}
                disabled={!file || isScanning}
                className={cn(
                  "flex items-center justify-center gap-2 w-full py-3 px-5 rounded-xl font-semibold text-sm transition-all duration-200",
                  !file || isScanning
                    ? "bg-secondary text-muted-foreground cursor-not-allowed"
                    : "bg-electric-blue text-background hover:opacity-90 glow-blue"
                )}
              >
                {isScanning ? (
                  <>
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-background/40 border-t-background animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Run AI Scan
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </Shell>
  )
}
