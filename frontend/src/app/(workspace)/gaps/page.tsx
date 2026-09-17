"use client";
import { useState } from "react";
import { Target } from "lucide-react";
import { Gap } from "@/lib/types";
import {
  Badge,
  Empty,
  ErrorBox,
  Heading,
  Loading,
  useLoad,
} from "@/components/ui";
export default function Gaps() {
  const { data, error } = useLoad<Gap>("/gaps");
  const [filter, setFilter] = useState("all");
  return (
    <>
      <Heading
        eyebrow="APRENDA COM DIREÇÃO"
        title="Career Gap"
        description="O que suas oportunidades pedem — e onde seu próximo aprendizado pode fazer diferença."
      />
      <ErrorBox message={error} />
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="insight-banner">
            <Target size={25} />
            <div>
              <b>Baseado em {data.sample_size} vaga(s) do seu radar.</b>
              <p>{data.scope}</p>
            </div>
          </div>
          <div className="tabs">
            {[
              ["all", "Todas as skills"],
              ["missing", "Não registradas"],
              ["weak", "Em desenvolvimento"],
              ["strong", "Declaradas fortes"],
              ["impact", "Alto impacto"],
            ].map(([k, v]) => (
              <button
                key={k}
                className={filter === k ? "active" : ""}
                onClick={() => setFilter(k)}
              >
                {v}
              </button>
            ))}
          </div>
          <section className="panel">
            {data.skills.length ? (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Habilidade</th>
                        <th>Frequência na amostra</th>
                        <th>Seu perfil</th>
                        <th>Prioridade de estudo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.skills
                        .filter(
                          (s) =>
                            filter === "all" ||
                            (filter === "impact" && s.high_impact) ||
                            s.category === filter,
                        )
                        .map((s) => (
                          <tr key={s.skill}>
                            <td>
                              <b>{s.skill}</b>
                              <small>
                                {s.mandatory_count} requisito(s) obrigatório(s)
                              </small>
                            </td>
                            <td>
                              <div className="frequency">
                                <div className="bar-track">
                                  <span style={{ width: `${s.percentage}%` }} />
                                </div>
                                <b>{s.percentage}%</b>
                              </div>
                              <small>
                                {s.count} de {data.sample_size} vagas
                              </small>
                            </td>
                            <td>
                              <Badge
                                tone={
                                  s.category === "strong"
                                    ? "green"
                                    : s.category === "missing"
                                      ? "orange"
                                      : ""
                                }
                              >
                                {s.category === "strong"
                                  ? "Nível declarado ≥ 3"
                                  : s.category === "weak"
                                    ? "Em desenvolvimento"
                                    : "Não registrada"}
                              </Badge>
                            </td>
                            <td>
                              {s.high_impact ? (
                                <Badge tone="purple">
                                  Alto impacto na amostra
                                </Badge>
                              ) : (
                                "—"
                              )}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                <p className="muted">
                  Alto impacto: habilidade ausente ou fraca em pelo menos 30% da
                  amostra. Isso mede frequência, não garante aumento de score
                  nem contratação. Nível declarado não substitui evidências.
                </p>
              </>
            ) : (
              <Empty
                title="Seu mapa de aprendizado se forma com dados"
                description="Analise vagas reais e mantenha seu perfil atualizado para identificar gaps relevantes."
                href="/radar"
                action="Ir para o radar"
              />
            )}
          </section>
        </>
      )}
    </>
  );
}
