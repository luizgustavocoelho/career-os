"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Link2, Plus, Save, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { ErrorBox, Field, Heading } from "@/components/ui";
import { JobData, MODES, SENIORITIES } from "@/lib/types";
import { api, post, put } from "@/lib/api";
const blank: JobData = {
  title: "",
  company: "",
  location: "",
  description: "",
  url: null,
  source: "manual",
  work_model: "unknown",
  seniority: "unknown",
  salary_min: null,
  salary_max: null,
  salary_currency: "BRL",
  salary_period: "month",
  experience_months: null,
  education_level: null,
  requirements: [],
  responsibilities: [],
  soft_skills: [],
  benefits: [],
  languages: [],
  keywords: [],
  published_at: null,
  deadline: null,
};
export default function NewJob() {
  const [job, setJob] = useState<JobData>(blank);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const router = useRouter();
  const [editId, setEditId] = useState<string | null>(null);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("edit");
    if (id)
      api<{ data: JobData }>(`/jobs/${id}`)
        .then((j) => {
          setJob(j.data);
          setEditId(id);
        })
        .catch((e) => setError(e.message));
  }, []);
  const set = <K extends keyof JobData>(key: K, value: JobData[K]) =>
    setJob({ ...job, [key]: value });
  async function parse(ai = false, fromUrl = false) {
    setBusy(true);
    setError("");
    try {
      const result = await post<{ data: JobData }>(
        fromUrl ? "/jobs/from-url" : `/jobs/parse?ai=${ai}`,
        fromUrl ? { url } : { text: job.description },
      );
      setJob({ ...blank, ...result.data });
      setNotice(
        "Campos extraídos. Revise empresa, cargo e requisitos antes de salvar. A interpretação pode conter erros.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const saved = editId
        ? await put<{ id: string }>(`/jobs/${editId}`, job)
        : await post<{ id: string }>("/jobs", job);
      router.push(`/jobs/${saved.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="back-link" href="/radar">
        <ArrowLeft size={15} />
        Voltar ao radar
      </Link>
      <Heading
        eyebrow="UMA NOVA POSSIBILIDADE"
        title="Adicionar oportunidade"
        description="Cole a descrição ou importe de uma fonte pública. Você revisa tudo antes de salvar."
      />
      <ErrorBox message={error} />
      <section className="panel">
        <div className="section-heading">
          <h3>
            <Link2 size={18} />
            Importar por URL
          </h3>
          <span className="muted">Greenhouse e Lever</span>
        </div>
        <div className="inline-form">
          <input
            aria-label="URL da vaga para importar"
            type="url"
            placeholder="https://job-boards.greenhouse.io/empresa/jobs/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            disabled={busy || !url}
            className="button"
            onClick={() => parse(false, true)}
          >
            Importar URL
          </button>
        </div>
        <small className="muted">
          Para LinkedIn e outras fontes, cole a descrição abaixo e registre o
          link original.
        </small>
      </section>
      <form onSubmit={save} className="stack">
        <section className="panel">
          <Field label="Descrição completa da vaga">
            <textarea
              rows={9}
              minLength={20}
              maxLength={60000}
              required
              placeholder="Cole aqui responsabilidades, requisitos, benefícios e demais informações da vaga…"
              value={job.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </Field>
          <div className="button-row">
            <button
              type="button"
              className="button"
              disabled={busy || job.description.length < 20}
              onClick={() => parse()}
            >
              Extrair termos localmente
            </button>
            <button
              type="button"
              className="button"
              disabled={busy || job.description.length < 20}
              onClick={() => parse(true)}
            >
              <Sparkles size={16} />
              Interpretar com IA
            </button>
          </div>
          {notice && <div className="notice">{notice}</div>}
        </section>
        <section className="panel">
          <h3>Dados da oportunidade</h3>
          <div className="form-grid">
            <Field label="Cargo">
              <input
                required
                value={job.title}
                onChange={(e) => set("title", e.target.value)}
              />
            </Field>
            <Field label="Empresa">
              <input
                required
                value={job.company}
                onChange={(e) => set("company", e.target.value)}
              />
            </Field>
            <Field label="Localização / restrição geográfica">
              <input
                value={job.location}
                onChange={(e) => set("location", e.target.value)}
              />
            </Field>
            <Field label="Link original">
              <input
                type="url"
                value={job.url || ""}
                onChange={(e) => set("url", e.target.value || null)}
              />
            </Field>
            <Field label="Modelo de trabalho">
              <select
                value={job.work_model}
                onChange={(e) => set("work_model", e.target.value)}
              >
                {Object.entries(MODES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Senioridade">
              <select
                value={job.seniority}
                onChange={(e) => set("seniority", e.target.value)}
              >
                {Object.entries(SENIORITIES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Salário mínimo">
              <input
                type="number"
                min={0}
                value={job.salary_min ?? ""}
                onChange={(e) =>
                  set(
                    "salary_min",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              />
            </Field>
            <Field label="Salário máximo">
              <input
                type="number"
                min={0}
                value={job.salary_max ?? ""}
                onChange={(e) =>
                  set(
                    "salary_max",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              />
            </Field>
            <Field label="Moeda">
              <select
                value={job.salary_currency}
                onChange={(e) => set("salary_currency", e.target.value)}
              >
                {["BRL", "USD", "EUR", "GBP"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            <Field label="Período salarial">
              <select
                value={job.salary_period}
                onChange={(e) => set("salary_period", e.target.value)}
              >
                <option value="month">Mensal</option>
                <option value="year">Anual</option>
                <option value="hour">Hora</option>
              </select>
            </Field>
            <Field label="Experiência exigida em meses">
              <input
                type="number"
                min={0}
                max={960}
                value={job.experience_months ?? ""}
                onChange={(e) =>
                  set(
                    "experience_months",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              />
            </Field>
            <Field label="Formação mínima">
              <select
                value={job.education_level ?? ""}
                onChange={(e) =>
                  set(
                    "education_level",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              >
                <option value="">Não informada</option>
                <option value="0">Sem exigência</option>
                <option value="1">Ensino médio</option>
                <option value="2">Técnico</option>
                <option value="3">Graduação</option>
                <option value="4">Mestrado / pós</option>
                <option value="5">Doutorado</option>
              </select>
            </Field>
            <Field label="Data de publicação">
              <input
                type="date"
                value={job.published_at?.slice(0, 10) || ""}
                onChange={(e) => set("published_at", e.target.value || null)}
              />
            </Field>
            <Field label="Prazo">
              <input
                type="date"
                value={job.deadline?.slice(0, 10) || ""}
                onChange={(e) => set("deadline", e.target.value || null)}
              />
            </Field>
          </div>
        </section>
        <section className="panel">
          <div className="section-heading">
            <div>
              <h3>Requisitos e habilidades</h3>
              <p>Confirme o que é obrigatório. O score usa estes dados.</p>
            </div>
            <button
              type="button"
              className="button"
              onClick={() =>
                set("requirements", [
                  ...job.requirements,
                  { skill: "", mandatory: true, description: "" },
                ])
              }
            >
              <Plus size={15} />
              Requisito
            </button>
          </div>
          {job.requirements.map((r, i) => (
            <div className="requirement-edit" key={i}>
              <input
                aria-label={`Habilidade ${i + 1}`}
                required
                placeholder="Ex.: Python"
                value={r.skill}
                onChange={(e) =>
                  set(
                    "requirements",
                    job.requirements.map((v, n) =>
                      n === i ? { ...v, skill: e.target.value } : v,
                    ),
                  )
                }
              />
              <input
                aria-label={`Contexto ${i + 1}`}
                placeholder="Trecho da vaga / contexto"
                value={r.description}
                onChange={(e) =>
                  set(
                    "requirements",
                    job.requirements.map((v, n) =>
                      n === i ? { ...v, description: e.target.value } : v,
                    ),
                  )
                }
              />
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={r.mandatory}
                  onChange={(e) =>
                    set(
                      "requirements",
                      job.requirements.map((v, n) =>
                        n === i ? { ...v, mandatory: e.target.checked } : v,
                      ),
                    )
                  }
                />
                Obrigatório
              </label>
              <button
                type="button"
                className="icon-button"
                aria-label="Remover requisito"
                onClick={() =>
                  set(
                    "requirements",
                    job.requirements.filter((_, n) => n !== i),
                  )
                }
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {!job.requirements.length && (
            <p className="muted">
              Adicione requisitos ou extraia os termos da descrição.
            </p>
          )}
          <div className="form-grid">
            {(
              [
                ["responsibilities", "Responsabilidades"],
                ["soft_skills", "Soft skills"],
                ["benefits", "Benefícios"],
                ["languages", "Idiomas"],
              ] as const
            ).map(([k, label]) => (
              <Field label={`${label} (um por linha)`} key={k}>
                <textarea
                  rows={3}
                  value={job[k].join("\n")}
                  onChange={(e) => set(k, e.target.value.split("\n"))}
                />
              </Field>
            ))}
          </div>
        </section>
        <div className="form-footer">
          <span>
            O score será calculado ao salvar. Vagas duplicadas serão
            reconhecidas.
          </span>
          <button className="button primary" disabled={busy}>
            <Save size={17} />
            {busy ? "Processando…" : "Salvar e analisar"}
          </button>
        </div>
      </form>
    </>
  );
}
