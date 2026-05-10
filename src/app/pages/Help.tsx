import React from 'react';

export function Help() {
  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold text-foreground">Help</h1>

      <div className="space-y-4">
        <div className="glass-card rounded-xl border border-border p-5 space-y-2">
          <h3 className="text-sm font-semibold text-foreground">How it works</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            PathAI Verify audits resume claims against external evidence (GitHub, LinkedIn) and linguistic patterns to detect fabrications or AI-generated descriptions.
          </p>
        </div>

        <div className="glass-card rounded-xl border border-border p-5 space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Confidence Scores</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            A high score indicates verifiable evidence was found. A low score suggests a lack of public proof or timeline inconsistencies.
          </p>
        </div>

        <div className="glass-card rounded-xl border border-border p-5 space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Contact</h3>
          <p className="text-sm text-muted-foreground">support@pathai.verify</p>
        </div>
      </div>
    </div>
  );
}
