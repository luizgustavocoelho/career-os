"use client";
import Link from "next/link";
import { ArrowUpRight, MapPin, Star } from "lucide-react";
import { Job, MODES, PRIORITIES, STATES } from "@/lib/types";
import { date, post } from "@/lib/api";
import { Badge, Score } from "./ui";
export function JobCard({
  job,
  onUpdate,
}: {
  job: Job;
  onUpdate?: () => void;
}) {
  return (
    <article className="job-card">
      <div className="job-card-top">
        <span className="company-logo">
          {job.company.slice(0, 2).toUpperCase()}
        </span>
        <div>
          <b>{job.company}</b>
          <small>{date(job.created_at)}</small>
        </div>
        <button
          className={`icon-button favorite ${job.favorite ? "selected" : ""}`}
          title={
            job.favorite ? "Remover dos favoritos" : "Salvar nos favoritos"
          }
          onClick={async () => {
            try {
              await post(`/jobs/${job.id}/favorite`);
              onUpdate?.();
            } catch (e) {
              alert((e as Error).message);
            }
          }}
        >
          <Star size={17} fill={job.favorite ? "currentColor" : "none"} />
        </button>
      </div>
      <Link href={`/jobs/${job.id}`} className="job-title">
        {job.title}
        <ArrowUpRight size={18} />
      </Link>
      <div className="job-location">
        <MapPin size={14} />
        {job.location || "Local não informado"}
        <span>·</span>
        {MODES[job.work_model]}
      </div>
      <div className="job-card-bottom">
        <Badge>{STATES[job.application.status]}</Badge>
        <div className="match-inline">
          <small>Opportunity Score</small>
          <Score small value={job.score} />
        </div>
      </div>
      {job.classification && (
        <div className="job-context">
          <Badge tone={job.classification === "high" ? "green" : ""}>
            {PRIORITIES[job.classification]}
          </Badge>
          <small>Cobertura: {job.coverage}%</small>
        </div>
      )}
    </article>
  );
}
