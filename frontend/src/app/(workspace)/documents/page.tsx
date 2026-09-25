"use client";
import { useState } from "react";
import Link from "next/link";
import { Download, FileText, Plus, Sparkles, Upload } from "lucide-react";
import { api, dateTime, post } from "@/lib/api";
import { Document } from "@/lib/types";
import {
  Badge,
  Empty,
  ErrorBox,
  Field,
  Heading,
  useLoad,
} from "@/components/ui";
export default function Documents() {
  const { data, error, reload } = useLoad<Document[]>("/documents");
  const [current, setCurrent] = useState<Document | null>(null);
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [text, setText] = useState("");
  async function upload(file?: File) {
    if (!file) return;
    setBusy(true);
    setFailure("");
    try {
      const body = new FormData();
      body.append("file", file);
      const doc = await api<Document>("/documents/upload", {
        method: "POST",
        body,
      });
      setCurrent(doc);
      setText(doc.text);
      await reload();
    } catch (e) {
      setFailure((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function select(id: string) {
    setFailure("");
    try {
      const doc = await api<Document>(`/documents/${id}`);
      setCurrent(doc);
      setText(doc.text);
      setCreating(false);
    } catch (e) {
      setFailure((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        eyebrow="SUA HISTÓRIA, BEM DOCUMENTADA"
        title="Documentos"
        description="Currículos, versões e cartas. Sempre com informações que pertencem à sua trajetória."
      >
        <button
          className="button"
          onClick={() => {
            setCreating(true);
            setCurrent(null);
            setText("");
          }}
        >
          <Plus size={16} />
          Novo documento
        </button>
        <label className={`button primary ${busy ? "disabled" : ""}`}>
          <Upload size={16} />
          {busy ? "Processando…" : "Enviar currículo PDF"}
          <input
            className="sr-only"
            type="file"
            accept="application/pdf,.pdf"
            disabled={busy}
            onChange={(e) => {
              upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
      </Heading>
      <ErrorBox message={failure || error} />
      <div className="documents-layout">
        <section className="panel documents-list">
          {data?.length ? (
            data.map((d) => (
              <button
                key={d.id}
                className={`document-item ${current?.id === d.id ? "active" : ""}`}
                onClick={() => select(d.id)}
              >
                <span className="document-icon">
                  <FileText size={21} />
                </span>
                <span>
                  <b>{d.name}</b>
                  <small>{dateTime(d.created_at)}</small>
                </span>
                <Badge>
                  {d.kind === "resume"
                    ? "Currículo"
                    : d.kind === "cover_letter"
                      ? "Carta"
                      : "Nota"}
                </Badge>
              </button>
            ))
          ) : (
            <Empty
              title="Sua base de documentos"
              description="Envie um currículo PDF para extrair e revisar seu perfil."
            />
          )}
        </section>
        <section className="panel document-preview">
          {current ? (
            <>
              <div className="section-heading">
                <h3>{current.name}</h3>
                <a
                  className="button"
                  href={`/api/documents/${current.id}/download`}
                >
                  <Download size={15} />
                  Baixar
                </a>
              </div>
              <div className="button-row">
                {current.applications?.map((a) => (
                  <Link key={a.id} href={`/jobs/${a.job_id}`}>
                    Vinculado: {a.title}
                  </Link>
                ))}
                <button
                  className="button"
                  disabled={busy || !!current.applications?.length}
                  onClick={async () => {
                    if (
                      !confirm(
                        "Excluir esta vers�o? Documentos vinculados e vers�es com descendentes s�o protegidos.",
                      )
                    )
                      return;
                    try {
                      await api(`/documents/${current.id}`, {
                        method: "DELETE",
                      });
                      setCurrent(null);
                      await reload();
                    } catch (e) {
                      setFailure((e as Error).message);
                    }
                  }}
                >
                  Excluir vers�o n�o utilizada
                </button>
              </div>
              {current.extracted?.warnings.map((w, i) => (
                <div className="notice" key={i}>
                  {w}
                </div>
              ))}
              <div className="button-row">
                <button
                  className="button"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    setFailure("");
                    try {
                      setCurrent(
                        await post<Document>(
                          `/documents/${current.id}/extract`,
                        ),
                      );
                    } catch (e) {
                      setFailure((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <Sparkles size={16} />
                  Extrair perfil com IA
                </button>
                {current.extracted && (
                  <Link
                    className="button primary"
                    href={`/profile?document=${current.id}`}
                  >
                    Revisar no Career DNA →
                  </Link>
                )}
              </div>
              <Field
                label="Texto do documento"
                hint="Edite o texto e salve como uma nova versão. O arquivo original é preservado."
              >
                <textarea
                  rows={22}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </Field>
              <button
                className="button"
                disabled={busy || !text.trim()}
                onClick={async () => {
                  setBusy(true);
                  setFailure("");
                  try {
                    const doc = await post<Document>("/documents", {
                      name: current.name + " — revisão",
                      kind: current.kind,
                      text,
                      parent_id: current.id,
                    });
                    setCurrent(doc);
                    reload();
                  } catch (e) {
                    setFailure((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Salvar nova versão de texto
              </button>
            </>
          ) : creating ? (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                setBusy(true);
                setFailure("");
                try {
                  const doc = await post<Document>("/documents", {
                    name: f.get("name"),
                    kind: f.get("kind"),
                    text,
                  });
                  setCurrent(doc);
                  setCreating(false);
                  reload();
                } catch (e) {
                  setFailure((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <h3>Novo documento</h3>
              <Field label="Nome do documento">
                <input name="name" required />
              </Field>
              <Field label="Tipo">
                <select name="kind">
                  <option value="note">Nota</option>
                  <option value="cover_letter">Carta de apresentação</option>
                  <option value="resume">Currículo</option>
                </select>
              </Field>
              <Field label="Conteúdo">
                <textarea
                  required
                  rows={18}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </Field>
              <button className="button primary" disabled={busy}>
                Salvar documento
              </button>
            </form>
          ) : (
            <Empty
              title="Tudo o que conta a sua história"
              description="Selecione um documento para consultar, revisar a extração ou criar uma nova versão."
            />
          )}
        </section>
      </div>
    </>
  );
}
