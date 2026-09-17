"use client";
import { useState } from "react";
import { CheckCircle2, Plus, Trash2, Github } from "lucide-react";
import { Skill } from "@/lib/types";
import { api, post, put, safeUrl } from "@/lib/api";
import { Badge, ErrorBox, Field } from "./ui";
export function SkillsEditor({
  skills,
  reload,
}: {
  skills: Skill[];
  reload: () => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [repo, setRepo] = useState("");
  const [github, setGithub] = useState<{
    title: string;
    description: string;
    url: string;
    languages: string[];
    readme: string;
    warning: string;
  } | null>(null);
  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h3>Skills & Evidence Engine</h3>
          <p>Uma declaração é um começo. Evidências dão contexto.</p>
        </div>
        <Badge>{skills.length} skills</Badge>
      </div>
      <ErrorBox message={error} />
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await post("/profile/skills", { name });
            setName("");
          });
        }}
      >
        <input
          aria-label="Nova habilidade"
          required
          placeholder="Ex.: Python, SQL, comunicação…"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="button" disabled={busy}>
          <Plus size={16} />
          Adicionar skill
        </button>
      </form>
      <div className="skills-list">
        {skills.map((s) => (
          <div key={s.id} className="skill-card">
            <div className="skill-header">
              <div>
                <strong>{s.name}</strong>
                <Badge tone={s.evidence.length ? "green" : ""}>
                  {s.evidence.length
                    ? `${s.evidence.length} evidência(s)`
                    : "Declarada"}
                </Badge>
              </div>
              <div className="button-row">
                <button
                  className="text-button"
                  onClick={() => setSelected(selected === s.id ? null : s.id)}
                >
                  Editar e adicionar evidência
                </button>
                <button
                  className="icon-button danger"
                  aria-label={`Remover ${s.name}`}
                  onClick={() => {
                    if (confirm(`Remover ${s.name} e suas evidências?`))
                      run(() =>
                        api(`/profile/skills/${s.id}`, { method: "DELETE" }),
                      );
                  }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
            {s.evidence.map((ev) => (
              <div className="evidence-row" key={ev.id}>
                <CheckCircle2 size={16} />
                <div>
                  <b>{ev.title}</b>
                  <p>{ev.description}</p>
                  {safeUrl(ev.url) && (
                    <a
                      target="_blank"
                      rel="noreferrer"
                      href={safeUrl(ev.url)}
                      className="text-link"
                    >
                      Ver fonte ↗
                    </a>
                  )}
                </div>
                <button
                  className="icon-button"
                  aria-label="Remover evidência"
                  onClick={() =>
                    run(() =>
                      api(`/profile/evidence/${ev.id}`, { method: "DELETE" }),
                    )
                  }
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {selected === s.id && (
              <div className="skill-expanded">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    run(() =>
                      put(`/profile/skills/${s.id}`, {
                        name: s.name,
                        category: f.get("category"),
                        level: Number(f.get("level")),
                        months: f.get("months")
                          ? Number(f.get("months"))
                          : null,
                        last_used: f.get("last_used") || null,
                        developing: f.get("developing") === "on",
                      }),
                    );
                  }}
                >
                  <div className="form-grid">
                    <Field label="Categoria">
                      <input name="category" defaultValue={s.category} />
                    </Field>
                    <Field label="Nível percebido (1–5)">
                      <input
                        name="level"
                        type="number"
                        min={1}
                        max={5}
                        defaultValue={s.level}
                      />
                    </Field>
                    <Field label="Experiência em meses">
                      <input
                        name="months"
                        type="number"
                        min={0}
                        max={960}
                        defaultValue={s.months ?? ""}
                      />
                    </Field>
                    <Field label="Última utilização">
                      <input
                        name="last_used"
                        type="date"
                        defaultValue={s.last_used || ""}
                      />
                    </Field>
                  </div>
                  <label className="checkbox-inline">
                    <input
                      type="checkbox"
                      name="developing"
                      defaultChecked={s.developing}
                    />
                    Em desenvolvimento
                  </label>
                  <button className="button" disabled={busy}>
                    Salvar habilidade
                  </button>
                </form>
                <form
                  className="stack"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = e.currentTarget;
                    const f = new FormData(form);
                    run(async () => {
                      await post(`/profile/skills/${s.id}/evidence`, {
                        kind: f.get("kind"),
                        title: f.get("title"),
                        description: f.get("description"),
                        url: f.get("url") || null,
                        confidence: Number(f.get("confidence")),
                      });
                      form.reset();
                    });
                  }}
                >
                  <h4>Associar uma evidência</h4>
                  <div className="form-grid">
                    <Field label="Origem">
                      <select name="kind">
                        <option value="project">Projeto</option>
                        <option value="experience">
                          Experiência profissional
                        </option>
                        <option value="education">Formação</option>
                        <option value="certification">Certificação</option>
                        <option value="course">Curso</option>
                        <option value="github">GitHub</option>
                      </select>
                    </Field>
                    <Field label="Título da evidência">
                      <input name="title" required minLength={2} />
                    </Field>
                  </div>
                  <Field
                    label="O que demonstra essa habilidade?"
                    hint="Descreva sua contribuição real, tecnologias usadas e o que pode ser conferido."
                  >
                    <textarea
                      name="description"
                      required
                      minLength={10}
                      rows={3}
                    />
                  </Field>
                  <div className="form-grid">
                    <Field label="Link da evidência">
                      <input name="url" type="url" />
                    </Field>
                    <Field label="Confiança da associação">
                      <select name="confidence" defaultValue="1">
                        <option value="1">Confirmada por mim</option>
                        <option value="0.7">Há informação suficiente</option>
                        <option value="0.3">Indício, precisa de revisão</option>
                      </select>
                    </Field>
                  </div>
                  <button className="button primary" disabled={busy}>
                    Salvar evidência
                  </button>
                </form>
              </div>
            )}
          </div>
        ))}
      </div>
      <details className="github-import">
        <summary>
          <Github size={17} />
          Consultar um projeto público do GitHub
        </summary>
        <p className="muted">
          A consulta acontece somente ao clicar. Confirme sua contribuição antes
          de criar evidências.
        </p>
        <div className="inline-form">
          <input
            type="url"
            aria-label="URL do repositório"
            placeholder="https://github.com/usuario/repositorio"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
          />
          <button
            className="button"
            disabled={busy || !repo}
            onClick={() =>
              run(async () =>
                setGithub(await post("/integrations/github", { url: repo })),
              )
            }
          >
            Consultar
          </button>
        </div>
        {github && (
          <div className="notice">
            <b>{github.title}</b>
            <p>{github.description}</p>
            <p>Linguagens detectadas: {github.languages.join(", ")}</p>
            <small>{github.warning}</small>
            <details>
              <summary>README</summary>
              <pre>{github.readme}</pre>
            </details>
          </div>
        )}
      </details>
    </section>
  );
}
