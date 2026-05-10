"use client"

import { Shell } from "@/components/shell"
import {
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronRight,
  User,
  Calendar,
  Briefcase,
  Award,
  BarChart3,
} from "lucide-react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
} from "recharts"
import { cn } from "@/lib/utils"
import Link from "next/link"

const scoreCards = [
  {
    label: "Overall Confidence",
    value: "87%",
    delta: "+4%",
    up: true,
    color: "text-electric-blue",
    bg: "bg-electric-blue/10",
    border: "border-electric-blue/20",
    icon: Award,
  },
  {
    label: "Claims Verified",
    value: "14 / 18",
    delta: "78%",
    up: true,
    color: "text-chart-4",
    bg: "bg-chart-4/10",
    border: "border-chart-4/20",
    icon: CheckCircle2,
  },
  {
    label: "Risk Score",
    value: "Low",
    delta: "3 flags",
    up: false,
    color: "text-cyan-accent",
    bg: "bg-cyan-accent/10",
    border: "border-cyan-accent/20",
    icon: ShieldAlert,
  },
  {
    label: "Skill Match",
    value: "72%",
    delta: "vs JD",
    up: true,
    color: "text-chart-3",
    bg: "bg-chart-3/10",
    border: "border-chart-3/20",
    icon: Briefcase,
  },
]

const areaData = [
  { label: "Jan", score: 62 },
  { label: "Feb", score: 71 },
  { label: "Mar", score: 68 },
  { label: "Apr", score: 79 },
  { label: "May", score: 75 },
  { label: "Jun", score: 83 },
  { label: "Jul", score: 87 },
]

const radarData = [
  { subject: "Education", A: 90 },
  { subject: "Experience", A: 75 },
  { subject: "Skills", A: 88 },
  { subject: "Certifications", A: 60 },
  { subject: "Projects", A: 72 },
  { subject: "References", A: 55 },
]

const skills = [
  { name: "React", level: 92, verified: true },
  { name: "TypeScript", level: 88, verified: true },
  { name: "Node.js", level: 81, verified: true },
  { name: "PostgreSQL", level: 74, verified: true },
  { name: "AWS", level: 65, verified: false },
  { name: "Docker", level: 58, verified: false },
]

const recentClaims = [
  { claim: "Senior Software Engineer at Acme Corp (2020–2023)", status: "verified" },
  { claim: "Led team of 8 engineers across 3 product lines", status: "unverified" },
  { claim: "AWS Certified Solutions Architect (2022)", status: "flagged" },
  { claim: "Reduced system latency by 40%", status: "unverified" },
  { claim: "B.S. Computer Science, MIT (2018)", status: "verified" },
]

const statusConfig = {
  verified: { label: "Verified", icon: CheckCircle2, color: "text-chart-4", bg: "bg-chart-4/10" },
  unverified: { label: "Unverified", icon: AlertCircle, color: "text-muted-foreground", bg: "bg-secondary" },
  flagged: { label: "Flagged", icon: XCircle, color: "text-destructive", bg: "bg-destructive/10" },
}

export default function DashboardPage() {
  return (
    <Shell>
      <div className="px-8 py-8 max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between fade-in-up">
          <div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
              <span>Workspace</span>
              <ChevronRight className="w-3 h-3" />
              <span className="text-foreground">Verification Summary</span>
            </div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Summary Dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">Analysis complete · Candidate: Jordan Mitchell · {new Date().toLocaleDateString()}</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-chart-4/10 border border-chart-4/20">
            <span className="w-2 h-2 rounded-full bg-chart-4 pulse-dot" />
            <span className="text-xs font-medium text-chart-4">Analysis Complete</span>
          </div>
        </div>

        {/* Candidate card */}
        <div className="glass-card rounded-xl p-4 flex items-center gap-5">
          <div className="w-12 h-12 rounded-xl bg-secondary border border-border flex items-center justify-center shrink-0">
            <User className="w-5 h-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold text-foreground">Jordan Mitchell</p>
            <p className="text-sm text-muted-foreground">Senior Software Engineer · San Francisco, CA</p>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              <span>8 years exp.</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5" />
              <span>3 companies</span>
            </div>
            <div className="flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5" />
              <span>18 claims</span>
            </div>
          </div>
          <Link
            href="/claims"
            className="hidden md:flex items-center gap-1.5 text-xs font-medium text-electric-blue hover:opacity-80 transition-opacity"
          >
            View Claims <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Score cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {scoreCards.map(({ label, value, delta, up, color, bg, border, icon: Icon }) => (
            <div key={label} className={cn("glass-card rounded-xl p-5 border", border)}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-muted-foreground">{label}</span>
                <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center", bg)}>
                  <Icon className={cn("w-3.5 h-3.5", color)} />
                </div>
              </div>
              <p className={cn("text-2xl font-bold tracking-tight", color)}>{value}</p>
              <p className={cn("text-xs mt-1 flex items-center gap-1", up ? "text-chart-4" : "text-muted-foreground")}>
                {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {delta}
              </p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Area chart */}
          <div className="lg:col-span-2 glass-card rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-semibold text-foreground">Confidence Trend</p>
                <p className="text-xs text-muted-foreground mt-0.5">Rolling confidence score over time</p>
              </div>
              <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded">Last 7 months</span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={areaData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="oklch(0.65 0.22 215)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="oklch(0.65 0.22 215)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="label" tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 11 }} axisLine={false} tickLine={false} domain={[40, 100]} />
                <Tooltip
                  contentStyle={{ background: "oklch(0.13 0.018 250)", border: "1px solid oklch(0.22 0.02 250)", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "oklch(0.93 0.01 220)" }}
                  itemStyle={{ color: "oklch(0.65 0.22 215)" }}
                />
                <Area type="monotone" dataKey="score" stroke="oklch(0.65 0.22 215)" strokeWidth={2} fill="url(#blueGrad)" dot={false} activeDot={{ r: 4, fill: "oklch(0.65 0.22 215)" }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Radar chart */}
          <div className="glass-card rounded-xl p-5">
            <p className="text-sm font-semibold text-foreground mb-1">Claim Categories</p>
            <p className="text-xs text-muted-foreground mb-3">Verification coverage by section</p>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData} margin={{ top: 0, right: 10, bottom: 0, left: 10 }}>
                <PolarGrid stroke="oklch(0.22 0.02 250)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 10 }} />
                <Radar dataKey="A" stroke="oklch(0.72 0.16 195)" fill="oklch(0.72 0.16 195)" fillOpacity={0.15} strokeWidth={1.5} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Skills */}
          <div className="glass-card rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-foreground">Extracted Skills</p>
              <Link href="/claims" className="text-xs text-electric-blue hover:opacity-80 transition-opacity">View all</Link>
            </div>
            <div className="space-y-3">
              {skills.map(({ name, level, verified }) => (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{name}</span>
                      {verified ? (
                        <CheckCircle2 className="w-3 h-3 text-chart-4" />
                      ) : (
                        <AlertCircle className="w-3 h-3 text-muted-foreground" />
                      )}
                    </div>
                    <span className="text-muted-foreground">{level}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all", verified ? "bg-electric-blue" : "bg-muted-foreground/50")}
                      style={{ width: `${level}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent claims */}
          <div className="glass-card rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-foreground">Recent Claims</p>
              <Link href="/claims" className="text-xs text-electric-blue hover:opacity-80 transition-opacity">View all</Link>
            </div>
            <div className="space-y-2">
              {recentClaims.map(({ claim, status }) => {
                const cfg = statusConfig[status as keyof typeof statusConfig]
                const Icon = cfg.icon
                return (
                  <div key={claim} className="flex items-start gap-3 p-3 rounded-lg bg-secondary/40 hover:bg-secondary/70 transition-colors">
                    <div className={cn("mt-0.5 w-5 h-5 rounded-md flex items-center justify-center shrink-0", cfg.bg)}>
                      <Icon className={cn("w-3 h-3", cfg.color)} />
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed flex-1">{claim}</p>
                    <span className={cn("shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded", cfg.bg, cfg.color)}>
                      {cfg.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  )
}
