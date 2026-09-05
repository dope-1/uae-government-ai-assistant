"use client";

import { useEffect, useState } from "react";

import { fetchReadiness } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { Language, Readiness } from "@/lib/types";

interface SystemStatusProps {
  language: Language;
}

export function SystemStatus({ language }: SystemStatusProps) {
  const labels = t(language);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const result = await fetchReadiness();
        if (alive) {
          setReadiness(result);
          setFailed(false);
        }
      } catch {
        if (alive) {
          setReadiness(null);
          setFailed(true);
        }
      }
    };
    void check();
    const interval = window.setInterval(() => void check(), 30_000);
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, []);

  const rows = [
    { label: labels.backend, ok: readiness?.status === "ready" && !failed },
    { label: labels.postgres, ok: Boolean(readiness?.dependencies.postgres) && !failed },
    { label: labels.redis, ok: Boolean(readiness?.dependencies.redis) && !failed },
  ];

  return (
    <section className="side-card status-card" aria-labelledby="system-status-title">
      <div className="side-card-heading">
        <div>
          <span className="eyebrow">RUNTIME</span>
          <h2 id="system-status-title">{labels.system}</h2>
        </div>
        <span className={`status-beacon ${readiness?.status === "ready" && !failed ? "is-up" : ""}`} />
      </div>
      <div className="status-list" aria-live="polite">
        {rows.map((row) => (
          <div className="status-row" key={row.label}>
            <span>{row.label}</span>
            <strong className={readiness || failed ? (row.ok ? "status-up" : "status-down") : "status-checking"}>
              {!readiness && !failed ? labels.checking : row.ok ? labels.online : labels.offline}
            </strong>
          </div>
        ))}
      </div>
    </section>
  );
}
