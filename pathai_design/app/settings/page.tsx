"use client"

import { useState } from "react"
import { Shell } from "@/components/shell"
import {
  ChevronRight,
  Shield,
  Bell,
  Users,
  Key,
  Globe,
  Database,
  Zap,
  Save,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
} from "lucide-react"
import { cn } from "@/lib/utils"

const sections = [
  { id: "verification", label: "Verification", icon: Shield },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "integrations", label: "Integrations", icon: Globe },
  { id: "team", label: "Team & Access", icon: Users },
  { id: "api", label: "API Keys", icon: Key },
]

interface ToggleRowProps {
  label: string
  description: string
  value: boolean
  onChange: (v: boolean) => void
  accent?: boolean
}

function ToggleRow({ label, description, value, onChange, accent }: ToggleRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-4 border-b border-border last:border-0">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{description}</p>
      </div>
      <button
        onClick={() => onChange(!value)}
        className={cn(
          "relative flex-shrink-0 w-10 h-5.5 rounded-full transition-colors duration-200 mt-0.5",
          value
            ? accent ? "bg-cyan-accent" : "bg-electric-blue"
            : "bg-secondary border border-border"
        )}
        style={{ height: "22px", width: "40px" }}
      >
        <span
          className={cn(
            "absolute top-0.5 w-4 h-4 rounded-full bg-foreground shadow transition-all duration-200",
            value ? "left-5" : "left-0.5"
          )}
        />
      </button>
    </div>
  )
}

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("verification")
  const [saved, setSaved] = useState(false)

  // Verification settings
  const [crossRef, setCrossRef] = useState(true)
  const [deepAnalysis, setDeepAnalysis] = useState(true)
  const [autoFlag, setAutoFlag] = useState(true)
  const [dateValidation, setDateValidation] = useState(true)
  const [defaultStrictness, setDefaultStrictness] = useState("standard")

  // Notification settings
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [scanComplete, setScanComplete] = useState(true)
  const [highRisk, setHighRisk] = useState(true)
  const [weeklyDigest, setWeeklyDigest] = useState(false)

  // Integration settings
  const [linkedinInteg, setLinkedinInteg] = useState(true)
  const [githubInteg, setGithubInteg] = useState(true)
  const [scholarInteg, setScholarInteg] = useState(false)
  const [awsInteg, setAwsInteg] = useState(true)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <Shell>
      <div className="px-8 py-8 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between fade-in-up">
          <div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
              <span>Workspace</span>
              <ChevronRight className="w-3 h-3" />
              <span className="text-foreground">Settings</span>
            </div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Settings</h1>
            <p className="mt-1 text-sm text-muted-foreground">Manage your PathAI Verify workspace configuration.</p>
          </div>
          <button
            onClick={handleSave}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200",
              saved
                ? "bg-chart-4/20 text-chart-4 border border-chart-4/30"
                : "bg-electric-blue text-background hover:opacity-90 glow-blue"
            )}
          >
            {saved ? (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Saved
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>

        <div className="flex gap-6">
          {/* Sidebar nav */}
          <div className="w-44 shrink-0 space-y-0.5">
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
                  activeSection === id
                    ? "bg-secondary text-foreground font-medium border border-border"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <Icon className={cn("w-3.5 h-3.5", activeSection === id ? "text-electric-blue" : "text-muted-foreground")} />
                {label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 space-y-4">
            {activeSection === "verification" && (
              <>
                <div className="glass-card rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <Shield className="w-4 h-4 text-electric-blue" />
                    <p className="text-sm font-semibold text-foreground">Verification Engine</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4">Configure how PathAI Verify analyzes resumes.</p>
                  <ToggleRow label="Cross-reference Sync" description="Validate claims against LinkedIn, GitHub, and academic databases in real-time." value={crossRef} onChange={setCrossRef} />
                  <ToggleRow label="Deep Analysis Mode" description="Run extended NLP analysis to detect inconsistencies and semantic mismatches." value={deepAnalysis} onChange={setDeepAnalysis} />
                  <ToggleRow label="Auto-flag Anomalies" description="Automatically flag claims with confidence scores below 30%." value={autoFlag} onChange={setAutoFlag} />
                  <ToggleRow label="Employment Date Validation" description="Verify that employment date ranges are logically consistent." value={dateValidation} onChange={setDateValidation} />
                </div>

                <div className="glass-card rounded-xl p-5">
                  <p className="text-sm font-semibold text-foreground mb-1">Default Strictness Level</p>
                  <p className="text-xs text-muted-foreground mb-4">This applies to all new scans unless overridden at scan time.</p>
                  <div className="space-y-2">
                    {[
                      { value: "lenient", label: "Lenient", desc: "Broad matching, lower false positive rate. Best for early-stage screening." },
                      { value: "standard", label: "Standard", desc: "Balanced accuracy and coverage. Recommended for most hiring workflows." },
                      { value: "strict", label: "Strict", desc: "Exact matching required. Best for senior or specialized roles." },
                    ].map(({ value, label, desc }) => (
                      <button
                        key={value}
                        onClick={() => setDefaultStrictness(value)}
                        className={cn(
                          "w-full flex items-start gap-3 p-3 rounded-lg border text-left transition-all duration-150",
                          defaultStrictness === value
                            ? "bg-secondary border-electric-blue/40"
                            : "border-border hover:bg-secondary/50"
                        )}
                      >
                        <div className={cn(
                          "mt-0.5 w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors",
                          defaultStrictness === value ? "border-electric-blue" : "border-muted-foreground"
                        )}>
                          {defaultStrictness === value && <div className="w-1.5 h-1.5 rounded-full bg-electric-blue" />}
                        </div>
                        <div>
                          <p className={cn("text-sm font-medium", defaultStrictness === value ? "text-foreground" : "text-muted-foreground")}>{label}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{desc}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeSection === "notifications" && (
              <div className="glass-card rounded-xl p-5">
                <div className="flex items-center gap-2 mb-1">
                  <Bell className="w-4 h-4 text-electric-blue" />
                  <p className="text-sm font-semibold text-foreground">Notification Preferences</p>
                </div>
                <p className="text-xs text-muted-foreground mb-4">Choose when and how you receive alerts.</p>
                <ToggleRow label="Email Alerts" description="Send all notifications to your registered email address." value={emailAlerts} onChange={setEmailAlerts} />
                <ToggleRow label="Scan Complete" description="Notify when an AI verification scan finishes processing." value={scanComplete} onChange={setScanComplete} />
                <ToggleRow label="High-Risk Alerts" description="Immediate notification when a resume receives a risk score above threshold." value={highRisk} onChange={setHighRisk} accent />
                <ToggleRow label="Weekly Digest" description="Summary email every Monday with verification stats and team activity." value={weeklyDigest} onChange={setWeeklyDigest} />
              </div>
            )}

            {activeSection === "integrations" && (
              <div className="glass-card rounded-xl p-5">
                <div className="flex items-center gap-2 mb-1">
                  <Globe className="w-4 h-4 text-electric-blue" />
                  <p className="text-sm font-semibold text-foreground">External Integrations</p>
                </div>
                <p className="text-xs text-muted-foreground mb-4">Control which external sources PathAI uses for cross-referencing.</p>
                <ToggleRow label="LinkedIn Integration" description="Cross-reference employment history and endorsements via LinkedIn API." value={linkedinInteg} onChange={setLinkedinInteg} />
                <ToggleRow label="GitHub Integration" description="Verify coding skills and activity through GitHub profile analysis." value={githubInteg} onChange={setGithubInteg} />
                <ToggleRow label="Google Scholar" description="Check academic publications and citations in scholarly databases." value={scholarInteg} onChange={setScholarInteg} />
                <ToggleRow label="AWS Credential Portal" description="Validate AWS certifications against the official credential registry." value={awsInteg} onChange={setAwsInteg} />
              </div>
            )}

            {activeSection === "team" && (
              <div className="glass-card rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-electric-blue" />
                  <p className="text-sm font-semibold text-foreground">Team Members</p>
                </div>
                <div className="space-y-2">
                  {[
                    { name: "Sarah Chen", role: "Admin", email: "sarah@company.com", active: true },
                    { name: "Marcus Webb", role: "Reviewer", email: "marcus@company.com", active: true },
                    { name: "Priya Nair", role: "Viewer", email: "priya@company.com", active: false },
                  ].map(({ name, role, email, active }) => (
                    <div key={email} className="flex items-center gap-3 p-3 rounded-lg bg-secondary/40">
                      <div className="relative w-8 h-8 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0">
                        <span className="text-xs font-bold text-foreground">{name[0]}</span>
                        {active && <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-chart-4 border-2 border-card" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">{name}</p>
                        <p className="text-xs text-muted-foreground">{email}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="flex items-center gap-1 px-2 py-1 rounded bg-secondary border border-border text-xs text-muted-foreground hover:text-foreground transition-colors">
                          {role}
                          <ChevronDown className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <button className="w-full py-2.5 rounded-lg border border-dashed border-border text-xs font-medium text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors">
                  + Invite team member
                </button>
              </div>
            )}

            {activeSection === "api" && (
              <div className="glass-card rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <Key className="w-4 h-4 text-electric-blue" />
                  <p className="text-sm font-semibold text-foreground">API Configuration</p>
                </div>
                <div className="space-y-3">
                  {[
                    { label: "PathAI Verify API Key", key: "path_live_sk_••••••••••••••••••••••••••••", created: "Jan 12, 2026" },
                    { label: "LinkedIn API Token", key: "linked_••••••••••••••••••••••••", created: "Mar 5, 2026" },
                    { label: "GitHub OAuth Token", key: "ghp_••••••••••••••••••••••••••••••", created: "Apr 20, 2026" },
                  ].map(({ label, key, created }) => (
                    <div key={label} className="p-4 rounded-lg bg-secondary/40 border border-border space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold text-foreground">{label}</p>
                        <div className="flex items-center gap-1.5">
                          <button className="text-[10px] text-muted-foreground hover:text-foreground px-2 py-0.5 rounded bg-secondary transition-colors">
                            Reveal
                          </button>
                          <button className="text-[10px] text-destructive hover:opacity-80 px-2 py-0.5 rounded bg-destructive/10 transition-opacity">
                            Revoke
                          </button>
                        </div>
                      </div>
                      <code className="block text-xs font-mono text-muted-foreground bg-background/50 px-3 py-2 rounded border border-border">
                        {key}
                      </code>
                      <p className="text-[10px] text-muted-foreground">Created {created}</p>
                    </div>
                  ))}
                </div>
                <button className="flex items-center gap-1.5 text-xs font-medium text-electric-blue hover:opacity-80 transition-opacity">
                  <Zap className="w-3.5 h-3.5" />
                  Generate new API key
                </button>
              </div>
            )}

            {/* Data section always visible */}
            <div className="glass-card rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Database className="w-4 h-4 text-muted-foreground" />
                <p className="text-sm font-semibold text-foreground">Data & Privacy</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border bg-secondary/40 text-xs text-muted-foreground hover:text-foreground transition-colors">
                  <RefreshCw className="w-3.5 h-3.5" />
                  Clear scan history
                </button>
                <button className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border bg-secondary/40 text-xs text-muted-foreground hover:text-foreground transition-colors">
                  <Database className="w-3.5 h-3.5" />
                  Export all data
                </button>
              </div>
              <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed">
                All resume data is encrypted at rest and in transit. Scans are retained for 90 days unless manually deleted.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Shell>
  )
}
