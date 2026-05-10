"use client"

import { useState } from "react"
import { Shell } from "@/components/shell"
import {
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
  Globe,
  Linkedin,
  Github,
  FileText,
  Database,
  Link2,
  Shield,
  ZoomIn,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface EvidenceItem {
  id: string
  source: string
  sourceIcon: React.ElementType
  sourceType: string
  status: "confirmed" | "partial" | "failed"
  description: string
  timestamp: string
  url?: string
  confidence: number
  details?: string[]
}

interface EvidenceGroup {
  claim: string
  category: string
  overallStatus: "verified" | "unverified" | "flagged"
  overallConfidence: number
  evidenceItems: EvidenceItem[]
}

const evidenceGroups: EvidenceGroup[] = [
  {
    claim: "Senior Software Engineer at Acme Corp (2020–2023)",
    category: "Experience",
    overallStatus: "verified",
    overallConfidence: 94,
    evidenceItems: [
      {
        id: "e1",
        source: "LinkedIn",
        sourceIcon: Linkedin,
        sourceType: "Professional Network",
        status: "confirmed",
        description: "LinkedIn profile lists position with matching title, dates, and company.",
        timestamp: "2 min ago",
        url: "#",
        confidence: 96,
        details: ["Position title: Senior Software Engineer", "Dates: Jan 2020 – Dec 2023", "Company: Acme Corp (verified entity)", "3 mutual connections confirmed"],
      },
      {
        id: "e2",
        source: "GitHub",
        sourceIcon: Github,
        sourceType: "Code Repository",
        status: "confirmed",
        description: "GitHub commit history shows active contributions to Acme Corp repos from 2020–2023.",
        timestamp: "2 min ago",
        url: "#",
        confidence: 91,
        details: ["847 commits to acme-corp org", "Consistent activity 2020–2023", "Merged 124 pull requests"],
      },
    ],
  },
  {
    claim: "AWS Certified Solutions Architect (2022)",
    category: "Certification",
    overallStatus: "flagged",
    overallConfidence: 28,
    evidenceItems: [
      {
        id: "e3",
        source: "AWS Credential Portal",
        sourceIcon: Database,
        sourceType: "Official Registry",
        status: "failed",
        description: "AWS certification verification returned no matching record for provided credential ID.",
        timestamp: "3 min ago",
        confidence: 15,
        details: ["Credential ID: AWS-SA-2022-XXXXXX — not found", "Name match: 0 results", "Possible causes: expired, incorrect ID, or fabricated"],
      },
      {
        id: "e4",
        source: "Credly Badge",
        sourceIcon: Globe,
        sourceType: "Badge Platform",
        status: "failed",
        description: "No Credly badge found linked to this candidate for AWS certifications.",
        timestamp: "3 min ago",
        confidence: 20,
        details: ["Email: no linked badges", "Username search: no match", "Public badge URL: 404"],
      },
    ],
  },
  {
    claim: "B.S. Computer Science, MIT (2018)",
    category: "Education",
    overallStatus: "verified",
    overallConfidence: 98,
    evidenceItems: [
      {
        id: "e5",
        source: "MIT Alumni Directory",
        sourceIcon: Database,
        sourceType: "University Registry",
        status: "confirmed",
        description: "MIT alumni directory confirms graduation year, degree, and department.",
        timestamp: "1 min ago",
        url: "#",
        confidence: 99,
        details: ["Degree: Bachelor of Science", "Major: Computer Science (Course 6-3)", "Year: 2018", "Status: Verified graduate"],
      },
    ],
  },
  {
    claim: "React, TypeScript, Node.js — 5+ years",
    category: "Skills",
    overallStatus: "verified",
    overallConfidence: 88,
    evidenceItems: [
      {
        id: "e6",
        source: "GitHub",
        sourceIcon: Github,
        sourceType: "Code Repository",
        status: "confirmed",
        description: "GitHub activity analysis confirms consistent usage of React, TypeScript, and Node.js.",
        timestamp: "2 min ago",
        url: "#",
        confidence: 92,
        details: ["React: 4.2 years of activity", "TypeScript: 3.8 years", "Node.js: 5.1 years", "1,340 total GitHub stars"],
      },
      {
        id: "e7",
        source: "Stack Overflow",
        sourceIcon: Globe,
        sourceType: "Developer Community",
        status: "partial",
        description: "Stack Overflow profile shows relevant activity but limited React-specific contributions.",
        timestamp: "2 min ago",
        url: "#",
        confidence: 72,
        details: ["Reputation: 4,210", "Top tags: javascript, node.js, typescript", "React answers: 12 (low activity)"],
      },
    ],
  },
  {
    claim: "Published 2 papers on distributed systems",
    category: "Projects",
    overallStatus: "unverified",
    overallConfidence: 35,
    evidenceItems: [
      {
        id: "e8",
        source: "Google Scholar",
        sourceIcon: FileText,
        sourceType: "Academic Database",
        status: "failed",
        description: "No publications indexed under this name in academic databases.",
        timestamp: "4 min ago",
        confidence: 20,
        details: ["Google Scholar: 0 results", "arXiv: 0 results", "IEEE Xplore: 0 results", "Semantic Scholar: 0 results"],
      },
    ],
  },
]

const statusConfig = {
  verified: { icon: CheckCircle2, color: "text-chart-4", bg: "bg-chart-4/10", label: "Verified" },
  unverified: { icon: AlertCircle, color: "text-muted-foreground", bg: "bg-secondary", label: "Unverified" },
  flagged: { icon: XCircle, color: "text-destructive", bg: "bg-destructive/10", label: "Flagged" },
}

const evidenceStatusConfig = {
  confirmed: { icon: CheckCircle2, color: "text-chart-4", label: "Confirmed" },
  partial: { icon: AlertCircle, color: "text-yellow-400", label: "Partial" },
  failed: { icon: XCircle, color: "text-destructive", label: "Failed" },
}

export default function EvidencePage() {
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set(["Senior Software Engineer at Acme Corp (2020–2023)"]))
  const [openItems, setOpenItems] = useState<Set<string>>(new Set())

  const toggleGroup = (claim: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev)
      next.has(claim) ? next.delete(claim) : next.add(claim)
      return next
    })
  }

  const toggleItem = (id: string) => {
    setOpenItems((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <Shell>
      <div className="px-8 py-8 max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="fade-in-up">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
            <span>Workspace</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-foreground">Evidence Verification</span>
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Evidence Verification</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Source-by-source evidence mapping for each extracted claim.
          </p>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-4 flex-wrap">
          {[
            { label: "Sources checked", value: "12" },
            { label: "Confirmed", value: "7", color: "text-chart-4" },
            { label: "Partial", value: "2", color: "text-yellow-400" },
            { label: "Failed", value: "3", color: "text-destructive" },
          ].map(({ label, value, color }) => (
            <div key={label} className="flex items-center gap-2 glass px-3 py-2 rounded-lg">
              <span className={cn("text-sm font-semibold", color || "text-foreground")}>{value}</span>
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>

        {/* Evidence groups */}
        <div className="space-y-3">
          {evidenceGroups.map((group) => {
            const cfg = statusConfig[group.overallStatus]
            const GroupIcon = cfg.icon
            const isOpen = openGroups.has(group.claim)

            return (
              <div key={group.claim} className="glass-card rounded-xl overflow-hidden border border-border">
                {/* Group header */}
                <button
                  onClick={() => toggleGroup(group.claim)}
                  className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-secondary/30 transition-colors"
                >
                  <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center shrink-0", cfg.bg)}>
                    <GroupIcon className={cn("w-3.5 h-3.5", cfg.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{group.claim}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {group.category} · {group.evidenceItems.length} source{group.evidenceItems.length !== 1 ? "s" : ""} checked
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="flex items-center gap-1.5">
                      <div className="w-12 h-1 rounded-full bg-input overflow-hidden">
                        <div
                          className={cn("h-full rounded-full", group.overallConfidence >= 80 ? "bg-electric-blue" : group.overallConfidence >= 50 ? "bg-chart-4" : "bg-destructive")}
                          style={{ width: `${group.overallConfidence}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">{group.overallConfidence}%</span>
                    </div>
                    <ChevronDown className={cn("w-4 h-4 text-muted-foreground transition-transform duration-200", isOpen && "rotate-180")} />
                  </div>
                </button>

                {/* Evidence items */}
                {isOpen && (
                  <div className="border-t border-border divide-y divide-border/60">
                    {group.evidenceItems.map((item) => {
                      const ecfg = evidenceStatusConfig[item.status]
                      const EIcon = ecfg.icon
                      const SourceIcon = item.sourceIcon
                      const isItemOpen = openItems.has(item.id)

                      return (
                        <div key={item.id} className="bg-secondary/20">
                          <button
                            onClick={() => toggleItem(item.id)}
                            className="w-full flex items-center gap-3 px-5 py-3 text-left hover:bg-secondary/40 transition-colors"
                          >
                            <div className="w-7 h-7 rounded-md bg-secondary border border-border flex items-center justify-center shrink-0">
                              <SourceIcon className="w-3.5 h-3.5 text-muted-foreground" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-foreground">{item.source}</span>
                                <span className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">{item.sourceType}</span>
                              </div>
                              <p className="text-xs text-muted-foreground mt-0.5 truncate">{item.description}</p>
                            </div>
                            <div className="flex items-center gap-3 shrink-0">
                              <div className={cn("flex items-center gap-1 px-2 py-0.5 rounded", item.status === "confirmed" ? "bg-chart-4/10" : item.status === "partial" ? "bg-yellow-400/10" : "bg-destructive/10")}>
                                <EIcon className={cn("w-3 h-3", ecfg.color)} />
                                <span className={cn("text-[10px] font-medium", ecfg.color)}>{ecfg.label}</span>
                              </div>
                              <ZoomIn className={cn("w-3.5 h-3.5 text-muted-foreground transition-transform", isItemOpen && "text-foreground")} />
                            </div>
                          </button>

                          {isItemOpen && item.details && (
                            <div className="px-5 pb-4 pt-2 ml-10 space-y-3">
                              <div className="grid grid-cols-1 gap-1">
                                {item.details.map((d, i) => (
                                  <div key={i} className="flex items-start gap-2">
                                    <div className={cn("mt-1.5 w-1 h-1 rounded-full shrink-0", item.status === "confirmed" ? "bg-chart-4" : item.status === "partial" ? "bg-yellow-400" : "bg-destructive")} />
                                    <span className="text-xs text-muted-foreground leading-relaxed">{d}</span>
                                  </div>
                                ))}
                              </div>
                              <div className="flex items-center justify-between pt-1">
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                  <Shield className="w-3 h-3" />
                                  <span>Confidence: {item.confidence}%</span>
                                  <span>·</span>
                                  <span>Checked {item.timestamp}</span>
                                </div>
                                {item.url && (
                                  <a href={item.url} className="flex items-center gap-1 text-xs text-electric-blue hover:opacity-80 transition-opacity">
                                    <Link2 className="w-3 h-3" />
                                    View source
                                    <ExternalLink className="w-2.5 h-2.5" />
                                  </a>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </Shell>
  )
}
