"use client";
import Link from "next/link";
import { SavedSearches } from "@/components/saved-searches";
import { useState } from "react";
import { ListFilter, Plus, Search } from "lucide-react";
import { JobCard } from "@/components/job-card";
import {
  Empty,
  ErrorBox,
  Field,
  Heading,
  Loading,
  useLoad,
} from "@/components/ui";
import { JobPage, MODES, SENIORITIES, STATES } from "@/lib/types";
export default function Radar() {
  const [filters, setFilters] = useState<Record<string, string>>({
    q: "",
    sort: "recent",
  });
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState(false);
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v),
  );
  params.set("page", String(page));
  const { data, error, loading, reload } = useLoad<JobPage>(`/jobs?${params}`);
  const set = (key: string, value: string) => {
    setFilters({ ...filters, [key]: value });
    setPage(1);
  };
  return (
    <>
      <Heading
        eyebrow="OPORTUNIDADES COM CONTEXTO"
        title="Opportunity Radar"
        description="Encontre o que faz sentido. Escolha onde vale investir sua energia."
      >
        <Link className="button" href="/settings">
          Gerenciar fontes
        </Link>
        <Link href="/radar/new" className="button primary">
          <Plus size={17} />
          Adicionar vaga
        </Link>
      </Heading>
      <details className="panel">
        <summary>Gerenciar buscas automáticas</summary>
        <SavedSearches />
      </details>
      <div className="panel filter-panel">
        <div className="filter-main">
          <div className="input-icon">
            <Search size={17} />
            <input
              aria-label="Buscar vagas"
              placeholder="Cargo, empresa ou palavra-chave"
              value={filters.q}
              onChange={(e) => set("q", e.target.value)}
            />
          </div>
          <select
            aria-label="Ordenação"
            value={filters.sort}
            onChange={(e) => set("sort", e.target.value)}
          >
            <option value="recent">Mais recentes</option>
            <option value="score">Melhor match</option>
            <option value="salary">Maior salário</option>
            <option value="priority">Prioridade</option>
          </select>
          <button
            className={`button ${expanded ? "selected" : ""}`}
            onClick={() => setExpanded(!expanded)}
          >
            <ListFilter size={17} />
            Filtros
          </button>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={filters.favorite === "true"}
              onChange={(e) => set("favorite", e.target.checked ? "true" : "")}
            />
            Favoritos
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={filters.archived === "true"}
              onChange={(e) => set("archived", e.target.checked ? "true" : "")}
            />
            Arquivadas
          </label>
        </div>
        {expanded && (
          <div className="form-grid filters-expanded">
            <Field label="Empresa">
              <input
                value={filters.company || ""}
                onChange={(e) => set("company", e.target.value)}
              />
            </Field>
            <Field label="Localização">
              <input
                value={filters.location || ""}
                onChange={(e) => set("location", e.target.value)}
              />
            </Field>
            <Field label="Modelo de trabalho">
              <select
                value={filters.work_model || ""}
                onChange={(e) => set("work_model", e.target.value)}
              >
                <option value="">Todos</option>
                {Object.entries(MODES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Senioridade">
              <select
                value={filters.seniority || ""}
                onChange={(e) => set("seniority", e.target.value)}
              >
                <option value="">Todas</option>
                {Object.entries(SENIORITIES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Score mínimo">
              <input
                type="number"
                min="0"
                max="100"
                value={filters.min_score || ""}
                onChange={(e) => set("min_score", e.target.value)}
              />
            </Field>
            <Field label="Salário máximo da vaga a partir de">
              <input
                type="number"
                min="0"
                value={filters.min_salary || ""}
                onChange={(e) => set("min_salary", e.target.value)}
              />
            </Field>
            <Field label="Skill">
              <input
                value={filters.skill || ""}
                onChange={(e) => set("skill", e.target.value)}
              />
            </Field>
            <Field label="Fonte">
              <input
                value={filters.source || ""}
                placeholder="manual, greenhouse:empresa"
                onChange={(e) => set("source", e.target.value)}
              />
            </Field>
            <Field label="Adicionada a partir de">
              <input
                type="date"
                value={filters.since || ""}
                onChange={(e) => set("since", e.target.value)}
              />
            </Field>
            <Field label="Etapa">
              <select
                value={filters.status || ""}
                onChange={(e) => set("status", e.target.value)}
              >
                <option value="">Todas</option>
                {Object.entries(STATES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <button
              className="text-button"
              onClick={() => {
                setFilters({ q: "", sort: "recent" });
                setPage(1);
              }}
            >
              Limpar filtros
            </button>
          </div>
        )}
      </div>
      <ErrorBox message={error} />
      <div className="section-heading roomy">
        <span className="muted">{data?.total || 0} oportunidade(s)</span>
        <span className="mini-label">SEU RADAR, SUAS ESCOLHAS</span>
      </div>
      {loading && !data ? (
        <Loading />
      ) : data?.items.length ? (
        <div className="job-grid">
          {data.items.map((j) => (
            <JobCard key={j.id} job={j} onUpdate={reload} />
          ))}
        </div>
      ) : (
        <div className="panel">
          <Empty
            title="Nenhuma vaga por aqui"
            description="Adicione uma oportunidade ou ajuste os filtros da sua busca."
            href="/radar/new"
            action="Adicionar oportunidade"
          />
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
          Página {page} de {Math.max(1, Math.ceil((data?.total || 0) / 20))}
        </span>
        <button
          className="button"
          disabled={page * 20 >= (data?.total || 0)}
          onClick={() => setPage(page + 1)}
        >
          Próxima
        </button>
      </div>
    </>
  );
}
