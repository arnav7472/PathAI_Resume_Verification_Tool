import React, { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Search } from "lucide-react";
import { useVerification, ScanResult } from "../context/VerificationContext";

export function Reports() {
  const { history, setCurrentScan } = useVerification();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  // Read initial query from URL: /reports?q=hardware
  const initialQ = params.get("q") ?? "";
  const [query, setQuery] = useState(initialQ);

  const normalizedQ = useMemo(() => query.trim().toLowerCase(), [query]);

  const filteredHistory = useMemo(() => {
    if (!normalizedQ) return history;

    return history.filter((r) => {
      const haystack = `${r.candidateName} ${r.jobDescription} ${r.id} ${r.date}`.toLowerCase();
      return haystack.includes(normalizedQ);
    });
  }, [history, normalizedQ]);

  const handleViewReport = (report: ScanResult) => {
    setCurrentScan(report);
    navigate("/summary");
  };

  const onChangeQuery = (val: string) => {
    setQuery(val);

    // Keep URL in sync (deep-link friendly)
    const q = val.trim();
    if (!q) {
      params.delete("q");
      setParams(params, { replace: true });
      return;
    }
    params.set("q", q);
    setParams(params, { replace: true });
  };

  const clearSearch = () => {
    setQuery("");
    params.delete("q");
    setParams(params, { replace: true });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center gap-3">
        <h1 className="text-2xl font-semibold text-foreground">Reports</h1>

        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search candidates…"
            value={query}
            onChange={(e) => onChangeQuery(e.target.value)}
            className="bg-secondary/60 border border-border rounded-lg px-8 py-1.5 text-xs text-foreground placeholder:text-muted-foreground outline-none focus:border-electric-blue/40"
            aria-label="Search report history"
          />
          {query.trim().length > 0 && (
            <button
              type="button"
              onClick={clearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {history.length === 0 ? (
        <div className="glass-card h-64 flex flex-col items-center justify-center border border-border rounded-xl text-muted-foreground text-sm">
          No history available. Run a scan to see it here.
        </div>
      ) : (
        <div className="glass-card border border-border rounded-xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-secondary/40 text-[10px] uppercase font-bold tracking-widest text-muted-foreground">
              <tr>
                <th className="px-6 py-4">Candidate</th>
                <th className="px-6 py-4">Job Description</th>
                <th className="px-6 py-4">Date</th>
                <th className="px-6 py-4 text-right">Confidence</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-border text-muted-foreground">
              {filteredHistory.map((r) => (
                <tr
                  key={r.id}
                  className="hover:bg-secondary/60 cursor-pointer transition-colors group"
                  onClick={() => handleViewReport(r)}
                >
                  <td className="px-6 py-4">
                    <div className="text-foreground font-medium group-hover:text-electric-blue transition-colors">
                      {r.candidateName}
                    </div>
                    <div className="text-[10px] text-muted-foreground">{r.id}</div>
                  </td>
                  <td className="px-6 py-4 max-w-xs truncate">{r.jobDescription || 'No JD saved'}</td>
                  <td className="px-6 py-4">{r.date}</td>
                  <td
                    className={`px-6 py-4 text-right font-bold ${
                      r.confidence > 80
                        ? "text-emerald-500"
                        : r.confidence > 60
                        ? "text-amber-500"
                        : "text-rose-500"
                    }`}
                  >
                    {r.confidence}%
                  </td>
                </tr>
              ))}

              {filteredHistory.length === 0 && (
                <tr>
                  <td className="px-6 py-8" colSpan={4}>
                    <div className="text-sm text-muted-foreground">
                      No results for{" "}
                      <span className="text-foreground font-semibold">
                        "{query.trim()}"
                      </span>
                      .
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Try a different name, job description keyword, ID, or date.
                    </div>
                    <div className="mt-3">
                      <button
                        type="button"
                        onClick={clearSearch}
                        className="px-3 py-2 text-xs font-semibold rounded border border-border bg-secondary/70 text-foreground hover:bg-secondary"
                      >
                        Clear search
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
