"use client";
import { Plus, Trash2 } from "lucide-react";
import { Entry } from "@/lib/types";
import { Field } from "./ui";
export function EntryEditor({
  title,
  entries,
  onChange,
}: {
  title: string;
  entries: Entry[];
  onChange: (entries: Entry[]) => void;
}) {
  const set = (index: number, key: keyof Entry, value: string) =>
    onChange(entries.map((e, i) => (i === index ? { ...e, [key]: value } : e)));
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>{title}</h3>
        <button
          type="button"
          className="button"
          onClick={() =>
            onChange([
              ...entries,
              {
                title: "",
                organization: "",
                description: "",
                start: "",
                end: "",
                url: "",
              },
            ])
          }
        >
          <Plus size={15} />
          Adicionar
        </button>
      </div>
      {entries.length === 0 && (
        <p className="muted">
          Registre informações reais. Detalhes e resultados ajudam a construir
          seu contexto.
        </p>
      )}
      {entries.map((entry, i) => (
        <div className="entry-editor" key={i}>
          <div className="form-grid">
            <Field label="Título / cargo / curso">
              <input
                required
                value={entry.title}
                onChange={(e) => set(i, "title", e.target.value)}
              />
            </Field>
            <Field label="Empresa / instituição">
              <input
                value={entry.organization}
                onChange={(e) => set(i, "organization", e.target.value)}
              />
            </Field>
            <Field label="Início">
              <input
                placeholder="AAAA-MM"
                maxLength={10}
                value={entry.start}
                onChange={(e) => set(i, "start", e.target.value)}
              />
            </Field>
            <Field label="Fim">
              <input
                placeholder="AAAA-MM ou Atual"
                maxLength={10}
                value={entry.end}
                onChange={(e) => set(i, "end", e.target.value)}
              />
            </Field>
          </div>
          <Field label="Descrição, contribuição e resultados reais">
            <textarea
              rows={3}
              value={entry.description}
              onChange={(e) => set(i, "description", e.target.value)}
            />
          </Field>
          <div className="inline-form">
            <Field label="Link de referência">
              <input
                type="url"
                value={entry.url}
                onChange={(e) => set(i, "url", e.target.value)}
              />
            </Field>
            <button
              type="button"
              className="icon-button danger"
              aria-label="Remover registro"
              onClick={() => onChange(entries.filter((_, n) => n !== i))}
            >
              <Trash2 size={17} />
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}
