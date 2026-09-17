"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, Dna, ShieldCheck, Target } from "lucide-react";
import { api, post } from "@/lib/api";
import { User } from "@/lib/types";
import { useSession } from "@/components/session";
import { ErrorBox, Field } from "@/components/ui";
const schema = z.object({
  name: z.string().max(160),
  email: z.email("Informe um e-mail válido."),
  password: z.string().min(12, "Use pelo menos 12 caracteres.").max(128),
});
type Form = z.infer<typeof schema>;
export default function Login() {
  const [registering, setRegistering] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const { user, setUser } = useSession();
  const router = useRouter();
  const [destination, setDestination] = useState("/");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", password: "" },
  });
  useEffect(() => {
    api<{ registration_open: boolean }>("/auth/config")
      .then((c) => {
        setOpen(c.registration_open);
        setRegistering(c.registration_open);
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (user) router.replace(destination);
  }, [user, router, destination]);
  async function submit(data: Form) {
    setError("");
    try {
      const u = await post<User>(
        registering ? "/auth/register" : "/auth/login",
        data,
      );
      setDestination(registering ? "/profile" : "/");
      setUser(u);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="auth-page">
      <div className="auth-story">
        <div className="brand light">
          <span className="brand-mark">
            <Dna />
          </span>
          career<span>os</span>
        </div>
        <div className="auth-pitch">
          <span className="eyebrow">SUA CARREIRA, COM DIREÇÃO</span>
          <h1>
            O próximo passo
            <br />
            merece mais
            <br />
            <em>clareza.</em>
          </h1>
          <p>
            Conecte quem você é às oportunidades que fazem sentido. Organize sua
            busca, encontre evidências e avance com intenção.
          </p>
          <div className="auth-principles">
            <span>
              <Target size={18} />
              Oportunidades com contexto
            </span>
            <span>
              <ShieldCheck size={18} />
              Sua história, sem invenções
            </span>
          </div>
        </div>
        <small>Um workspace pessoal. Um novo capítulo.</small>
      </div>
      <div className="auth-form-wrap">
        <form className="auth-form" onSubmit={handleSubmit(submit)}>
          <span className="eyebrow">BEM-VINDO AO SEU WORKSPACE</span>
          <h2>
            {registering
              ? "Comece pela sua história."
              : "Bom ter você de volta."}
          </h2>
          <p>
            {registering
              ? "Crie sua conta para construir seu Career DNA."
              : "Entre para continuar de onde parou."}
          </p>
          <ErrorBox message={error} />
          {registering && (
            <Field label="Seu nome">
              <input autoComplete="name" {...register("name")} required />
            </Field>
          )}
          <Field label="E-mail">
            <input type="email" autoComplete="email" {...register("email")} />
            {errors.email && (
              <small className="text-danger">{errors.email.message}</small>
            )}
          </Field>
          <Field label="Senha" hint="Pelo menos 12 caracteres.">
            <input
              type="password"
              autoComplete={registering ? "new-password" : "current-password"}
              {...register("password")}
            />
            {errors.password && (
              <small className="text-danger">{errors.password.message}</small>
            )}
          </Field>
          <button className="primary button full" disabled={isSubmitting}>
            {isSubmitting
              ? "Aguarde…"
              : registering
                ? "Criar meu workspace"
                : "Entrar no workspace"}
            <ArrowRight size={18} />
          </button>
          {open && (
            <button
              type="button"
              className="text-button full"
              onClick={() => setRegistering(!registering)}
            >
              {registering ? "Já tenho conta. Entrar" : "Criar uma conta"}
            </button>
          )}
          <small className="auth-privacy">
            Seus dados ficam nesta instalação. O envio de contexto para IA
            depende da sua autorização no perfil.
          </small>
        </form>
      </div>
    </div>
  );
}
