"use client";
import Link from "next/link";
import { DashboardActions } from "@/components/diagnostics";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Check,
  Compass,
  Dna,
  Plus,
  Radar,
  Send,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { useSession } from "@/components/session";
import {
  Badge,
  Empty,
  ErrorBox,
  Heading,
  Loading,
  useLoad,
} from "@/components/ui";
import { JobCard } from "@/components/job-card";
import type { Gap, JobPage, Overview, Profile } from "@/lib/types";
import { dateTime } from "@/lib/api";
export default function Dashboard() {
  const { user } = useSession();
  const stats = useLoad<Overview>("/dashboard");
  const jobs = useLoad<JobPage>("/jobs?sort=priority&per_page=3");
  const profile = useLoad<Profile>("/profile");
  const gaps = useLoad<Gap>("/gaps");
  if (!stats.data)
    return stats.error ? <ErrorBox message={stats.error} /> : <Loading />;
  const d = stats.data;
  const complete =
    !!profile.data?.data.desired_roles.length && !!profile.data?.skills.length;
  return (
    <>
      <Heading
        eyebrow="SEU PRÓXIMO CAPÍTULO"
        title={`Olá, ${user?.name.split(" ")[0] || "você"}. Vamos avançar?`}
        description="Um pouco de foco hoje. Novas possibilidades amanhã."
      >
        <Link href="/radar/new" className="button primary">
          <Plus size={17} />
          Adicionar oportunidade
        </Link>
      </Heading>
      <DashboardActions />
      <div className="dashboard-top">
        <section className="focus-card">
          <div>
            <Badge tone="dark">
              <span className="status-dot" />
              SEU FOCO DE HOJE
            </Badge>
            <h2>
              {!complete
                ? "Boas oportunidades começam\ncom a sua história."
                : d.followups.length
                  ? "Uma boa conversa pode\nabrir o próximo capítulo."
                  : d.high_matches
                    ? "Seu próximo passo\njá está no radar."
                    : "Abra espaço para\nnovas oportunidades."}
            </h2>
            <p>
              {!complete
                ? "Construa seu Career DNA para descobrir onde seu perfil encontra o que o mercado procura."
                : d.followups.length
                  ? `${d.followups.length} acompanhamento(s) aguardando sua atenção. Revise o contexto antes de retomar o contato.`
                  : "Traga vagas reais para o seu workspace. Entenda os requisitos e decida onde investir seu tempo."}
            </p>
            <Link
              href={
                !complete
                  ? "/profile"
                  : d.followups.length
                    ? `/jobs/${d.followups[0].job_id}`
                    : "/radar"
              }
              className="button mint"
            >
              {!complete
                ? "Construir meu Career DNA"
                : d.followups.length
                  ? "Revisar acompanhamento"
                  : "Explorar meu radar"}
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="orbit-art" aria-hidden="true">
            <div className="orbit outer" />
            <div className="orbit middle" />
            <div className="orbit inner" />
            <div className="orbit-center">
              <Compass size={48} strokeWidth={1} />
            </div>
            <span className="orbit-node node-one">
              <Target size={19} />
            </span>
            <span className="orbit-node node-two">
              <Sparkles size={17} />
            </span>
            <i className="orbit-spark" />
          </div>
          <div className="focus-footer">
            <span>
              <span className="status-dot" />
              Uma ação de cada vez.
            </span>
            <span>Você decide o caminho ↗</span>
          </div>
        </section>
        <section className="panel today-panel">
          <div className="section-heading">
            <h3>Na sua agenda</h3>
            <CalendarDays size={18} />
          </div>
          {d.upcoming.length ? (
            d.upcoming.slice(0, 3).map((i) => (
              <Link
                href={`/jobs/${i.job_id}`}
                className="agenda-item"
                key={i.id}
              >
                <div className="agenda-icon">
                  <CalendarDays size={19} />
                </div>
                <div>
                  <b>{i.title}</b>
                  <small>
                    {i.company} · {dateTime(i.scheduled_at)}
                  </small>
                </div>
                <ArrowUpRight size={16} />
              </Link>
            ))
          ) : (
            <div className="agenda-empty">
              <CalendarDays size={30} strokeWidth={1.2} />
              <h4>Espaço para o que vem.</h4>
              <p>
                Suas próximas entrevistas aparecem aqui quando forem agendadas.
              </p>
            </div>
          )}
          <Link className="text-link" href="/interviews">
            Ver entrevistas
            <ArrowRight size={14} />
          </Link>
        </section>
      </div>
      <div className="stats-grid">
        {[
          {
            label: "No seu radar",
            value: d.jobs,
            detail: `${d.new_jobs} adicionadas nesta semana`,
            icon: Radar,
            color: "purple",
          },
          {
            label: "Matches fortes",
            value: d.high_matches,
            detail: "Score alto, com contexto suficiente",
            icon: Target,
            color: "green",
          },
          {
            label: "Candidaturas enviadas",
            value: d.applications,
            detail: `${d.waiting} em acompanhamento`,
            icon: Send,
            color: "blue",
          },
          {
            label: "Entrevistas",
            value: d.interview_count,
            detail: `${d.offers} oferta(s) registrada(s)`,
            icon: CalendarDays,
            color: "orange",
          },
        ].map((s) => (
          <div className="stat-card" key={s.label}>
            <div className="stat-top">
              <span>{s.label}</span>
              <span className={`stat-icon ${s.color}`}>
                <s.icon size={18} />
              </span>
            </div>
            <strong>{s.value}</strong>
            <small>{s.detail}</small>
          </div>
        ))}
      </div>
      <div className="section-heading roomy">
        <div>
          <h2>Oportunidades em destaque</h2>
          <p>Onde seu perfil e suas próximas possibilidades se encontram.</p>
        </div>
        <Link href="/radar" className="text-link">
          Ver radar completo
          <ArrowUpRight size={15} />
        </Link>
      </div>
      <ErrorBox message={jobs.error} />
      {jobs.data?.items.length ? (
        <div className="job-grid">
          {jobs.data.items.map((j) => (
            <JobCard key={j.id} job={j} onUpdate={jobs.reload} />
          ))}
        </div>
      ) : (
        <div className="panel">
          <Empty
            title="Seu radar está pronto para começar"
            description="Adicione uma vaga por descrição, URL ou uma fonte pública de oportunidades."
            href="/radar/new"
            action="Adicionar primeira vaga"
          />
        </div>
      )}
      <div className="dashboard-bottom">
        <section className="panel">
          <div className="section-heading">
            <h3>Próximas ações</h3>
            <span className="mini-label">COM INTENÇÃO</span>
          </div>
          {!complete && (
            <Link href="/profile" className="action-row">
              <span className="action-check">
                <Dna size={17} />
              </span>
              <div>
                <b>Fortaleça seu Career DNA</b>
                <small>
                  Cadastre seus objetivos e associe evidências às skills.
                </small>
              </div>
              <ArrowUpRight size={16} />
            </Link>
          )}
          {d.followups.slice(0, 3).map((f) => (
            <Link href={`/jobs/${f.job_id}`} key={f.id} className="action-row">
              <span className="action-check">
                <Send size={17} />
              </span>
              <div>
                <b>Retomar contato com {f.company}</b>
                <small>{f.title}</small>
              </div>
              <ArrowUpRight size={16} />
            </Link>
          ))}
          {d.jobs > 0 && (
            <Link href="/gaps" className="action-row">
              <span className="action-check">
                <TrendingUp size={17} />
              </span>
              <div>
                <b>Entenda as habilidades mais pedidas</b>
                <small>
                  Priorize seu estudo com base nas vagas do seu radar.
                </small>
              </div>
              <ArrowUpRight size={16} />
            </Link>
          )}
          {complete && !d.followups.length && (
            <div className="action-row">
              <span className="action-check">
                <Check size={17} />
              </span>
              <div>
                <b>Acompanhamentos em dia</b>
                <small>Novas ações aparecem conforme sua busca avança.</small>
              </div>
            </div>
          )}
        </section>
        <section className="panel growth-panel">
          <div className="section-heading">
            <h3>Seu próximo aprendizado</h3>
            <Target size={18} />
          </div>
          {gaps.data?.skills
            .filter((s) => s.high_impact)
            .slice(0, 3)
            .map((s) => (
              <div className="gap-mini" key={s.skill}>
                <div>
                  <b>{s.skill}</b>
                  <span>{s.percentage}% da amostra</span>
                </div>
                <div className="bar-track">
                  <span style={{ width: `${s.percentage}%` }} />
                </div>
              </div>
            ))}
          {!gaps.data?.skills.some((s) => s.high_impact) && (
            <p className="muted">
              À medida que você analisa vagas, identificamos habilidades
              recorrentes que ainda faltam no seu perfil.
            </p>
          )}
          <Link href="/gaps" className="text-link">
            Explorar Career Gap
            <ArrowRight size={14} />
          </Link>
        </section>
      </div>
    </>
  );
}
