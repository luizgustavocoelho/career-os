export type User = {
  id: string;
  name: string;
  email: string;
  csrf_token: string;
};
export type Entry = {
  title: string;
  organization: string;
  description: string;
  start: string;
  end: string;
  url: string;
};
export type DNA = {
  name: string;
  headline: string;
  summary: string;
  location: string;
  email: string;
  phone: string;
  github: string;
  linkedin: string;
  portfolio: string;
  desired_roles: string[];
  acceptable_roles: string[];
  seniority: string;
  work_models: string[];
  relocation: boolean;
  salary_min: number | null;
  salary_currency: string;
  salary_period: string;
  experience_months: number | null;
  education_level: number | null;
  interests: string[];
  target_companies: string[];
  sectors: string[];
  goals: string;
  languages: string[];
  experiences: Entry[];
  education: Entry[];
  certifications: Entry[];
  projects: Entry[];
  ai_consent: boolean;
  follow_up_days: number;
  follow_up_enabled: boolean;
};
export type Evidence = {
  id: string;
  kind: string;
  title: string;
  description: string;
  url: string | null;
  confidence: number;
};
export type Skill = {
  id: string;
  name: string;
  normalized: string;
  category: string;
  level: number;
  months: number | null;
  last_used: string | null;
  developing: boolean;
  evidence: Evidence[];
};
export type Profile = {
  id: string;
  data: DNA;
  version: number;
  skills: Skill[];
};
export type Requirement = {
  skill: string;
  mandatory: boolean;
  description: string;
};
export type JobData = {
  title: string;
  company: string;
  location: string;
  description: string;
  url: string | null;
  source: string;
  work_model: string;
  seniority: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  salary_period: string;
  experience_months: number | null;
  education_level: number | null;
  requirements: Requirement[];
  responsibilities: string[];
  soft_skills: string[];
  benefits: string[];
  languages: string[];
  keywords: string[];
  published_at: string | null;
  deadline: string | null;
};
export type Application = {
  id: string;
  job_id: string;
  status: string;
  version: number;
  resume_id: string | null;
  updated_at: string;
};
export type Job = JobData & {
  archived_at: string | null;
  classification: string | null;
  coverage: number | null;
  id: string;
  score: number | null;
  favorite: boolean;
  created_at: string;
  application: Application;
  data: JobData;
};
export type AnalysisResult = {
  score: number;
  coverage: number;
  classification: string;
  reason: string;
  algorithm: string;
  blockers: string[];
  components: {
    name: string;
    score: number | null;
    weight: number;
    explanation: string;
  }[];
  requirements: (Requirement & {
    status: string;
    explanation: string;
    evidence: Evidence[];
  })[];
};
export type Draft = {
  id: string;
  body: string;
  kind: string;
  sent_at: string | null;
  created_at: string;
};
export type Advice = {
  body: string;
  citations: { source_id: string; quote: string }[];
  missing_information: string[];
};
export type Interview = {
  id: string;
  title: string;
  kind: string;
  scheduled_at: string;
  notes: string;
  feedback: string;
  preparation: Advice | null;
  checklist: string[];
};
export type Followup = {
  id: string;
  due_at: string;
  status: string;
  completed_at: string | null;
};
export type JobDetail = Job & {
  analysis: { id: string; result: AnalysisResult; created_at: string } | null;
  analysis_stale: boolean;
  events: { id: string; title: string; kind: string; created_at: string }[];
  notes: { id: string; body: string; created_at: string }[];
  contacts: {
    id: string;
    name: string;
    email: string | null;
    url: string | null;
    role: string;
  }[];
  messages: Draft[];
  followups: Followup[];
  interviews: Interview[];
};
export type JobPage = {
  items: Job[];
  total: number;
  page: number;
  per_page: number;
};
export type Document = {
  applications?: { id: string; job_id: string; title: string }[];
  id: string;
  name: string;
  kind: string;
  text: string;
  content_type: string;
  created_at: string;
  extracted: { profile: DNA; skills: Skill[]; warnings: string[] } | null;
};
export type Gap = {
  sample_size: number;
  scope: string;
  skills: {
    skill: string;
    count: number;
    percentage: number;
    category: string;
    high_impact: boolean;
    mandatory_count: number;
  }[];
};
export type Overview = {
  jobs: number;
  analyzed: number;
  high_matches: number;
  new_jobs: number;
  applications: number;
  replies: number;
  response_rate: number | null;
  application_rate: number | null;
  interview_count: number;
  technical_interviews: number;
  offers: number;
  rejections: number;
  waiting: number;
  no_response: number;
  pipeline: {
    status: string;
    label: string;
    count: number;
    ever_reached: number;
  }[];
  followups: {
    id: string;
    job_id: string;
    title: string;
    company: string;
    due_at: string;
  }[];
  upcoming: {
    id: string;
    job_id: string;
    title: string;
    company: string;
    scheduled_at: string;
  }[];
  weekly: { week: string; applications: number }[];
  sources: Record<string, { applications: number; interviews: number }>;
  roles: Record<string, { applications: number; interviews: number }>;
  transition_days: Record<string, number>;
  rejection_reasons: Record<string, number>;
  score_ranges: { label: string; count: number }[];
};
export const STATES: Record<string, string> = {
  discovered: "Descoberta",
  saved: "Salva",
  analyzing: "Analisando",
  preparing: "Preparando",
  applied: "Candidatura enviada",
  recruiter: "Contato com recrutador",
  screening: "Triagem RH",
  hr_interview: "Entrevista RH",
  technical: "Entrevista técnica",
  case: "Case / Teste",
  final: "Entrevista final",
  offer: "Oferta",
  hired: "Contratado",
  rejected: "Rejeitado",
  withdrawn: "Desistência",
  no_response: "Sem resposta",
};
export const MODES: Record<string, string> = {
  unknown: "Não informado",
  remote: "Remoto",
  hybrid: "Híbrido",
  onsite: "Presencial",
};
export const SENIORITIES: Record<string, string> = {
  unknown: "Não informada",
  intern: "Estágio",
  junior: "Júnior",
  mid: "Pleno",
  senior: "Sênior",
  lead: "Liderança",
};
export const PRIORITIES: Record<string, string> = {
  high: "Prioridade alta",
  worth: "Vale candidatura",
  review: "Analisar",
  low: "Baixa prioridade",
};
export const COMPONENTS: Record<string, string> = {
  technical: "Compatibilidade técnica",
  experience: "Experiência",
  education: "Formação",
  career_goal: "Objetivo profissional",
  location: "Localização",
  work_model: "Modelo de trabalho",
  salary: "Salário",
  evidence: "Evidências de portfólio",
  skill_gap: "Cobertura de requisitos",
  seniority: "Senioridade",
};
