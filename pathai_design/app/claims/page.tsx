"use client"

import { useState } from "react"
import { Shell } from "@/components/shell"
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Search,
  Filter,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react"
import { cn } from "@/lib/utils"

type ClaimStatus = "verified" | "unverified" | "flagged"
type ClaimCategory = "experience" | "education" | "skills" | "certifications" | "projects"

interface Claim {
  id: string
  text: string
  category: ClaimCategory
  status: ClaimStatus
  confidence: number
  evidence?: string
  risk?: string
}

const claims: Claim[] = [
  { id: "1", text: "Senior Software Engineer at Acme Corp (2020–2023)", category: "experience", status: "verified", confidence: 94, evidence: "LinkedIn profile cross-referenced. 3 mutual connections confirmed role." },
  { id: "2", text: "Led team of 8 engineers across 3 product lines", category: "experience", status: "unverified", confidence: 48, risk: "No public evidence found. Claim is plausible but unconfirmed." },
  { id: "3", text: "AWS Certified Solutions Architect (2022)", category: "certifications", status: "flagged", confidence: 28, risk: "AWS credential portal returned no matching record. Possible expiration or inaccurate ID." },
  { id: "4", text: "Reduced system latency by 40% via caching layer", category: "experience", status: "unverified", confidence: 52, risk: "Quantified claims are hard to verify without internal data." },
  { id: "5", text: "B.S. Computer Science, MIT (2018)", category: "education", status: "verified", confidence: 98, evidence: "MIT alumni directory confirmed. GPA and graduation year match." },
  { id: "6", text: "Published 2 papers on distributed systems", category: "projects", status: "unverified", confidence: 35, risk: "No indexed publications found under this name." },
  { id: "7", text: "React, TypeScript, Node.js — 5+ years", category: "skills", status: "verified", confidence: 88, evidence: "GitHub activity shows 4.2 years of consistent React/TS usage." },
  { id: "8", text: "Docker & Kubernetes — production experience", category: "skills", status: "unverified", confidence: 60, risk: "Limited public evidence. Mentioned in 2 repos." },
  { id: "9", text: "Software Engineer at StartupXYZ (2017–2020)", category: "experience", status: "verified", confidence: 91, evidence: "Company verified via LinkedIn. StartupXYZ is a registered entity." },
  { id: "10", text: "Managed $2M engineering budget", category: "experience", status: "flagged", confidence: 18, risk: "No evidence found. Role level inconsistent with budget claim." },
  { id: "11", text: "Google Cloud Professional Data Engineer (2023)", category: "certifications", status: "verified", confidence: 82, evidence: "GCP credential verified via public badge link provided." },
  { id: "12", text: "Open source contributor — 1200+ GitHub stars", category: "projects", status: "verified", confidence: 76, evidence: "GitHub profile matches. Repositories total 1,340 stars." },
]

const statusConfig = {
  verified: { label: "Verified", icon: CheckCircle2, color: "text-chart-4", bg: "bg-chart-4/10", border: "border-chart-4/20" },
  unverified: { label: "Unverified", icon: AlertCircle, color: "text-muted-foreground", bg: "bg-secondary", border: "border-border" },
  flagged: { label: "Flagged", icon: XCircle, color: "text-destructive", bg: "bg-destructive/10", border: "border-destructive/20" },
}

const categories: ClaimCategory[] = ["experience", "education", "skills", "certifications", "projects"]

export default function ClaimsPage() {
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState<ClaimStatus | "all">("all")
  const [filterCategory, setFilterCategory] = useState<ClaimCategory | "all">("all")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [sort, setSort] = useState<"confidence-asc" | "confidence-desc">("confidence-desc")

  const filtered = claims
    .filter((c) => {
      if (filterStatus !== "all" && c.status !== filterStatus) return false
      if (filterCategory !== "all" && c.category !== filterCategory) return false
      if (search && !c.text.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
    .sort((a, b) =>
      sort === "confidence-desc" ? b.confidence - a.confidence : a.confidence - b.confidence
    )

  const counts = {
    verified: claims.filter((c) => c.status === "verified").length,
    unverified: claims.filter((c) => c.status === "unverified").length,
    flagged: claims.filter((c) => c.status === "flagged").length,
  }

  return (
    <Shell>
      <div className="px-8 py-8 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="fade-in-up">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
            <span>Workspace</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-foreground">Claims Analysis</span>
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Claims Analysis</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {claims.length} claims extracted · {counts.verified} verified · {counts.flagged} flagged
          </p>
        </div>

        {/* Status summary */}
        <div className="grid grid-cols-3 gap-3">
          {(["verified", "unverified", "flagged"] as ClaimStatus[]).map((s) => {
            const cfg = statusConfig[s]
            const Icon = cfg.icon
            return (
              <button
                key={s}
                onClick={() => setFilterStatus(filterStatus === s ? "all" : s)}
                className={cn(
                  "glass-card rounded-xl p-4 text-left border transition-all duration-150",
                  filterStatus === s ? cfg.border : "border-border hover:border-border/80"
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={cn("w-4 h-4", cfg.color)} />
                  <span className="text-xs font-medium capitalize text-muted-foreground">{s}</span>
                </div>
                <p className={cn("text-2xl font-bold", cfg.color)}>{counts[s]}</p>
              </button>
            )
          })}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search claims..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary/40 transition-colors"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-muted-foreground" />
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(filterCategory === cat ? "all" : cat)}
                className={cn(
                  "px-2.5 py-1 rounded-md text-xs font-medium transition-colors capitalize",
                  filterCategory === cat
                    ? "bg-secondary text-foreground border border-border"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                )}
              >
                {cat}
              </button>
            ))}
          </div>
          <button
            onClick={() => setSort(sort === "confidence-desc" ? "confidence-asc" : "confidence-desc")}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-secondary border border-border text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {sort === "confidence-desc" ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            Confidence
          </button>
        </div>

        {/* Claims table */}
        <div className="glass-card rounded-xl overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 px-5 py-3 border-b border-border text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            <span>Claim</span>
            <span>Category</span>
            <span>Confidence</span>
            <span>Status</span>
          </div>
          <div className="divide-y divide-border">
            {filtered.map((claim) => {
              const cfg = statusConfig[claim.status]
              const Icon = cfg.icon
              const isOpen = expanded === claim.id
              return (
                <div key={claim.id}>
                  <button
                    onClick={() => setExpanded(isOpen ? null : claim.id)}
                    className="w-full grid grid-cols-[1fr_auto_auto_auto] gap-4 items-center px-5 py-3.5 text-left hover:bg-secondary/40 transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={cn(
                        "transition-transform duration-150",
                        isOpen ? "rotate-90" : "rotate-0"
                      )}>
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      </span>
                      <span className="text-sm text-foreground truncate">{claim.text}</span>
                    </div>
                    <span className="text-xs capitalize text-muted-foreground bg-secondary px-2 py-0.5 rounded whitespace-nowrap">
                      {claim.category}
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 rounded-full bg-input overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            claim.confidence >= 80 ? "bg-electric-blue" :
                            claim.confidence >= 50 ? "bg-chart-4" : "bg-destructive"
                          )}
                          style={{ width: `${claim.confidence}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">{claim.confidence}%</span>
                    </div>
                    <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-md", cfg.bg)}>
                      <Icon className={cn("w-3 h-3 shrink-0", cfg.color)} />
                      <span className={cn("text-[10px] font-medium whitespace-nowrap", cfg.color)}>{cfg.label}</span>
                    </div>
                  </button>

                  {/* Expandable evidence */}
                  {isOpen && (
                    <div className="px-5 pb-4 bg-secondary/20 border-t border-border/50">
                      <div className="flex items-start gap-2.5 pt-3">
                        <Info className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
                            {claim.evidence ? "Evidence" : "Risk Note"}
                          </p>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {claim.evidence || claim.risk}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          {filtered.length === 0 && (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No claims match your filters.
            </div>
          )}
        </div>
      </div>
    </Shell>
  )
}
