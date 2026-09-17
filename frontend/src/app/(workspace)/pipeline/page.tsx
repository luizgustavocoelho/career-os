"use client";
import Link from "next/link";
import { useState } from "react";
import { GripVertical, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Job, JobPage, STATES } from "@/lib/types";
import { ErrorBox, Heading, Loading, Score, useLoad } from "@/components/ui";
export default function Pipeline() {
  const [page, setPage] = useState(1);
  const { data, error, reload } = useLoad<JobPage>(
    `/jobs?per_page=60&page=${page}`,
  );
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  async function move(job: Job, status: string) {
    if (busy || job.application.status === status) return;
    setBusy(true);
    setFailure("");
    try {
      await api(`/applications/${job.application.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, version: job.application.version }),
      });
      await reload();
    } catch (e) {
      setFailure((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="CADA PASSO CONTA"
        title="Suas candidaturas"
        description="Arraste os cartões ou use o seletor de etapa. Cada movimento fica na timeline."
      >
        <Link className="button primary" href="/radar/new">
          <Plus size={16} />
          Adicionar oportunidade
        </Link>
      </Heading>
      <ErrorBox message={failure || error} />
      <div className="kanban-caption">
        <span>
          {data?.total || 0} oportunidades · {data?.items.length || 0} nesta
          página
        </span>
        <span>Deslize horizontalmente para ver todas as etapas →</span>
      </div>
      {!data ? (
        <Loading />
      ) : (
        <div className="kanban">
          {Object.entries(STATES).map(([status, label]) => (
            <section
              className={`kanban-column ${["offer", "hired"].includes(status) ? "success" : ""}`}
              key={status}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const job = data.items.find(
                  (j) => j.id === e.dataTransfer.getData("text/plain"),
                );
                if (job) move(job, status);
              }}
            >
              <div className="kanban-heading">
                <span className="status-dot" />
                <h3>{label}</h3>
                <span>
                  {
                    data.items.filter((j) => j.application.status === status)
                      .length
                  }
                </span>
              </div>
              {data.items
                .filter((j) => j.application.status === status)
                .map((j) => (
                  <article
                    className="kanban-card"
                    draggable={!busy}
                    onDragStart={(e) =>
                      e.dataTransfer.setData("text/plain", j.id)
                    }
                    key={j.id}
                  >
                    <div className="section-heading">
                      <span className="muted">{j.company}</span>
                      <GripVertical size={16} />
                    </div>
                    <Link href={`/jobs/${j.id}`}>{j.title}</Link>
                    <div className="kanban-card-footer">
                      <small>{j.location || "Local não informado"}</small>
                      <Score small value={j.score} />
                    </div>
                    <select
                      aria-label={`Etapa de ${j.title}`}
                      value={status}
                      disabled={busy}
                      onChange={(e) => move(j, e.target.value)}
                    >
                      {Object.entries(STATES).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </article>
                ))}
              {!data.items.some((j) => j.application.status === status) && (
                <div className="kanban-empty">
                  Arraste uma oportunidade para cá
                </div>
              )}
            </section>
          ))}
        </div>
      )}
      <div className="pagination">
        <button
          className="button"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Anterior
        </button>
        <span>
          Página {page} de {Math.max(1, Math.ceil((data?.total || 0) / 60))}
        </span>
        <button
          className="button"
          disabled={page * 60 >= (data?.total || 0)}
          onClick={() => setPage(page + 1)}
        >
          Próxima
        </button>
      </div>
    </>
  );
}
