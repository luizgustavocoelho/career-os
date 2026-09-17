import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "@/components/session";

export const metadata: Metadata = {
  title: "CareerOS — sua próxima oportunidade",
  description:
    "Seu sistema pessoal para uma busca profissional com clareza, contexto e evidências.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
