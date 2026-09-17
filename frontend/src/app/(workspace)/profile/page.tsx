"use client";
import { useEffect, useState } from "react";
import { Save, Upload } from "lucide-react";
import Link from "next/link";
import { EntryEditor } from "@/components/entry-editor";
import { SkillsEditor } from "@/components/skills-editor";
import { ErrorBox, Field, Heading, Loading, useLoad } from "@/components/ui";
import { api, post, put } from "@/lib/api";
import { DNA, Document, Profile, SENIORITIES, Skill } from "@/lib/types";
export default function ProfilePage() {
  const p = useLoad<Profile>("/profile");
  return (
    <>
      <Heading
        eyebrow="SUA HISTÓRIA É O PONTO DE PARTIDA"
        title="Career DNA"
        description="Seu perfil, seus objetivos e as evidências que sustentam suas habilidades."
      >
        <Link className="button" href="/documents">
          <Upload size={16} />
          Importar currículo
        </Link>
      </Heading>
      <ErrorBox message={p.error} />
      {p.data ? (
        <ProfileForm initial={p.data} reload={p.reload} />
      ) : (
        <Loading />
      )}
    </>
  );
}
function ProfileForm({
  initial,
  reload,
}: {
  initial: Profile;
  reload: () => void;
}) {
  const [dna, setDna] = useState<DNA>(initial.data);
  const [version, setVersion] = useState(initial.version);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<Skill[]>([]);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("document");
    if (!id) return;
    api<Document>(`/documents/${id}`)
      .then((doc) => {
        if (!doc.extracted) return;
        setDna((prev) => {
          const next = { ...prev };
          for (const [key, value] of Object.entries(doc.extracted!.profile)) {
            if (
              [
                "ai_consent",
                "follow_up_days",
                "follow_up_enabled",
                "relocation",
                "salary_currency",
                "salary_period",
                "seniority",
              ].includes(key)
            )
              continue;
            if (
              value !== null &&
              value !== "" &&
              (!Array.isArray(value) || value.length)
            )
              Object.assign(next, { [key]: value });
          }
          return next;
        });
        setSuggestions(doc.extracted.skills);
        setNotice(
          "Dados extraídos carregados para revisão. Corrija os campos e clique em Salvar Career DNA. Nada foi aplicado ao perfil ainda.",
        );
      })
      .catch((e) => setError(e.message));
  }, []);
  const set = <K extends keyof DNA>(key: K, value: DNA[K]) =>
    setDna({ ...dna, [key]: value });
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const p = await put<Profile>("/profile", { data: dna, version });
      setVersion(p.version);
      setNotice(
        "Career DNA salvo. Scores anteriores foram marcados para recálculo.",
      );
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="profile-layout">
      <div className="profile-main">
        <ErrorBox message={error} />
        {notice && <div className="notice">{notice}</div>}
        <form onSubmit={save} className="stack">
          <section className="panel">
            <h3>Identidade profissional</h3>
            <div className="form-grid">
              {(
                [
                  ["name", "Nome"],
                  ["headline", "Título profissional"],
                  ["location", "Cidade / região"],
                  ["email", "E-mail profissional"],
                  ["phone", "Telefone"],
                  ["linkedin", "LinkedIn"],
                  ["github", "GitHub"],
                  ["portfolio", "Portfólio"],
                ] as const
              ).map(([key, label]) => (
                <Field key={key} label={label}>
                  <input
                    type={
                      ["linkedin", "github", "portfolio"].includes(key)
                        ? "url"
                        : key === "email"
                          ? "email"
                          : "text"
                    }
                    value={dna[key]}
                    onChange={(e) => set(key, e.target.value)}
                  />
                </Field>
              ))}
            </div>
            <Field label="Resumo profissional">
              <textarea
                rows={5}
                value={dna.summary}
                onChange={(e) => set("summary", e.target.value)}
              />
            </Field>
          </section>
          <section className="panel">
            <h3>Onde você quer chegar</h3>
            <div className="form-grid">
              {(
                [
                  ["desired_roles", "Cargos desejados"],
                  ["acceptable_roles", "Cargos aceitáveis"],
                  ["languages", "Idiomas e níveis"],
                  ["interests", "Áreas de interesse"],
                  ["target_companies", "Empresas de interesse"],
                  ["sectors", "Setores preferidos"],
                ] as const
              ).map(([key, label]) => (
                <Field
                  key={key}
                  label={label}
                  hint="Separe os itens por vírgula."
                >
                  <input
                    value={dna[key].join(",")}
                    onChange={(e) => set(key, e.target.value.split(","))}
                  />
                </Field>
              ))}
              <Field label="Senioridade">
                <select
                  value={dna.seniority}
                  onChange={(e) => set("seniority", e.target.value)}
                >
                  {Object.entries(SENIORITIES).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Experiência total em meses">
                <input
                  type="number"
                  min={0}
                  max={960}
                  value={dna.experience_months ?? ""}
                  onChange={(e) =>
                    set(
                      "experience_months",
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                />
              </Field>
              <Field label="Formação concluída">
                <select
                  value={dna.education_level ?? ""}
                  onChange={(e) =>
                    set(
                      "education_level",
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                >
                  <option value="">Não informada</option>
                  {[
                    "Sem formação formal",
                    "Ensino médio",
                    "Técnico",
                    "Graduação",
                    "Mestrado / pós",
                    "Doutorado",
                  ].map((v, i) => (
                    <option value={i} key={i}>
                      {v}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Pretensão salarial mínima">
                <input
                  type="number"
                  min={0}
                  value={dna.salary_min ?? ""}
                  onChange={(e) =>
                    set(
                      "salary_min",
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                />
              </Field>
              <Field label="Moeda">
                <select
                  value={dna.salary_currency}
                  onChange={(e) => set("salary_currency", e.target.value)}
                >
                  {["BRL", "USD", "EUR", "GBP"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </Field>
              <Field label="Período">
                <select
                  value={dna.salary_period}
                  onChange={(e) => set("salary_period", e.target.value)}
                >
                  <option value="month">Mensal</option>
                  <option value="year">Anual</option>
                  <option value="hour">Hora</option>
                </select>
              </Field>
            </div>
            <div className="button-row">
              {[
                ["remote", "Remoto"],
                ["hybrid", "Híbrido"],
                ["onsite", "Presencial"],
              ].map(([key, label]) => (
                <label key={key} className="checkbox-inline">
                  <input
                    type="checkbox"
                    checked={dna.work_models.includes(key)}
                    onChange={(e) =>
                      set(
                        "work_models",
                        e.target.checked
                          ? [...dna.work_models, key]
                          : dna.work_models.filter((x) => x !== key),
                      )
                    }
                  />
                  {label}
                </label>
              ))}
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={dna.relocation}
                  onChange={(e) => set("relocation", e.target.checked)}
                />
                Disponível para mudança
              </label>
            </div>
            <Field label="Objetivos profissionais">
              <textarea
                rows={3}
                value={dna.goals}
                onChange={(e) => set("goals", e.target.value)}
              />
            </Field>
          </section>
          {(
            [
              ["experiences", "Experiências"],
              ["projects", "Projetos"],
              ["education", "Formação"],
              ["certifications", "Certificações"],
            ] as const
          ).map(([key, label]) => (
            <EntryEditor
              key={key}
              title={label}
              entries={dna[key]}
              onChange={(v) => set(key, v)}
            />
          ))}
          <section className="panel">
            <h3>Preferências e privacidade</h3>
            <label className="checkbox-inline">
              <input
                type="checkbox"
                checked={dna.ai_consent}
                onChange={(e) => set("ai_consent", e.target.checked)}
              />
              Autorizo enviar o contexto necessário ao provedor de IA quando
              solicitar uma análise.
            </label>
            <p className="muted">
              Perfil profissional, habilidades, evidências e contexto da vaga
              podem ser enviados. O PDF original não é enviado; a extração com
              IA usa seu texto. Senhas e chaves nunca entram nos prompts.
            </p>
            <div className="inline-form">
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={dna.follow_up_enabled}
                  onChange={(e) => set("follow_up_enabled", e.target.checked)}
                />
                Sugerir follow-ups
              </label>
              <Field label="Dias sem movimentação">
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={dna.follow_up_days}
                  onChange={(e) =>
                    set("follow_up_days", Number(e.target.value))
                  }
                />
              </Field>
            </div>
          </section>
          <div className="sticky-save">
            <span>Seu perfil é editável. Você tem a palavra final.</span>
            <button className="button primary" disabled={busy}>
              <Save size={17} />
              {busy ? "Salvando…" : "Salvar Career DNA"}
            </button>
          </div>
        </form>
        {suggestions.length > 0 && (
          <section className="panel">
            <h3>Habilidades extraídas para revisão</h3>
            <p>
              Adicione apenas o que corresponde à sua experiência. Elas entram
              como declarações.
            </p>
            <div className="chip-list">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  className="button"
                  onClick={async () => {
                    try {
                      await post("/profile/skills", {
                        name: s.name,
                        level: s.level || 1,
                      });
                      setSuggestions(suggestions.filter((_, n) => n !== i));
                      reload();
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  + {s.name}
                </button>
              ))}
            </div>
          </section>
        )}
        <SkillsEditor skills={initial.skills} reload={reload} />
      </div>
      <aside className="profile-aside">
        <div className="panel">
          <span className="eyebrow">UM PERFIL COM CONTEXTO</span>
          <h3>Mais que uma lista de palavras.</h3>
          <p>
            Seu DNA conecta objetivos, experiências e evidências para tornar
            cada análise mais útil.
          </p>
          <ol>
            <li>Registre o que você já fez.</li>
            <li>Defina o que procura agora.</li>
            <li>Associe evidências às habilidades.</li>
            <li>Revise sempre que sua história evoluir.</li>
          </ol>
          <small>
            Dados ausentes geram incerteza no score. Eles nunca contam como
            compatibilidade confirmada.
          </small>
        </div>
      </aside>
    </div>
  );
}
