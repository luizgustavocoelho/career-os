"use client";
import { useState } from "react";
import { Copy, Save, Sparkles } from "lucide-react";
import { dateTime, post, put } from "@/lib/api";
import { Advice, Draft, Interview } from "@/lib/types";
import { Badge, Field } from "@/components/ui";
export type Act = (
  fn: () => Promise<unknown>,
  message?: string,
) => Promise<void>;
export function MessageEditor({
  message: m,
  busy,
  act,
}: {
  message: Draft;
  busy: boolean;
  act: Act;
}) {
  const [text, setText] = useState(m.body);
  const [copied, setCopied] = useState(false);
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Rascunho · {dateTime(m.created_at)}</h3>
        <Badge tone={m.sent_at ? "green" : ""}>
          {m.sent_at ? "Envio registrado" : "Em edição"}
        </Badge>
      </div>
      <textarea
        aria-label="Mensagem editável"
        rows={10}
        value={text}
        disabled={!!m.sent_at}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="button-row">
        {!m.sent_at && (
          <button
            className="button"
            disabled={busy}
            onClick={() => act(() => put(`/messages/${m.id}`, { body: text }))}
          >
            <Save size={15} />
            Salvar edição
          </button>
        )}
        <button
          className="button"
          onClick={() =>
            act(async () => {
              await navigator.clipboard.writeText(text);
              setCopied(true);
            }, "Texto copiado. Revise no aplicativo em que fará o envio.")
          }
        >
          <Copy size={15} />
          {copied ? "Copiado" : "Copiar mensagem"}
        </button>
        {!m.sent_at && (
          <button
            className="button"
            disabled={busy}
            onClick={() =>
              act(async () => {
                await put(`/messages/${m.id}`, { body: text });
                await post(`/messages/${m.id}/sent`);
              }, "Envio registrado na timeline.")
            }
          >
            Marcar como enviada
          </button>
        )}
      </div>
    </section>
  );
}
export function InterviewCard({
  interview: i,
  busy,
  act,
}: {
  interview: Interview;
  busy: boolean;
  act: Act;
}) {
  const [feedback, setFeedback] = useState(i.feedback);
  const [notes, setNotes] = useState(i.notes);
  const [checklist, setChecklist] = useState(i.checklist);
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h3>{i.title}</h3>
          <p>{dateTime(i.scheduled_at)}</p>
        </div>
        <Badge>Interview Mission</Badge>
      </div>
      <div className="button-row">
        <button
          className="button"
          disabled={busy}
          onClick={() =>
            act(
              () => post(`/interviews/${i.id}/prepare`),
              "Roteiro gerado a partir da vaga e do perfil.",
            )
          }
        >
          Preparar roteiro
        </button>
        <button
          className="button"
          disabled={busy}
          onClick={() =>
            act(
              () => post(`/interviews/${i.id}/prepare?ai=true`),
              "Preparação com IA concluída.",
            )
          }
        >
          <Sparkles size={15} />
          Aprofundar com IA
        </button>
      </div>
      {i.preparation && <AdviceView advice={i.preparation} />}
      <div className="checklist">
        {[
          "Revisar a vaga",
          "Selecionar exemplos reais",
          "Preparar perguntas",
          "Conferir horário e link",
        ].map((c) => (
          <label key={c} className="checkbox-inline">
            <input
              type="checkbox"
              checked={checklist.includes(c)}
              onChange={(e) =>
                setChecklist(
                  e.target.checked
                    ? [...checklist, c]
                    : checklist.filter((x) => x !== c),
                )
              }
            />
            {c}
          </label>
        ))}
      </div>
      <Field label="Anotações da entrevista">
        <textarea
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Field>
      <Field label="Feedback após a entrevista">
        <textarea
          rows={3}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
      </Field>
      <button
        className="button"
        disabled={busy}
        onClick={() =>
          act(() => put(`/interviews/${i.id}`, { feedback, notes, checklist }))
        }
      >
        Salvar preparação e feedback
      </button>
    </section>
  );
}
export function AdviceView({ advice }: { advice: Advice }) {
  return (
    <div className="advice">
      <div className="prose-text">{advice.body}</div>
      {advice.citations?.length > 0 && (
        <details>
          <summary>Fontes usadas na resposta</summary>
          {advice.citations.map((c, i) => (
            <blockquote key={i}>
              <small>{c.source_id}</small>
              <p>{c.quote}</p>
            </blockquote>
          ))}
        </details>
      )}
      {advice.missing_information?.length > 0 && (
        <div className="notice">
          Informações a completar: {advice.missing_information.join("; ")}
        </div>
      )}
    </div>
  );
}
