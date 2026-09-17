"use client";
import { Overview } from "@/lib/types";
import { Empty, ErrorBox, Heading, Loading, useLoad } from "@/components/ui";
export default function Analytics() {
  const { data: d, error } = useLoad<Overview>("/analytics");
  if (!d) return error ? <ErrorBox message={error} /> : <Loading />;
  return (
    <>
      <Heading
        eyebrow="APRENDA COM A SUA BUSCA"
        title="Analytics"
        description="Observe padrões, acompanhe resultados e ajuste o caminho com dados reais."
      />
      <div className="stats-grid">
        {[
          [
            "Taxa de candidatura",
            d.application_rate === null ? "—" : `${d.application_rate}%`,
          ],
          [
            "Taxa de resposta",
            d.response_rate === null ? "—" : `${d.response_rate}%`,
          ],
          ["Entrevistas técnicas", d.technical_interviews],
          ["Ofertas", d.offers],
        ].map(([k, v]) => (
          <div className="stat-card" key={k}>
            <span>{k}</span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>
      {!d.jobs && (
        <section className="panel">
          <Empty
            title="Cada ação vai contar uma parte da história"
            description="Suas métricas aparecem conforme você analisa vagas e movimenta candidaturas."
            href="/radar/new"
            action="Adicionar oportunidade"
          />
        </section>
      )}
      <div className="analytics-grid">
        <section className="panel">
          <h3>Etapas alcançadas</h3>
          <p className="muted">
            Candidaturas únicas que passaram por cada etapa.
          </p>
          <Bars
            rows={d.pipeline
              .filter((p) => p.ever_reached)
              .map((p) => ({ label: p.label, value: p.ever_reached }))}
          />
        </section>
        <section className="panel">
          <h3>Candidaturas por semana</h3>
          <p className="muted">Eventos de envio registrados na timeline.</p>
          <Bars
            rows={d.weekly.map((w) => ({
              label: w.week,
              value: w.applications,
            }))}
          />
        </section>
        <section className="panel">
          <h3>Faixas de Opportunity Score</h3>
          <Bars
            rows={d.score_ranges.map((s) => ({
              label: s.label,
              value: s.count,
            }))}
          />
        </section>
        <section className="panel">
          <h3>Tempo médio entre etapas</h3>
          <p className="muted">Dias entre eventos consecutivos registrados.</p>
          <Bars
            rows={Object.entries(d.transition_days).map(([label, value]) => ({
              label,
              value,
            }))}
          />
        </section>
      </div>
      <div className="analytics-grid">
        {[
          ["Fontes", d.sources],
          ["Cargos", d.roles],
        ].map(([title, group]) => (
          <section className="panel" key={String(title)}>
            <h3>{String(title)} e entrevistas</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{String(title)}</th>
                    <th>Envios</th>
                    <th>Com entrevista</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(group as Overview["sources"]).map(
                    ([label, v]) => (
                      <tr key={label}>
                        <td>{label}</td>
                        <td>{v.applications}</td>
                        <td>{v.interviews}</td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </section>
        ))}
      </div>
      <section className="panel">
        <h3>Motivos de rejeição informados</h3>
        {Object.keys(d.rejection_reasons).length ? (
          <Bars
            rows={Object.entries(d.rejection_reasons).map(([label, value]) => ({
              label,
              value,
            }))}
          />
        ) : (
          <p className="muted">
            Nenhum motivo registrado. O sistema não deduz causas de rejeição.
          </p>
        )}
        <p className="muted">
          Respostas consideram etapas de triagem, entrevista, oferta,
          contratação ou rejeição após um envio registrado. Os dados sugerem
          padrões dentro da sua amostra; não estabelecem causalidade.
        </p>
      </section>
    </>
  );
}
function Bars({ rows }: { rows: { label: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="bars">
      {rows.length ? (
        rows.map((r, i) => (
          <div className="chart-row" key={i}>
            <span>{r.label}</span>
            <div className="bar-track">
              <span style={{ width: `${(100 * r.value) / max}%` }} />
            </div>
            <b>{r.value}</b>
          </div>
        ))
      ) : (
        <p className="muted">Sem eventos suficientes neste período.</p>
      )}
    </div>
  );
}
