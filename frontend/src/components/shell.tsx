"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Bell,
  CalendarDays,
  ChevronRight,
  Dna,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Radar,
  Search,
  Sparkles,
  Sun,
  Target,
  X,
  Columns3,
  Settings2,
} from "lucide-react";
import { api, post } from "@/lib/api";
import { useSession } from "./session";
import { Loading } from "./ui";

const nav = [
  { href: "/", label: "Visão geral", icon: LayoutDashboard },
  { href: "/radar", label: "Opportunity Radar", icon: Radar },
  { href: "/pipeline", label: "Candidaturas", icon: Columns3 },
  { href: "/interviews", label: "Entrevistas", icon: CalendarDays },
  { href: "/coach", label: "Career Coach", icon: Sparkles },
  { href: "/gaps", label: "Career Gap", icon: Target },
  { href: "/analytics", label: "Analytics", icon: Activity },
];
type Notice = {
  id: string;
  title: string;
  job_id: string | null;
  read: boolean;
};
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, setUser } = useSession();
  const [mobile, setMobile] = useState(false);
  const [dark, setDark] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{
    jobs: { id: string; title: string; company: string }[];
    contacts: { id: string; name: string; job_id: string }[];
    skills: { id: string; name: string }[];
  } | null>(null);
  const [notices, setNotices] = useState<Notice[] | null>(null);
  const [noticeError, setNoticeError] = useState("");
  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);
  useEffect(() => {
    const saved = localStorage.getItem("careeros-theme") === "dark";
    document.documentElement.dataset.theme = saved ? "dark" : "light";
  }, []);
  useEffect(() => {
    if (q.length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api<typeof results>(`/search?q=${encodeURIComponent(q)}`, {
        signal: controller.signal,
      })
        .then(setResults)
        .catch(() => {});
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q]);
  if (loading || !user) return <Loading />;
  const toggleTheme = () => {
    const next = document.documentElement.dataset.theme !== "dark";
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem("careeros-theme", next ? "dark" : "light");
  };
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <Link href="/" className="brand">
          <span className="brand-mark">
            <Dna size={24} />
          </span>
          career<span>os</span>
          <span className="version">1.0</span>
        </Link>
        <button
          className="mobile-close icon-button"
          aria-label="Fechar menu"
          onClick={() => setMobile(false)}
        >
          <X />
        </button>
        <div className="workspace-label">
          <span className="workspace-avatar">
            {user.name.charAt(0).toUpperCase()}
          </span>
          <div>
            <b>Meu workspace</b>
            <small>Carreira em movimento</small>
          </div>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>
          {nav.map((n) => (
            <Link
              onClick={() => setMobile(false)}
              key={n.href}
              href={n.href}
              className={
                (
                  n.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(n.href)
                )
                  ? "active"
                  : ""
              }
            >
              <n.icon size={18} />
              {n.label}
              {n.href === "/coach" && <span className="nav-ai">AI</span>}
            </Link>
          ))}
        </nav>
        <div className="nav-caption">MINHA BASE</div>
        <nav>
          <Link
            className={pathname === "/profile" ? "active" : ""}
            href="/profile"
          >
            <Dna size={18} />
            Career DNA
          </Link>
          <Link
            className={pathname === "/documents" ? "active" : ""}
            href="/documents"
          >
            <FileText size={18} />
            Documentos
          </Link>
          <Link
            className={pathname === "/settings" ? "active" : ""}
            href="/settings"
          >
            <Settings2 size={18} />
            Configurações
          </Link>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="status-dot" />
            Seu próximo passo começa aqui.
            <small>Clareza para decidir. Contexto para agir.</small>
          </div>
          <button
            className="account"
            onClick={async () => {
              await post("/auth/logout");
              setUser(null);
              router.replace("/login");
            }}
            title="Sair da conta"
          >
            <span className="avatar">{user.name.charAt(0).toUpperCase()}</span>
            <span>
              <b>{user.name}</b>
              <small>Conta pessoal</small>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Abrir menu"
            onClick={() => setMobile(true)}
          >
            <Menu />
          </button>
          <div className="breadcrumb">
            Workspace
            <ChevronRight size={14} />
            <span>
              {nav.find((n) => n.href === pathname)?.label ||
                (pathname.startsWith("/jobs/")
                  ? "Oportunidade"
                  : pathname === "/profile"
                    ? "Career DNA"
                    : pathname === "/documents"
                      ? "Documentos"
                      : "Configurações")}
            </span>
          </div>
          <div className="top-actions">
            <div className="global-search">
              <Search size={16} />
              <input
                aria-label="Pesquisa global"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar no workspace…"
              />
              {q.length >= 2 && results && (
                <div className="search-results">
                  {results.jobs.map((j) => (
                    <Link
                      key={j.id}
                      href={`/jobs/${j.id}`}
                      onClick={() => setQ("")}
                    >
                      {j.title}
                      <small>{j.company}</small>
                    </Link>
                  ))}
                  {results.contacts.map((c) => (
                    <Link
                      key={c.id}
                      href={`/jobs/${c.job_id}`}
                      onClick={() => setQ("")}
                    >
                      Contato: {c.name}
                    </Link>
                  ))}
                  {results.skills.map((s) => (
                    <Link key={s.id} href="/profile" onClick={() => setQ("")}>
                      Skill: {s.name}
                    </Link>
                  ))}
                  {!results.jobs.length &&
                    !results.contacts.length &&
                    !results.skills.length && <p>Nenhum resultado.</p>}
                </div>
              )}
            </div>
            <button
              className="icon-button"
              aria-label="Alternar tema"
              onClick={toggleTheme}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <div className="notification-wrap">
              <button
                className="icon-button"
                aria-label="Notificações"
                onClick={async () => {
                  if (notices) {
                    setNotices(null);
                    return;
                  }
                  try {
                    setNotices(await api<Notice[]>("/notifications"));
                    setNoticeError("");
                  } catch (e) {
                    setNoticeError((e as Error).message);
                  }
                }}
              >
                <Bell size={18} />
              </button>
              {(notices || noticeError) && (
                <div className="notifications">
                  <h3>Notificações</h3>
                  {noticeError && <p>{noticeError}</p>}
                  {notices?.length === 0 && <p>Você está em dia.</p>}
                  {notices?.map((n) => (
                    <button
                      key={n.id}
                      className={n.read ? "muted" : ""}
                      onClick={async () => {
                        await post(`/notifications/${n.id}/read`);
                        setNotices(null);
                        if (n.job_id) router.push(`/jobs/${n.job_id}`);
                      }}
                    >
                      {n.title}
                      <ArrowUpRight size={15} />
                    </button>
                  ))}
                </div>
              )}
            </div>
            <span className="avatar top-avatar">
              {user.name.charAt(0).toUpperCase()}
            </span>
          </div>
        </header>
        <main className="main-content">{children}</main>
        <footer className="footer">
          CareerOS <span>Decisões melhores. Uma oportunidade de cada vez.</span>
        </footer>
      </div>
    </div>
  );
}
