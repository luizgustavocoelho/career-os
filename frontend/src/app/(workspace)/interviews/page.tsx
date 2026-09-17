"use client";
import Link from "next/link";
import { CalendarDays, ArrowUpRight } from "lucide-react";
import { dateTime } from "@/lib/api";
import { Overview } from "@/lib/types";
import {
  Badge,
  Empty,
  ErrorBox,
  Heading,
  Loading,
  useLoad,
} from "@/components/ui";
export default function Interviews() {
  const { data, error } = useLoad<Overview>("/dashboard");
  return (
    <>
      <Heading
        eyebrow="PREPARE SEU PRÓXIMO PASSO"
        title="Interview Missions"
        description="Entre em cada conversa com contexto, exemplos reais e boas perguntas."
      />
      <ErrorBox message={error} />
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="insight-banner">
            <CalendarDays size={24} />
            <div>
              <b>{data.interview_count} entrevista(s) registrada(s)</b>
              <p>
                Agende, prepare e registre feedback no workspace de cada
                oportunidade.
              </p>
            </div>
          </div>
          {data.upcoming.length ? (
            <div className="job-grid">
              {data.upcoming.map((i) => (
                <Link
                  className="panel interview-summary"
                  key={i.id}
                  href={`/jobs/${i.job_id}`}
                >
                  <Badge tone="purple">Próxima entrevista</Badge>
                  <h3>{i.title}</h3>
                  <p>{i.company}</p>
                  <b>{dateTime(i.scheduled_at)}</b>
                  <span className="text-link">
                    Abrir missão
                    <ArrowUpRight size={16} />
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <section className="panel">
              <Empty
                title="Sua próxima conversa começa com uma oportunidade"
                description="Abra uma vaga no radar e registre a entrevista para criar sua preparação."
                href="/radar"
                action="Abrir radar"
              />
            </section>
          )}
          <Link className="text-link" href="/pipeline">
            Consultar candidaturas e entrevistas anteriores →
          </Link>
        </>
      )}
    </>
  );
}
