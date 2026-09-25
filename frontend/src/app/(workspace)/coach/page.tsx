"use client";
import { useEffect, useState } from "react";
import { Plus, Send, Sparkles } from "lucide-react";
import { api, post } from "@/lib/api";
import { Advice } from "@/lib/types";
import { Badge, ErrorBox, Heading, useLoad } from "@/components/ui";
type Conversation = { id: string; title: string; job_id: string | null };
type Message = { role: string; body: string };
export default function Coach() {
  const conv = useLoad<Conversation[]>("/coach/conversations");
  const status = useLoad<{ configured: boolean; model: string }>("/ai/status");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [id, setId] = useState<string | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const j = new URLSearchParams(window.location.search).get("job");
    if (j)
      api<{ id: string }>(`/jobs/${j}`)
        .then((v) => setJob(v.id))
        .catch((e) => setError(e.message));
  }, []);
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setBusy(true);
    setError("");
    try {
      const reply = await post<Advice & { conversation_id: string }>("/coach", {
        body: input,
        conversation_id: id,
        job_id: job,
      });
      setMessages([
        ...messages,
        { role: "user", body: input },
        { role: "assistant", body: reply.body },
      ]);
      setId(reply.conversation_id);
      setInput("");
      conv.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="UM PONTO DE VISTA COM CONTEXTO"
        title="Career Coach"
        description="Converse sobre sua busca usando seu Career DNA, evidências e histórico real."
      >
        <Badge tone="purple">
          <Sparkles size={13} />
          {job ? "Contexto da vaga selecionada" : "Contexto do seu perfil"}
        </Badge>
      </Heading>
      <div className="coach-layout">
        <aside className="panel conversations">
          <button
            className="button full"
            onClick={() => {
              setId(null);
              setMessages([]);
            }}
          >
            <Plus size={16} />
            Nova conversa
          </button>
          {conv.data?.map((c) => (
            <button
              key={c.id}
              className={id === c.id ? "active" : ""}
              onClick={async () => {
                try {
                  setMessages(
                    await api<Message[]>(`/coach/conversations/${c.id}`),
                  );
                  setId(c.id);
                  setJob(c.job_id);
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              {c.title}
            </button>
          ))}
        </aside>
        <section className="panel coach-panel">
          {status.data && !status.data.configured && (
            <div className="notice">
              O Career Coach precisa de uma chave de API. Configure
              OPENAI_API_KEY no .env da raiz, reinicie a API e autorize o uso de
              IA no Career DNA. Nenhuma resposta externa é simulada.
            </div>
          )}
          {id && (
            <div className="button-row">
              <button
                className="button"
                disabled={busy}
                onClick={async () => {
                  const title = prompt(
                    "Nome da conversa",
                    conv.data?.find((c) => c.id === id)?.title,
                  );
                  if (!title) return;
                  try {
                    await api(`/coach/conversations/${id}`, {
                      method: "PATCH",
                      body: JSON.stringify({ title }),
                    });
                    await conv.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Renomear conversa
              </button>
              <button
                className="button"
                disabled={busy}
                onClick={async () => {
                  if (!confirm("Excluir esta conversa e suas mensagens?"))
                    return;
                  try {
                    await api(`/coach/conversations/${id}`, {
                      method: "DELETE",
                    });
                    setId(null);
                    setMessages([]);
                    await conv.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Excluir conversa
              </button>
            </div>
          )}
          <div className="chat-messages">
            {messages.length ? (
              messages.map((m, i) => (
                <div key={i} className={`chat-message ${m.role}`}>
                  <span className="chat-avatar">
                    {m.role === "assistant" ? <Sparkles size={17} /> : "Eu"}
                  </span>
                  <div>
                    <small>
                      {m.role === "assistant" ? "Career Coach" : "Você"}
                    </small>
                    <div className="prose-text">{m.body}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="coach-empty">
                <div className="coach-symbol">
                  <Sparkles size={30} />
                </div>
                <h2>Vamos pensar no próximo passo.</h2>
                <p>
                  Seu contexto é o ponto de partida. Suas decisões continuam
                  sendo suas.
                </p>
                <div className="suggestions">
                  {[
                    "O que devo fazer hoje?",
                    "Qual é meu principal gap?",
                    "Como apresentar meus projetos em uma entrevista?",
                    "Simule uma entrevista comigo, uma pergunta por vez.",
                  ].map((q) => (
                    <button key={q} onClick={() => setInput(q)}>
                      {q} ↗
                    </button>
                  ))}
                </div>
              </div>
            )}
            {busy && (
              <div className="chat-message">
                <span className="loading-dots">Consultando seu contexto…</span>
              </div>
            )}
          </div>
          <ErrorBox message={error || conv.error} />
          <form className="chat-input" onSubmit={send}>
            <textarea
              aria-label="Pergunta para o Career Coach"
              rows={2}
              maxLength={6000}
              placeholder="O que você gostaria de entender melhor?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button
              aria-label="Enviar pergunta"
              className="button primary"
              disabled={busy || !input.trim() || !status.data?.configured}
            >
              <Send size={18} />
            </button>
          </form>
          <small className="muted chat-disclaimer">
            A IA pode interpretar informações incorretamente. Confira fatos e
            rascunhos antes de usar.
          </small>
        </section>
      </div>
    </>
  );
}
