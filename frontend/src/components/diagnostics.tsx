"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { post, dateTime } from "@/lib/api";
import { ErrorBox, useLoad } from "@/components/ui";
export function DashboardActions() {
  const { data, error } = useLoad<{
    as_of: string;
    new_since_visit: number;
    failed_tasks: number;
    recent: {
      id: string;
      title: string;
      company: string;
      classification: string | null;
    }[];
  }>("/dashboard/actions");
  const [visitError, setVisitError] = useState("");
  useEffect(() => {
    if (data)
      post("/dashboard/visited", { as_of: data.as_of }).catch((e) =>
        setVisitError(e.message),
      );
  }, [data]);
  return (
    <section className="panel">
      <h3>Desde sua última visita</h3>
      <ErrorBox message={error || visitError} />
      {data && (
        <>
          <p>
            {data.new_since_visit} nova(s) oportunidade(s).{" "}
            <Link href="/radar">Revisar Radar →</Link>
          </p>
          {data.recent.map((j) => (
            <p key={j.id}>
              <Link href={`/jobs/${j.id}`}>
                {j.title} — {j.company}
              </Link>
              {j.classification === "high" ? " · Prioridade alta" : ""}
            </p>
          ))}
          {!!data.failed_tasks && (
            <p>
              <Link href="/settings">
                Revisar {data.failed_tasks} tarefa(s) com falha →
              </Link>
            </p>
          )}
          <Link className="button" href="/radar">
            Configurar buscas automáticas
          </Link>
        </>
      )}
    </section>
  );
}
type Diagnostics = {
  version: string;
  environment: string;
  database: string;
  worker: { active: boolean; last_activity: string | null };
  providers: { id: string; configured: boolean }[];
  sources: {
    id: string;
    board: string;
    last_synced_at: string | null;
    last_error: string | null;
  }[];
  searches: {
    id: string;
    name: string;
    next_run_at: string | null;
    last_error: string | null;
  }[];
};
export function DiagnosticsPanel() {
  const { data, error, reload } = useLoad<Diagnostics>("/diagnostics");
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Diagnóstico</h3>
        <button className="button" onClick={reload}>
          Atualizar diagnóstico
        </button>
      </div>
      <ErrorBox message={error} />
      {data && (
        <>
          <p>
            CareerOS {data.version} · {data.environment} · Banco:{" "}
            {data.database}
          </p>
          <p>
            Worker: {data.worker.active ? "Ativo" : "Sem atividade recente"} ·{" "}
            {data.worker.last_activity
              ? dateTime(data.worker.last_activity)
              : "Ainda não registrado"}
          </p>
          {data.providers.map((p) => (
            <p key={p.id}>
              {p.id}: {p.configured ? "Configurado" : "Credencial necessária"}
            </p>
          ))}
          {data.sources.map((s) => (
            <p key={s.id}>
              {s.board} · Última sincronização:{" "}
              {s.last_synced_at
                ? dateTime(s.last_synced_at)
                : "Ainda não executada"}
              {s.last_error ? ` · ${s.last_error}` : ""}
            </p>
          ))}
          {data.searches.map((s) => (
            <p key={s.id}>
              {s.name} · Próxima execução:{" "}
              {s.next_run_at ? dateTime(s.next_run_at) : "Manual/desativada"}
              {s.last_error ? ` · ${s.last_error}` : ""}
            </p>
          ))}
        </>
      )}
      <a className="button" href="/api/export">
        Exportar meus dados (ZIP)
      </a>
    </section>
  );
}
