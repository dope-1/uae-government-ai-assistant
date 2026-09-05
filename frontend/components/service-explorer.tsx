"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { fetchServices } from "@/lib/api";
import { containsArabic, t } from "@/lib/i18n";
import type { Jurisdiction, Language, ServiceSummary } from "@/lib/types";

interface ServiceExplorerProps {
  language: Language;
  jurisdiction: Jurisdiction | null;
}

export function ServiceExplorer({ language, jurisdiction }: ServiceExplorerProps) {
  const labels = t(language);
  const [query, setQuery] = useState("");
  const [services, setServices] = useState<ServiceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (nextQuery: string) => {
    setLoading(true);
    setError(null);
    try {
      setServices(await fetchServices(jurisdiction, nextQuery));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load services.");
      setServices([]);
    } finally {
      setLoading(false);
    }
  }, [jurisdiction]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh("");
    }, 0);

    return () => window.clearTimeout(timer);
  }, [refresh]);

  const orderedServices = useMemo(() => {
    return [...services]
      .sort((left, right) => {
        const leftMatches = containsArabic(left.service_name) === (language === "ar") ? 1 : 0;
        const rightMatches = containsArabic(right.service_name) === (language === "ar") ? 1 : 0;
        return rightMatches - leftMatches || left.service_name.localeCompare(right.service_name);
      })
      .slice(0, 6);
  }, [language, services]);

  return (
    <section className="side-card service-explorer" aria-labelledby="service-explorer-title">
      <div className="side-card-heading">
        <div>
          <span className="eyebrow">INDEXED</span>
          <h2 id="service-explorer-title">{labels.services}</h2>
        </div>
        {jurisdiction && <span className="tiny-jurisdiction">{jurisdiction}</span>}
      </div>
      <form
        className="service-search"
        onSubmit={(event: FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          void refresh(query);
        }}
      >
        <input
          value={query}
          onChange={(event: ChangeEvent<HTMLInputElement>) => setQuery(event.target.value)}
          placeholder={labels.serviceSearch}
          aria-label={labels.serviceSearch}
          dir={language === "ar" ? "rtl" : "ltr"}
        />
        <button type="submit">{labels.search}</button>
      </form>

      <div className="service-list" aria-live="polite">
        {loading && <div className="skeleton-stack" aria-label={labels.checking}><i /><i /><i /></div>}
        {!loading && error && <p className="panel-error">{error}</p>}
        {!loading && !error && orderedServices.length === 0 && (
          <p className="empty-panel">{labels.noServices}</p>
        )}
        {!loading && !error && orderedServices.map((service) => (
          <article className="service-card" key={service.id} dir={containsArabic(service.service_name) ? "rtl" : "ltr"}>
            <div className="service-card-topline">
              <span>{service.category ?? "Service"}</span>
              <span>{service.jurisdiction}</span>
            </div>
            <h3>{service.service_name}</h3>
            {service.description && <p>{service.description}</p>}
            <div className="service-authority">{service.authority}</div>
            <a href={service.official_url} target="_blank" rel="noreferrer noopener">
              {labels.openOfficial} ↗
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}
