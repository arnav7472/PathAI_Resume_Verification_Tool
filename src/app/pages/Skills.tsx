import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useVerification, type ClaimView } from "../context/VerificationContext";

type SkillStatus = "Verified" | "Inflated" | "Buzzword" | "Likely";
type StatusFilter = "All" | SkillStatus;

function statusBadgeClasses(status: SkillStatus) {
  switch (status) {
    case "Verified":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "Buzzword":
      return "bg-rose-500/10 text-rose-400 border-rose-500/20";
    case "Inflated":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    case "Likely":
    default:
      return "bg-sky-500/10 text-sky-300 border-sky-500/20";
  }
}

function clampPct(n: number) {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

export function Skills() {
  const navigate = useNavigate();
  const { currentScan } = useVerification();

  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");

  if (!currentScan) {
    return (
      <div className="glass-card h-64 flex flex-col items-center justify-center border border-border rounded-xl">
        <p className="text-muted-foreground text-sm mb-4">No active scan results found.</p>
        <Link to="/" className="text-xs font-semibold text-electric-blue hover:underline">
          Run your first scan
        </Link>
      </div>
    );
  }

  const skills = currentScan.claimViews as ClaimView[];
  const normalizedQ = useMemo(() => query.trim().toLowerCase(), [query]);

  const filteredSkills = useMemo(() => {
    return skills.filter((skill) => {
      const haystack = `${skill.name} ${skill.category} ${skill.claimed} ${skill.status} ${skill.reason}`.toLowerCase();
      const matchesText = !normalizedQ || haystack.includes(normalizedQ);
      const matchesStatus = statusFilter === "All" || skill.status === statusFilter;
      return matchesText && matchesStatus;
    });
  }, [skills, normalizedQ, statusFilter]);

  const hasNoResults = filteredSkills.length === 0;
  const hasActiveFilters = normalizedQ.length > 0 || statusFilter !== "All";

  const clearFilters = () => {
    setQuery("");
    setStatusFilter("All");
  };

  const goReportsWithQuery = () => {
    const q = query.trim();
    navigate(`/reports?q=${encodeURIComponent(q)}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Claims Breakdown</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Search extracted skills and claims. Try:{" "}
            <span className="text-foreground">"kubernetes"</span>,{" "}
            <span className="text-foreground">"experience"</span>,{" "}
            <span className="text-foreground">"verified"</span>.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Search skills or claims (e.g. "python", "docker")'
            className="w-full sm:w-80 bg-secondary/70 border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-electric-blue/30"
            aria-label="Search skills and claims"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="bg-secondary/70 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-electric-blue/30"
            aria-label="Filter by status"
          >
            <option value="All">All statuses</option>
            <option value="Verified">Verified</option>
            <option value="Inflated">Inflated</option>
            <option value="Buzzword">Buzzword</option>
            <option value="Likely">Likely</option>
          </select>
        </div>
      </div>

      {hasNoResults && hasActiveFilters && (
        <div className="glass-card border border-border rounded-xl p-5">
          <div className="text-sm text-foreground">
            No results for{" "}
            <span className="text-white font-semibold">"{query.trim()}"</span>.
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            This page searches extracted claims only. If you meant candidate names or report IDs, search in{" "}
            <span className="text-foreground">Reports</span>.
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={clearFilters}
              className="px-3 py-2 text-xs font-semibold rounded border border-border bg-secondary/70 text-foreground hover:bg-secondary"
            >
              Clear filters
            </button>

            <button
              type="button"
              onClick={goReportsWithQuery}
              disabled={!query.trim()}
              className="px-3 py-2 text-xs font-semibold rounded bg-electric-blue text-background hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Search in Reports
            </button>
          </div>
        </div>
      )}

      <div className="glass-card border border-border rounded-xl overflow-hidden">
        {currentScan.skills.length > 0 && (
          <div className="border-b border-border bg-secondary/40 px-6 py-4">
            <p className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground mb-3">Extracted Skills</p>
            <div className="flex flex-wrap gap-2">
              {currentScan.skills.map((skill) => (
                <span key={skill} className="rounded border border-border bg-secondary px-2 py-1 text-xs text-foreground">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
        <table className="w-full text-left text-sm">
          <thead className="bg-secondary/40 text-[10px] uppercase font-bold tracking-widest text-muted-foreground">
            <tr>
              <th className="px-6 py-4">Claim</th>
              <th className="px-6 py-4">Evidence</th>
              <th className="px-6 py-4">Confidence</th>
              <th className="px-6 py-4">Status</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {filteredSkills.map((skill, i) => {
              const pct = clampPct(skill.conf);

              return (
                <tr key={`${skill.name}-${skill.category}-${i}`} className="hover:bg-secondary/50">
                  <td className="px-6 py-4">
                    <div className="text-foreground font-medium">{skill.name}</div>
                    <div className="text-[10px] text-muted-foreground">{skill.category}</div>
                  </td>

                  <td className="px-6 py-4 text-muted-foreground">{skill.claimed}</td>

                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-foreground font-bold">{pct}%</span>
                      <div className="w-16 h-1 bg-secondary rounded-full overflow-hidden">
                        <div className="h-full bg-electric-blue" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </td>

                  <td className="px-6 py-4">
                    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${statusBadgeClasses(skill.status)}`}>
                      {skill.status}
                    </span>
                  </td>
                </tr>
              );
            })}

            {filteredSkills.length === 0 && (
              <tr>
                <td className="px-6 py-8" colSpan={4}>
                  <div className="text-sm text-muted-foreground">No skills or claims to display.</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {hasActiveFilters ? "Try a different keyword or reset the status filter." : "This scan contains zero extracted skills or claims."}
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="space-y-4 pt-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Claim Context</h2>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-[11px] font-bold text-muted-foreground hover:text-foreground"
            >
              Reset
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredSkills.map((skill, i) => (
            <div key={`${skill.name}-ctx-${i}`} className="glass-card p-4 border border-border rounded-xl">
              <p className="text-xs font-bold text-foreground mb-1">{skill.name}</p>
              <p className="text-xs text-muted-foreground leading-relaxed italic">"{skill.reason}"</p>
            </div>
          ))}

          {filteredSkills.length === 0 && (
            <div className="glass-card p-4 border border-border rounded-xl">
              <p className="text-xs font-bold text-foreground mb-1">No context</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                There are no matching claims to show context for.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
