"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { DiagnosticsPanel } from "@/components/diagnostics";
import { RefreshCw } from "lucide-react";
import { api, put, dateTime, post } from "@/lib/api";
import { Badge, ErrorBox, Field, Heading, useLoad } from "@/components/ui";
type Source = {
  enabled: boolean;
  id: string;
  provider: string;
  board: string;
  last_synced_at: string | null;
};
type Task = {
  id: string;
  kind: string;
  status: string;
  attempts: number;
  error: string | null;
  result: { processed: number } | null;
};
export default function Settings() {
  const sources = useLoad<Source[]>("/sources");
  const tasks = useLoad<Task[]>("/tasks");
  const status = useLoad<{
    configured: boolean;
    model: string;
    daily_limit: number;
    usage: { calls: number; tokens: number; failed: number };
  }>("/ai/status");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = tasks.data?.some((t) =>
    ["pending", "running"].includes(t.status),
  );
  const reloadTasks = tasks.reload;
  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(() => reloadTasks(), 10000);
    return () => clearInterval(timer);
  }, [pending, reloadTasks]);
  return (
    <>
      <Heading
        eyebrow="SEU WORKSPACE, DO SEU JEITO"
        title="Configurações"
        description="Fontes públicas, execução de tarefas e uso do provedor de inteligência artificial."
      />
      <ErrorBox
        message={error || sources.error || tasks.error || status.error}
      />
      <DiagnosticsPanel />
      <div className="settings-grid">
        <section className="panel">
          <h3>Fontes de oportunidades</h3>
          <p>
            Adicione o identificador público da empresa no Greenhouse ou Lever.
            A sincronização importa vagas reais e deduplica os registros.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const f = new FormData(form);
              setBusy(true);
              setError("");
              try {
                await post("/sources", {
                  provider: f.get("provider"),
                  board: f.get("board"),
                });
                await sources.reload();
                form.reset();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="form-grid">
              <Field label="Provedor">
                <select name="provider">
                  <option value="greenhouse">Greenhouse</option>
                  <option value="lever">Lever</option>
                </select>
              </Field>
              <Field label="Identificador da empresa">
                <input
                  name="board"
                  pattern="[a-zA-Z0-9_-]+"
                  required
                  placeholder="empresa"
                />
              </Field>
            </div>
            <button className="button primary" disabled={busy}>
              Adicionar fonte
            </button>
          </form>
          {sources.data?.map((s) => (
            <div className="source-row" key={s.id}>
              <div>
                <b>{s.board}</b>
                <small>
                  {s.provider} ·{" "}
                  {s.last_synced_at
                    ? dateTime(s.last_synced_at)
                    : "Ainda não sincronizada"}
                </small>
              </div>
              <button
                className="button"
                disabled={busy || !s.enabled}
                onClick={async () => {
                  setError("");
                  try {
                    await post(`/sources/${s.id}/sync`);
                    tasks.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                <RefreshCw size={15} />
                Sincronizar
              </button>
              <button
                className="button"
                onClick={async () => {
                  try {
                    await put(`/sources/${s.id}`, {
                      provider: s.provider,
                      board: s.board,
                      enabled: !s.enabled,
                    });
                    await sources.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                {s.enabled ? "Desativar" : "Ativar"}
              </button>
              <button
                className="button"
                onClick={async () => {
                  const board = prompt("Identificador da empresa", s.board);
                  if (!board) return;
                  try {
                    await put(`/sources/${s.id}`, {
                      provider: s.provider,
                      board,
                      enabled: s.enabled,
                    });
                    await sources.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Editar
              </button>
              <button
                className="button"
                onClick={async () => {
                  if (
                    !confirm(
                      "Remover fonte? As vagas importadas serão preservadas.",
                    )
                  )
                    return;
                  try {
                    await api(`/sources/${s.id}`, { method: "DELETE" });
                    await sources.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Remover
              </button>
            </div>
          ))}
        </section>
        <section className="panel">
          <h3>Inteligência artificial</h3>
          {status.data && (
            <>
              <Badge tone={status.data.configured ? "green" : "orange"}>
                {status.data.configured
                  ? "Provedor configurado"
                  : "Chave não configurada"}
              </Badge>
              <dl className="definition-list">
                <dt>Modelo</dt>
                <dd>{status.data.model}</dd>
                <dt>Limite diário</dt>
                <dd>{status.data.daily_limit} chamadas</dd>
                <dt>Últimos 30 dias</dt>
                <dd>
                  {status.data.usage.calls} chamadas ·{" "}
                  {status.data.usage.tokens.toLocaleString("pt-BR")} tokens
                </dd>
                <dt>Falhas</dt>
                <dd>{status.data.usage.failed}</dd>
              </dl>
              <p>
                Configure OPENAI_API_KEY e AI_MODEL no arquivo .env da raiz do
                projeto. As credenciais permanecem no servidor.
              </p>
              <p>
                Respostas idênticas reutilizam cache. O consumo em dinheiro
                depende da tabela de preços do provedor; consulte o painel da
                sua conta.
              </p>
              <Link className="text-link" href="/profile">
                Gerenciar consentimento e regras de follow-up →
              </Link>
            </>
          )}
        </section>
      </div>
      <section className="panel">
        <div className="section-heading">
          <h3>Tarefas em segundo plano</h3>
          <button className="button" onClick={() => tasks.reload()}>
            <RefreshCw size={15} />
            Atualizar
          </button>
        </div>
        <p className="muted">
          O processo worker precisa estar ativo. Tarefas sobrevivem a reinícios
          e têm até três tentativas.
        </p>
        {tasks.data?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tarefa</th>
                  <th>Status</th>
                  <th>Tentativas</th>
                  <th>Resultado</th>
                </tr>
              </thead>
              <tbody>
                {tasks.data.map((t) => (
                  <tr key={t.id}>
                    <td>
                      {t.kind === "sync"
                        ? "Sincronizar vagas"
                        : t.kind === "search"
                          ? "Buscar oportunidades"
                          : "Recalcular scores"}
                    </td>
                    <td>
                      <Badge
                        tone={
                          t.status === "completed"
                            ? "green"
                            : t.status === "failed"
                              ? "orange"
                              : ""
                        }
                      >
                        {
                          (
                            {
                              pending: "Na fila",
                              running: "Executando",
                              completed: "Concluída",
                              cancelled: "Cancelada",
                              failed: "Falhou",
                            } as Record<string, string>
                          )[t.status]
                        }
                      </Badge>
                    </td>
                    <td>{t.attempts}</td>
                    <td>
                      {t.error ||
                        (t.result
                          ? `${t.result.processed} registro(s) processado(s)`
                          : "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Nenhuma tarefa registrada.</p>
        )}
      </section>
    </>
  );
}
