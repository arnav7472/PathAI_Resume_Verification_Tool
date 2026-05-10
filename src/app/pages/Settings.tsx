import React, { useEffect, useState } from 'react';

type Strictness = 'low' | 'medium' | 'high';

export function Settings() {
  const [strictness, setStrictness] = useState<Strictness>('medium');
  const [crossReferenceSync, setCrossReferenceSync] = useState(true);

  useEffect(() => {
    const savedStrictness = localStorage.getItem('pathai_strictness');
    const savedCrossRef = localStorage.getItem('pathai_cross_reference_sync');
    if (savedStrictness === 'low' || savedStrictness === 'medium' || savedStrictness === 'high') {
      setStrictness(savedStrictness);
    }
    if (savedCrossRef !== null) {
      setCrossReferenceSync(savedCrossRef === 'true');
    }
  }, []);

  const updateStrictness = (value: Strictness) => {
    setStrictness(value);
    localStorage.setItem('pathai_strictness', value);
  };

  const updateCrossReference = (value: boolean) => {
    setCrossReferenceSync(value);
    localStorage.setItem('pathai_cross_reference_sync', String(value));
  };

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold text-foreground">Settings</h1>

      <div className="space-y-6">
        <section className="glass-card rounded-xl border border-border p-5 space-y-4">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">Scanning</h2>
          <div className="space-y-5">
            <div className="flex justify-between items-center gap-4 pb-4 border-b border-border">
              <div>
                <span className="text-sm text-foreground">Strictness Level</span>
                <p className="text-xs text-muted-foreground mt-1">Controls JD matching tolerance and evidence penalties.</p>
              </div>
              <select
                value={strictness}
                onChange={(event) => updateStrictness(event.target.value as Strictness)}
                className="bg-secondary/70 border border-border text-xs px-3 py-2 rounded-lg text-foreground"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div className="flex justify-between items-center gap-4">
              <div>
                <span className="text-sm text-foreground">Cross-Reference Sync</span>
                <p className="text-xs text-muted-foreground mt-1">Checks whether skills, projects, certifications, and senior claims support each other.</p>
              </div>
              <button
                type="button"
                onClick={() => updateCrossReference(!crossReferenceSync)}
                className={`w-10 h-5 rounded-full flex p-1 transition-colors ${crossReferenceSync ? 'bg-electric-blue justify-end' : 'bg-secondary justify-start border border-border'}`}
                aria-pressed={crossReferenceSync}
                aria-label="Toggle cross-reference sync"
              >
                <span className="w-3 h-3 bg-foreground rounded-full" />
              </button>
            </div>
          </div>
        </section>

        <section className="glass-card rounded-xl border border-border p-5 space-y-4">
          <h2 className="text-xs uppercase font-bold tracking-widest text-muted-foreground">API Access</h2>
          <div className="p-3 bg-secondary/60 rounded-lg font-mono text-[10px] text-muted-foreground flex justify-between border border-border">
            <span>Configured by deployment environment</span>
            <span className="text-electric-blue">Active</span>
          </div>
        </section>
      </div>
    </div>
  );
}
