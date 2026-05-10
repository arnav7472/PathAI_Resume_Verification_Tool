"use client"

import { Shell } from "@/components/shell"
import {
  ChevronRight,
  Download,
  FileText,
  Share2,
  TrendingUp,
  CheckCircle2,
  XCircle,
  AlertCircle,
  BarChart3,
  Calendar,
  Clock,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from "recharts"
import { cn } from "@/lib/utils"

const claimsByCategory = [
  { name: "Experience", verified: 3, unverified: 1, flagged: 1 },
  { name: "Education", verified: 1, unverified: 0, flagged: 0 },
  { name: "Skills", verified: 2, unverified: 1, flagged: 0 },
  { name: "Certifications", verified: 1, unverified: 0, flagged: 1 },
  { name: "Projects", verified: 1, unverified: 1, flagged: 0 },
]

const pieData = [
  { name: "Verified", value: 8, color: "oklch(0.72 0.20 145)" },
  { name: "Unverified", value: 6, color: "oklch(0.55 0.03 235)" },
  { name: "Flagged", value: 2, color: "oklch(0.55 0.22 25)" },
]

const confidenceTrend = [
  { month: "Jan", avg: 62 },
  { month: "Feb", avg: 71 },
  { month: "Mar", avg: 68 },
  { month: "Apr", avg: 79 },
  { month: "May", avg: 75 },
  { month: "Jun", avg: 83 },
  { month: "Jul", avg: 87 },
]

const pastReports = [
  { name: "Jordan Mitchell — Senior SWE", date: "May 10, 2026", score: 87, status: "verified", time: "4m 12s" },
  { name: "Alex Chen — Product Manager", date: "May 8, 2026", score: 91, status: "verified", time: "3m 58s" },
  { name: "Riley Johnson — Data Scientist", date: "May 6, 2026", score: 54, status: "flagged", time: "5m 31s" },
  { name: "Morgan Davis — DevOps Engineer", date: "May 4, 2026", score: 78, status: "verified", time: "4m 44s" },
  { name: "Sam Wilson — Frontend Lead", date: "May 2, 2026", score: 63, status: "unverified", time: "3m 22s" },
]

const statusConfig = {
  verified: { icon: CheckCircle2, color: "text-chart-4", bg: "bg-chart-4/10", label: "Verified" },
  unverified: { icon: AlertCircle, color: "text-muted-foreground", bg: "bg-secondary", label: "Unverified" },
  flagged: { icon: XCircle, color: "text-destructive", bg: "bg-destructive/10", label: "Flagged" },
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: {value: number; name: string; fill: string}[]; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-card rounded-lg p-3 text-xs border border-border space-y-1">
        <p className="font-semibold text-foreground mb-1">{label}</p>
        {payload.map((p) => (
          <div key={p.name} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: p.fill }} />
            <span className="text-muted-foreground capitalize">{p.name}:</span>
            <span className="text-foreground font-medium">{p.value}</span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export default function ReportsPage() {
  return (
    <Shell>
      <div className="px-8 py-8 max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between fade-in-up">
          <div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
              <span>Workspace</span>
              <ChevronRight className="w-3 h-3" />
              <span className="text-foreground">Reports</span>
            </div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Reports & Analytics</h1>
            <p className="mt-1 text-sm text-muted-foreground">Aggregate verification insights and export options.</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-secondary border border-border text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">
              <Share2 className="w-3.5 h-3.5" />
              Share
            </button>
            <button className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-electric-blue text-background text-xs font-semibold hover:opacity-90 transition-opacity">
              <Download className="w-3.5 h-3.5" />
              Export PDF
            </button>
          </div>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total Verifications", value: "247", delta: "+18 this month", icon: FileText, color: "text-electric-blue" },
            { label: "Avg Confidence", value: "79%", delta: "+3.2% vs last month", icon: TrendingUp, color: "text-cyan-accent" },
            { label: "High-Risk Resumes", value: "12", delta: "4.9% of total", icon: XCircle, color: "text-destructive" },
            { label: "Avg Scan Time", value: "4m 18s", delta: "Across all scans", icon: Clock, color: "text-chart-3" },
          ].map(({ label, value, delta, icon: Icon, color }) => (
            <div key={label} className="glass-card rounded-xl p-5 border border-border">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground">{label}</span>
                <Icon className={cn("w-4 h-4", color)} />
              </div>
              <p className={cn("text-2xl font-bold tracking-tight", color)}>{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{delta}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Stacked bar chart */}
          <div className="lg:col-span-2 glass-card rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-semibold text-foreground">Claims by Category</p>
                <p className="text-xs text-muted-foreground mt-0.5">Verification outcomes per section</p>
              </div>
              <BarChart3 className="w-4 h-4 text-muted-foreground" />
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={claimsByCategory} barGap={2} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <XAxis dataKey="name" tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: "oklch(0.17 0.02 250 / 0.5)" }} />
                <Bar dataKey="verified" stackId="a" fill="oklch(0.65 0.22 215)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="unverified" stackId="a" fill="oklch(0.35 0.03 250)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="flagged" stackId="a" fill="oklch(0.55 0.22 25)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="flex items-center gap-4 mt-2 justify-center">
              {[
                { label: "Verified", color: "bg-electric-blue" },
                { label: "Unverified", color: "bg-muted" },
                { label: "Flagged", color: "bg-destructive" },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <div className={cn("w-2 h-2 rounded-sm", color)} />
                  <span className="text-[11px] text-muted-foreground">{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Pie chart */}
          <div className="glass-card rounded-xl p-5">
            <p className="text-sm font-semibold text-foreground mb-1">Claim Outcomes</p>
            <p className="text-xs text-muted-foreground mb-3">Distribution across all claims</p>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "oklch(0.13 0.018 250)", border: "1px solid oklch(0.22 0.02 250)", borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2 mt-2">
              {pieData.map(({ name, value, color }) => (
                <div key={name} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                  <span className="text-xs text-muted-foreground flex-1">{name}</span>
                  <span className="text-xs font-medium text-foreground">{value}</span>
                  <span className="text-xs text-muted-foreground">{Math.round((value / 16) * 100)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Trend line */}
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold text-foreground">Average Confidence Over Time</p>
              <p className="text-xs text-muted-foreground mt-0.5">Monthly average across all candidates</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-chart-4">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>+25% since Jan</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={confidenceTrend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <XAxis dataKey="month" tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "oklch(0.55 0.03 235)", fontSize: 11 }} axisLine={false} tickLine={false} domain={[40, 100]} />
              <Tooltip contentStyle={{ background: "oklch(0.13 0.018 250)", border: "1px solid oklch(0.22 0.02 250)", borderRadius: 8, fontSize: 12 }} itemStyle={{ color: "oklch(0.72 0.16 195)" }} />
              <Line type="monotone" dataKey="avg" stroke="oklch(0.72 0.16 195)" strokeWidth={2} dot={{ fill: "oklch(0.72 0.16 195)", r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Past reports table */}
        <div className="glass-card rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">Recent Verifications</p>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Calendar className="w-3.5 h-3.5" />
              <span>Last 30 days</span>
            </div>
          </div>
          <div className="divide-y divide-border">
            {pastReports.map(({ name, date, score, status, time }) => {
              const cfg = statusConfig[status as keyof typeof statusConfig]
              const Icon = cfg.icon
              return (
                <div key={name} className="flex items-center gap-4 px-5 py-3.5 hover:bg-secondary/30 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-secondary border border-border flex items-center justify-center shrink-0">
                    <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{name}</p>
                    <p className="text-xs text-muted-foreground">{date}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-10 h-1 rounded-full bg-input overflow-hidden">
                      <div
                        className={cn("h-full rounded-full", score >= 80 ? "bg-electric-blue" : score >= 60 ? "bg-chart-4" : "bg-destructive")}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground w-8">{score}%</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    <span>{time}</span>
                  </div>
                  <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-md", cfg.bg)}>
                    <Icon className={cn("w-3 h-3", cfg.color)} />
                    <span className={cn("text-[10px] font-medium", cfg.color)}>{cfg.label}</span>
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground">
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </Shell>
  )
}
