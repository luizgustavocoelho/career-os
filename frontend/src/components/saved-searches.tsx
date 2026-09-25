"use client";
import { useEffect, useState } from "react";
import { api, post, put, dateTime } from "@/lib/api";
import { ErrorBox, Field, useLoad } from "@/components/ui";
import { MODES, SENIORITIES } from "@/lib/types";
type Search = {
  id: string;
  name: string;
  keywords: string[];
  location: string;
  work_models: string[];
  seniority: string;
  salary_min: number | null;
  providers: string[];
  enabled: boolean;
  cadence_hours: number | null;
  last_status: string | null;
  last_error: string | null;
  next_run_at: string | null;
  last_result: {
    found: number;
    new: number;
    deduplicated: number;
    filtered: number;
  } | null;
};
const initial = {
  name: "",
  keywords: [""],
  location: "",
  work_models: [] as string[],
  seniority: "unknown",
  salary_min: null as number | null,
  providers: ["jooble"],
  enabled: true,
  cadence_hours: null as number | null,
};
const STATUS: Record<string, string> = {
  pending: "Na fila",
  running: "Em execução",
  completed: "Concluída",
  failed: "Falhou",
  cancelled: "Cancelada",
};
export function SavedSearches() {
  const searches = useLoad<Search[]>("/saved-searches");
  const providers =
    useLoad<{ id: string; configured: boolean; region?: string }[]>(
      "/providers",
    );
  const [draft, setDraft] = useState(initial);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const reload = searches.reload;
  useEffect(() => {
    const timer = setInterval(reload, 10000);
    return () => clearInterval(timer);
  }, [reload]);
  async function action(run: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await run();
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel saved-searches">
      <h3>Buscas salvas</h3>
      <p>
        Busque pela API oficial Jooble ou filtre as empresas Greenhouse/Lever
        cadastradas em Configurações. Resultados sem modalidade ou salário
        permanecem para revisão.
      </p>
      <ErrorBox message={error || searches.error || providers.error} />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          action(async () => {
            if (editing) await put(`/saved-searches/${editing}`, draft);
            else await post("/saved-searches", draft);
            setDraft(initial);
            setEditing(null);
          });
        }}
      >
        <div className="form-grid">
          <Field label="Nome da busca">
            <input
              required
              maxLength={160}
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field
            label="Termos de busca"
            hint="Até três variações, uma por linha."
          >
            <textarea
              required
              rows={3}
              value={draft.keywords.join("\n")}
              onChange={(e) =>
                setDraft({ ...draft, keywords: e.target.value.split("\n") })
              }
            />
          </Field>
          <Field label="Localização da busca">
            <input
              maxLength={240}
              value={draft.location}
              onChange={(e) => setDraft({ ...draft, location: e.target.value })}
            />
          </Field>
          <Field label="Frequência">
            <select
              value={draft.cadence_hours || ""}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  cadence_hours: e.target.value ? Number(e.target.value) : null,
                })
              }
            >
              <option value="">Somente manual</option>
              {[12, 24, 48, 168].map((h) => (
                <option key={h} value={h}>
                  A cada {h} horas
                </option>
              ))}
            </select>
          </Field>
          <Field label="Senioridade da busca">
            <select
              value={draft.seniority}
              onChange={(e) =>
                setDraft({ ...draft, seniority: e.target.value })
              }
            >
              {Object.entries(SENIORITIES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Salário mínimo mensal BRL"
            hint="Filtro aplicado somente quando moeda e período são conhecidos; Jooble não informa esses dados estruturados."
          >
            <input
              type="number"
              min={0}
              value={draft.salary_min ?? ""}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  salary_min: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </Field>
        </div>
        <fieldset>
          <legend>Modalidades desejadas</legend>
          {Object.entries(MODES)
            .filter(([k]) => k !== "unknown")
            .map(([k, v]) => (
              <label className="checkbox-inline" key={k}>
                <input
                  type="checkbox"
                  checked={draft.work_models.includes(k)}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      work_models: e.target.checked
                        ? [...draft.work_models, k]
                        : draft.work_models.filter((x) => x !== k),
                    })
                  }
                />
                {v}
              </label>
            ))}
        </fieldset>
        <fieldset>
          <legend>Providers da busca</legend>
          {providers.data?.map((p) => (
            <label key={p.id} className="checkbox-inline">
              <input
                type="checkbox"
                checked={draft.providers.includes(p.id)}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    providers: e.target.checked
                      ? [...draft.providers, p.id]
                      : draft.providers.filter((x) => x !== p.id),
                  })
                }
              />
              {p.id}
              {!p.configured ? " — chave necessária" : ""}
              {p.region ? ` (${p.region})` : ""}
            </label>
          ))}
        </fieldset>
        <label className="checkbox-inline">
          <input
            type="checkbox"
            checked={draft.enabled}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
          />
          Busca ativa
        </label>
        <div className="button-row">
          <button
            className="button primary"
            disabled={busy || !draft.providers.length}
          >
            {editing ? "Salvar alterações da busca" : "Salvar busca"}
          </button>
          {editing && (
            <button
              type="button"
              className="button"
              onClick={() => {
                setEditing(null);
                setDraft(initial);
              }}
            >
              Cancelar edição
            </button>
          )}
        </div>
      </form>
      {searches.data?.map((s) => (
        <div className="panel" key={s.id}>
          <h4>{s.name}</h4>
          <p>
            {s.keywords.join(" · ")} — {s.location || "Todas as localidades"}
          </p>
          <p>
            {s.enabled ? "Ativa" : "Desativada"} ·{" "}
            {(s.last_status && STATUS[s.last_status]) || "Ainda não executada"}{" "}
            · Próxima: {s.next_run_at ? dateTime(s.next_run_at) : "Manual"}
          </p>
          {s.last_result && (
            <p>
              {s.last_result.found} encontradas · {s.last_result.new} novas ·{" "}
              {s.last_result.deduplicated} já existentes ·{" "}
              {s.last_result.filtered} fora dos filtros
            </p>
          )}
          {s.last_error && <p role="status">{s.last_error}</p>}
          <div className="button-row">
            <button
              className="button"
              disabled={busy || !s.enabled}
              onClick={() => action(() => post(`/saved-searches/${s.id}/run`))}
            >
              Executar busca
            </button>
            <button
              className="button"
              disabled={busy}
              onClick={() => {
                setEditing(s.id);
                setDraft({
                  name: s.name,
                  keywords: s.keywords,
                  location: s.location,
                  work_models: s.work_models,
                  seniority: s.seniority,
                  salary_min: s.salary_min,
                  providers: s.providers,
                  enabled: s.enabled,
                  cadence_hours: s.cadence_hours,
                });
              }}
            >
              Editar busca
            </button>
            <button
              className="button"
              disabled={busy}
              onClick={() => {
                if (
                  confirm("Remover busca? Vagas e histórico serão preservados.")
                )
                  action(() =>
                    api(`/saved-searches/${s.id}`, { method: "DELETE" }),
                  );
              }}
            >
              Remover busca
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}
