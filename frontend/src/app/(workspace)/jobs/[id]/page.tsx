"use client";
import {
  MessageEditor,
  InterviewCard,
  AdviceView,
} from "@/components/application-tools";
import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Download,
  FileText,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
  Star,
} from "lucide-react";
import { api, dateTime, post, safeUrl } from "@/lib/api";
import {
  Advice,
  COMPONENTS,
  Document,
  JobDetail,
  MODES,
  PRIORITIES,
  STATES,
} from "@/lib/types";
import {
  Badge,
  Empty,
  ErrorBox,
  Field,
  Heading,
  Loading,
  Score,
  useLoad,
} from "@/components/ui";
export default function Workspace({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: j, error, reload } = useLoad<JobDetail>(`/jobs/${id}`);
  const docs = useLoad<Document[]>("/documents");
  const [tab, setTab] = useState("analysis");
  const [failure, setFailure] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [semantic, setSemantic] = useState<Advice | null>(null);
  async function act(fn: () => Promise<unknown>, message = "Alteração salva.") {
    setBusy(true);
    setFailure("");
    setNotice("");
    try {
      await fn();
      await reload();
      setNotice(message);
    } catch (e) {
      setFailure((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!j) return error ? <ErrorBox message={error} /> : <Loading />;
  const app = j.application;
  const a = j.analysis?.result;
  const root = `/applications/${app.id}`;
  return (
    <>
      <Link className="back-link" href="/radar">
        <ArrowLeft size={15} />
        Voltar ao radar
      </Link>
      <Heading
        eyebrow={j.company.toUpperCase()}
        title={j.title}
        description={`${j.location || "Local não informado"} · ${MODES[j.work_model]}`}
      >
        <button
          className="button"
          disabled={busy}
          onClick={() =>
            act(
              () => post(`/jobs/${id}/favorite`),
              j.favorite ? "Favorito removido." : "Vaga salva nos favoritos.",
            )
          }
        >
          <Star size={16} fill={j.favorite ? "currentColor" : "none"} />
          {j.favorite ? "Favorita" : "Favoritar"}
        </button>
        {safeUrl(j.url) && (
          <a
            className="button"
            href={safeUrl(j.url)}
            target="_blank"
            rel="noreferrer"
          >
            Vaga original
            <ArrowUpRight size={16} />
          </a>
        )}
        <Link className="button" href={`/radar/new?edit=${id}`}>
          Editar vaga
        </Link>
      </Heading>
      <ErrorBox message={failure || error} />
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      <div className="workspace-layout">
        <div className="workspace-main">
          <div className="tabs" role="tablist">
            {[
              ["analysis", "Análise"],
              ["messages", "Mensagens"],
              ["interviews", "Entrevistas"],
              ["notes", "Notas e contatos"],
              ["timeline", "Timeline"],
            ].map(([key, label]) => (
              <button
                key={key}
                role="tab"
                aria-selected={tab === key}
                className={tab === key ? "active" : ""}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
          </div>
          {tab === "analysis" && (
            <div className="stack">
              {j.analysis_stale && (
                <div className="notice">
                  Seu perfil mudou. Recalcule o score para usar as informações
                  atuais.
                </div>
              )}
              <section className="panel">
                <div className="section-heading">
                  <div>
                    <h3>Opportunity Score</h3>
                    <p>Compatibilidade explicável, com base no seu perfil.</p>
                  </div>
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      act(
                        () => post(`/jobs/${id}/analyze`),
                        "Score recalculado.",
                      )
                    }
                  >
                    <RefreshCw size={15} />
                    Recalcular
                  </button>
                </div>
                {a ? (
                  <>
                    <div className="score-summary">
                      <Score value={a.score} />
                      <div>
                        <Badge
                          tone={a.classification === "high" ? "green" : ""}
                        >
                          {PRIORITIES[a.classification]}
                        </Badge>
                        <p>{a.reason}</p>
                        <small>
                          Cobertura da informação: {a.coverage}% · algoritmo{" "}
                          {a.algorithm}
                        </small>
                      </div>
                    </div>
                    <div className="component-grid">
                      {a.components.map((c) => (
                        <div
                          key={c.name}
                          className="score-component"
                          title={c.explanation}
                        >
                          <div>
                            <span>{COMPONENTS[c.name]}</span>
                            <b>
                              {c.score === null ? "Sem dados" : `${c.score}%`}
                            </b>
                          </div>
                          <div className="bar-track">
                            <span style={{ width: `${c.score || 0}%` }} />
                          </div>
                          <small>
                            {c.explanation} Peso: {c.weight}.
                          </small>
                        </div>
                      ))}
                    </div>
                    <details>
                      <summary>Como auditar esta análise</summary>
                      <p>
                        Dados ausentes são excluídos do cálculo; o peso dos
                        componentes conhecidos é normalizado. A classificação
                        considera a cobertura e os gaps obrigatórios.
                      </p>
                      <a
                        className="text-link"
                        href={`/api/analyses/${j.analysis!.id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir snapshot e componentes em JSON ↗
                      </a>
                    </details>
                  </>
                ) : (
                  <Empty
                    title="Pronta para analisar"
                    description="Calcule o score com o perfil que você cadastrou."
                  />
                )}
              </section>
              <section className="panel">
                <div className="section-heading">
                  <h3>Requisitos & evidências</h3>
                  <Badge>{a?.requirements.length || 0} requisitos</Badge>
                </div>
                {a?.requirements.map((r, i) => (
                  <div className="requirement-row" key={i}>
                    <div className={`requirement-icon ${r.status}`}>
                      <CheckCircle2 size={18} />
                    </div>
                    <div className="grow">
                      <div className="button-row">
                        <b>{r.skill}</b>
                        <Badge>
                          {r.mandatory ? "Obrigatório" : "Desejável"}
                        </Badge>
                        <Badge
                          tone={
                            r.status === "met"
                              ? "green"
                              : r.status === "missing"
                                ? "orange"
                                : ""
                          }
                        >
                          {r.status === "met"
                            ? "Com evidência"
                            : r.status === "partial"
                              ? "Parcial"
                              : "Não registrado"}
                        </Badge>
                      </div>
                      <p>{r.description}</p>
                      <small>{r.explanation}</small>
                      {r.evidence.map((e) => (
                        <div className="evidence-inline" key={e.id}>
                          <b>{e.title}</b>
                          <p>{e.description}</p>
                          {safeUrl(e.url) && (
                            <a
                              href={safeUrl(e.url)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Ver evidência ↗
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {!a?.requirements.length && (
                  <p className="muted">
                    Revise a vaga e adicione requisitos estruturados para obter
                    uma análise técnica.
                  </p>
                )}
              </section>
              <section className="panel">
                <div className="section-heading">
                  <h3>Análise contextual</h3>
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      act(
                        async () =>
                          setSemantic(
                            await post<Advice>(`/jobs/${id}/semantic`),
                          ),
                        "Análise contextual concluída.",
                      )
                    }
                  >
                    <Sparkles size={16} />
                    Analisar com IA
                  </button>
                </div>
                <p className="muted">
                  Interprete nuances de experiência e objetivos. A IA não altera
                  a composição do score.
                </p>
                {semantic && <AdviceView advice={semantic} />}
              </section>
              <section className="panel">
                <h3>Descrição da oportunidade</h3>
                <div className="prose-text">{j.description}</div>
              </section>
            </div>
          )}
          {tab === "messages" && (
            <div className="stack">
              <section className="panel">
                <h3>Recruiter Assistant</h3>
                <p>
                  Prepare uma mensagem com seu contexto real. Revise, edite e
                  copie antes de enviar.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    act(
                      () =>
                        post(`${root}/messages?ai=${f.get("ai") === "on"}`, {
                          kind: f.get("kind"),
                          instructions: f.get("instructions"),
                        }),
                      "Rascunho criado. Revise antes de copiar.",
                    );
                  }}
                >
                  <div className="form-grid">
                    <Field label="Tipo de mensagem">
                      <select name="kind">
                        {[
                          ["first_contact", "Primeiro contato"],
                          ["linkedin", "LinkedIn"],
                          ["email", "E-mail"],
                          ["application", "Candidatura"],
                          ["follow_up", "Follow-up"],
                          ["thanks", "Agradecimento pós-entrevista"],
                          ["reply", "Resposta a recrutador"],
                          ["interest", "Interesse em oportunidade"],
                          ["update", "Pedido de atualização"],
                        ].map(([k, v]) => (
                          <option key={k} value={k}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Contexto adicional (para IA)">
                      <input
                        name="instructions"
                        maxLength={3000}
                        placeholder="Ex.: responder à pergunta do recrutador…"
                      />
                    </Field>
                  </div>
                  <div className="button-row">
                    <label className="checkbox-inline">
                      <input name="ai" type="checkbox" />
                      Usar IA para personalizar
                    </label>
                    <button className="button primary" disabled={busy}>
                      <MessageSquare size={16} />
                      Gerar rascunho
                    </button>
                  </div>
                </form>
              </section>
              {j.messages.map((m) => (
                <MessageEditor
                  key={m.id + String(m.sent_at)}
                  message={m}
                  busy={busy}
                  act={act}
                />
              ))}
              {!j.messages.length && (
                <Empty
                  title="Sua próxima conversa começa aqui"
                  description="Escolha o objetivo da mensagem e crie um rascunho editável."
                />
              )}
            </div>
          )}
          {tab === "interviews" && (
            <div className="stack">
              <section className="panel">
                <h3>Agendar entrevista</h3>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    act(
                      () =>
                        post(`${root}/interviews`, {
                          title: f.get("title"),
                          scheduled_at: new Date(
                            String(f.get("scheduled_at")),
                          ).toISOString(),
                          kind: f.get("kind"),
                          notes: f.get("notes"),
                        }),
                      "Entrevista registrada.",
                    );
                  }}
                >
                  <div className="form-grid">
                    <Field label="Título da entrevista">
                      <input
                        name="title"
                        required
                        placeholder="Conversa com o time de dados"
                      />
                    </Field>
                    <Field label="Data e hora local">
                      <input
                        name="scheduled_at"
                        type="datetime-local"
                        required
                      />
                    </Field>
                    <Field label="Etapa">
                      <select name="kind">
                        <option value="hr">RH</option>
                        <option value="technical">Técnica</option>
                        <option value="case">Case / teste</option>
                        <option value="final">Final</option>
                      </select>
                    </Field>
                    <Field label="Link e observações">
                      <input name="notes" />
                    </Field>
                  </div>
                  <button className="button primary" disabled={busy}>
                    <CalendarDays size={16} />
                    Agendar entrevista
                  </button>
                </form>
              </section>
              {j.interviews.map((i) => (
                <InterviewCard
                  key={i.id + String(!!i.preparation)}
                  interview={i}
                  busy={busy}
                  act={act}
                />
              ))}
              <Link className="button" href={`/coach?job=${id}`}>
                Simular entrevista no Career Coach
                <Sparkles size={15} />
              </Link>
            </div>
          )}
          {tab === "notes" && (
            <div className="stack">
              <section className="panel">
                <h3>Notas pessoais</h3>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = e.currentTarget;
                    const f = new FormData(form);
                    act(async () => {
                      await post(`${root}/notes`, { body: f.get("body") });
                      form.reset();
                    });
                  }}
                >
                  <Field label="Nova nota">
                    <textarea
                      name="body"
                      required
                      rows={3}
                      placeholder="O que você quer lembrar sobre esta oportunidade?"
                    />
                  </Field>
                  <button className="button" disabled={busy}>
                    Salvar nota
                  </button>
                </form>
                {j.notes.map((n) => (
                  <div className="note" key={n.id}>
                    <small>{dateTime(n.created_at)}</small>
                    <p className="prose-text">{n.body}</p>
                  </div>
                ))}
              </section>
              <section className="panel">
                <h3>Contatos da oportunidade</h3>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = e.currentTarget;
                    const f = new FormData(form);
                    act(async () => {
                      await post(`${root}/contacts`, {
                        name: f.get("name"),
                        email: f.get("email") || null,
                        url: f.get("url") || null,
                        role: f.get("role"),
                      });
                      form.reset();
                    });
                  }}
                >
                  <div className="form-grid">
                    <Field label="Nome do contato">
                      <input name="name" required />
                    </Field>
                    <Field label="Cargo / função">
                      <input name="role" />
                    </Field>
                    <Field label="E-mail">
                      <input name="email" type="email" />
                    </Field>
                    <Field label="Perfil / URL">
                      <input name="url" type="url" />
                    </Field>
                  </div>
                  <button className="button" disabled={busy}>
                    Adicionar contato
                  </button>
                </form>
                {j.contacts.map((c) => (
                  <div className="note" key={c.id}>
                    <b>{c.name}</b>
                    <p>
                      {c.role} {c.email && `· ${c.email}`}
                    </p>
                    {safeUrl(c.url) && (
                      <a
                        href={safeUrl(c.url)}
                        target="_blank"
                        rel="noreferrer"
                        className="text-link"
                      >
                        Ver perfil ↗
                      </a>
                    )}
                  </div>
                ))}
              </section>
            </div>
          )}
          {tab === "timeline" && (
            <section className="panel">
              <h3>Uma história de cada passo</h3>
              <p className="muted">
                Alterações são registradas como eventos. Seu histórico é
                preservado.
              </p>
              <div className="timeline">
                {j.events.map((e) => (
                  <div className="timeline-event" key={e.id}>
                    <span className="timeline-dot" />
                    <small>{dateTime(e.created_at)}</small>
                    <b>{e.title}</b>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
        <aside className="workspace-aside">
          <section className="panel">
            <span className="eyebrow">SUA CANDIDATURA</span>
            <h3>Próximo movimento</h3>
            <Field label="Etapa do pipeline">
              <select
                value={app.status}
                disabled={busy}
                onChange={(e) => {
                  const status = e.target.value;
                  const rejection_reason =
                    status === "rejected"
                      ? prompt("Motivo informado (opcional):")
                      : null;
                  act(() =>
                    api(`${root}/status`, {
                      method: "PATCH",
                      body: JSON.stringify({
                        status,
                        version: app.version,
                        rejection_reason,
                      }),
                    }),
                  );
                }}
              >
                {Object.entries(STATES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            {["discovered", "saved", "analyzing", "preparing"].includes(
              app.status,
            ) && (
              <button
                className="button primary full"
                disabled={busy}
                onClick={() =>
                  act(
                    () =>
                      api(`${root}/status`, {
                        method: "PATCH",
                        body: JSON.stringify({
                          status: "applied",
                          version: app.version,
                        }),
                      }),
                    "Candidatura registrada. O follow-up foi agendado conforme suas preferências.",
                  )
                }
              >
                <Send size={15} />
                Já me candidatei
              </button>
            )}
            <p className="muted small-text">
              Registre aqui as ações que você realizou. O CareerOS não envia
              candidaturas.
            </p>
            <Link className="button full" href={`/coach?job=${id}`}>
              <Sparkles size={15} />
              Conversar sobre esta vaga
            </Link>
          </section>
          <section className="panel">
            <h3>Currículo da candidatura</h3>
            <Link className="button full" href={`/jobs/${id}/resume`}>
              Selecionar fatos e exportar currículo
            </Link>
            <Field label="Documento utilizado">
              <select
                value={app.resume_id || ""}
                disabled={busy}
                onChange={(e) => {
                  if (e.target.value)
                    act(() => post(`${root}/resume/${e.target.value}`));
                }}
              >
                <option value="">Selecione uma versão</option>
                {docs.data?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </Field>
            <button
              className="button full"
              disabled={busy}
              onClick={() =>
                act(
                  () => post(`${root}/resume`),
                  "Versão criada em Documentos, com fatos do seu perfil e skills relevantes em destaque.",
                )
              }
            >
              <FileText size={16} />
              Criar versão contextual
            </button>
            {app.resume_id && (
              <a
                className="text-link"
                href={`/api/documents/${app.resume_id}/download`}
              >
                <Download size={15} />
                Baixar currículo usado
              </a>
            )}
          </section>
          <section className="panel">
            <h3>Follow-ups</h3>
            {j.followups.map((f) => (
              <div className="follow-item" key={f.id}>
                <b>{dateTime(f.due_at)}</b>
                <Badge>
                  {
                    (
                      {
                        pending: "Pendente",
                        sent: "Enviado",
                        cancelled: "Cancelado",
                        replied: "Respondido",
                      } as Record<string, string>
                    )[f.status]
                  }
                </Badge>
                <div className="button-row">
                  {f.status === "pending" && (
                    <>
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() =>
                          act(
                            () => post(`/followups/${f.id}/sent`),
                            "Envio de follow-up registrado.",
                          )
                        }
                      >
                        Marcar enviado
                      </button>
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() =>
                          act(() => post(`/followups/${f.id}/cancelled`))
                        }
                      >
                        Cancelar
                      </button>
                    </>
                  )}
                  {["pending", "sent"].includes(f.status) && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        act(() => post(`/followups/${f.id}/replied`))
                      }
                    >
                      Recebi resposta
                    </button>
                  )}
                </div>
              </div>
            ))}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                act(() =>
                  post(`${root}/followups`, {
                    due_at: new Date(String(f.get("due_at"))).toISOString(),
                  }),
                );
              }}
            >
              <Field label="Próximo acompanhamento">
                <input name="due_at" type="datetime-local" required />
              </Field>
              <button className="button full" disabled={busy}>
                Agendar acompanhamento
              </button>
            </form>
            <button className="text-button" onClick={() => setTab("messages")}>
              Preparar mensagem de follow-up →
            </button>
          </section>
        </aside>
      </div>
    </>
  );
}
