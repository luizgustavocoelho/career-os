"use client";
import { use, useState } from "react";
import Link from "next/link";
import { post } from "@/lib/api";
import { Profile, JobDetail, Document } from "@/lib/types";
import { ErrorBox, Heading, useLoad } from "@/components/ui";
export default function ResumePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const job = useLoad<JobDetail>(`/jobs/${id}`);
  const profile = useLoad<Profile>("/profile");
  const [selected, setSelected] = useState<{
    experiences: number[];
    projects: number[];
  } | null>(null);
  const [preview, setPreview] = useState("");
  const [saved, setSaved] = useState<Document | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dna = profile.data?.data;
  const suggested = (field: "experiences" | "projects") =>
    (dna?.[field] || [])
      .map((entry, index) => ({ entry, index }))
      .filter(({ entry }) =>
        job.data?.data.requirements.some((r) =>
          (entry.title + " " + entry.description)
            .toLocaleLowerCase()
            .includes(r.skill.toLocaleLowerCase()),
        ),
      )
      .map((x) => x.index);
  const selection = selected || {
    experiences: suggested("experiences"),
    projects: suggested("projects"),
  };
  const body = { ...selection, profile_version: profile.data?.version };
  async function generate(save: boolean) {
    if (!job.data) return;
    setBusy(true);
    setError("");
    try {
      if (save) {
        setSaved(
          await post<Document>(
            `/applications/${job.data.application.id}/resume`,
            body,
          ),
        );
      } else {
        const response = await post<{ text: string }>(
          `/applications/${job.data.application.id}/resume-preview`,
          body,
        );
        setPreview(response.text);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="FATOS DA SUA TRAJETÓRIA"
        title="Preparar currículo"
        description={
          job.data
            ? `${job.data.title} — ${job.data.company}`
            : "Carregando vaga"
        }
      />
      <ErrorBox message={error || job.error || profile.error} />
      <section className="panel">
        <p>
          Selecione experiências e projetos existentes. As sugestões usam os
          requisitos cadastrados; revise a seleção. Identificação, resumo,
          formação e certificações são preservados.
        </p>
        {dna &&
          (["experiences", "projects"] as const).map((field) => (
            <fieldset key={field}>
              <legend>
                {field === "experiences" ? "Experiências" : "Projetos"}
              </legend>
              {dna[field].length ? (
                dna[field].map((entry, index) => (
                  <label className="checkbox-inline" key={index}>
                    <input
                      type="checkbox"
                      checked={selection[field].includes(index)}
                      onChange={(e) => {
                        setSelected({
                          ...selection,
                          [field]: e.target.checked
                            ? [...selection[field], index]
                            : selection[field].filter((i) => i !== index),
                        });
                        setPreview("");
                        setSaved(null);
                      }}
                    />
                    {entry.title} — {entry.organization}
                  </label>
                ))
              ) : (
                <p>Nenhum item cadastrado.</p>
              )}
            </fieldset>
          ))}
        <button
          className="button"
          disabled={busy || !dna}
          onClick={() => generate(false)}
        >
          Revisar currículo selecionado
        </button>
        {preview && (
          <>
            <h3>Prévia para revisão</h3>
            <pre className="prose-text" style={{ whiteSpace: "pre-wrap" }}>
              {preview}
            </pre>
            <button
              className="button primary"
              disabled={busy}
              onClick={() => generate(true)}
            >
              Aprovar e salvar versão
            </button>
          </>
        )}
        {saved && (
          <div className="button-row">
            <a
              className="button"
              href={`/api/documents/${saved.id}/download?format=docx`}
            >
              Exportar DOCX
            </a>
            <a
              className="button"
              href={`/api/documents/${saved.id}/download?format=html`}
            >
              Exportar HTML para imprimir / PDF
            </a>
            <Link href="/documents">Revisar versão em Documentos</Link>
          </div>
        )}
        <p>
          <Link href={`/jobs/${id}`}>Voltar à candidatura</Link>
        </p>
      </section>
    </>
  );
}
