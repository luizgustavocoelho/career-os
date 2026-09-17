import { test, expect } from "@playwright/test";

function pdfFixture(): Buffer {
  const content =
    "BT /F1 12 Tf 50 780 Td (E2E Candidate) Tj 0 -20 Td (Python SQL - e2e@example.com) Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((o, i) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 6\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((o) => `${String(o).padStart(10, "0")} 00000 n \n`)
    .join("")}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(pdf);
}

test("conta → DNA → currículo → vaga → score → pipeline → entrevista → persistência", async ({
  page,
}) => {
  const errors: string[] = [];
  const email = `e2e-${Date.now()}@example.com`;
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/login");
  await page.getByLabel("Seu nome", { exact: true }).fill("Candidato E2E");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page
    .getByLabel("Senha", { exact: true })
    .fill("E2E-password-long-123!");
  await page.getByRole("button", { name: "Criar meu workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Career DNA", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Título profissional", { exact: true })
    .fill("Engenheiro de Dados");
  await page
    .getByLabel("Cargos desejados", { exact: false })
    .fill("Engenheiro de Dados");
  await page.getByLabel("Senioridade", { exact: true }).selectOption("junior");
  await page.getByLabel("Remoto", { exact: true }).check();
  await page.getByLabel("Cidade / região", { exact: true }).fill("São Paulo");
  await page.getByRole("button", { name: "Salvar Career DNA" }).click();
  await expect(
    page.getByText("Career DNA salvo.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Nova habilidade").fill("Python");
  await page.getByRole("button", { name: "Adicionar skill" }).click();
  await expect(
    page.locator(".skill-card").filter({ hasText: "Python" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Editar e adicionar evidência" })
    .click();
  await page
    .getByLabel("Título da evidência")
    .fill("Pipeline de dados públicos");
  await page
    .getByLabel("O que demonstra essa habilidade?", { exact: false })
    .fill(
      "Implementei em Python um pipeline que processa dados públicos de transporte.",
    );
  await page.getByRole("button", { name: "Salvar evidência" }).click();
  await expect(page.getByText("1 evidência(s)")).toBeVisible();
  await page.goto("/documents");
  await page.locator('input[type="file"]').setInputFiles({
    name: "curriculo-e2e.pdf",
    mimeType: "application/pdf",
    buffer: pdfFixture(),
  });
  await expect(
    page.getByRole("heading", { name: "curriculo-e2e.pdf" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Texto do documento", { exact: false }),
  ).toHaveValue(/E2E Candidate/);
  await expect(
    page.getByRole("link", { name: "Revisar no Career DNA" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Revisar no Career DNA" }).click();
  await expect(page.getByLabel("Nome", { exact: true })).toHaveValue(
    "E2E Candidate",
  );
  await page.getByLabel("Nome", { exact: true }).fill("Candidato E2E");
  await page.getByRole("button", { name: "Salvar Career DNA" }).click();
  await expect(
    page.getByText("Career DNA salvo.", { exact: false }),
  ).toBeVisible();
  await page.goto("/radar/new");
  await page
    .getByLabel("Descrição completa da vaga")
    .fill(
      "Construir pipelines de dados com Python e SQL. Experiência com AWS é um diferencial.",
    );
  await page.getByRole("button", { name: "Extrair termos localmente" }).click();
  await expect(
    page.getByText("Campos extraídos.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Cargo", { exact: true }).fill("Engenheiro de Dados");
  await page.getByLabel("Empresa", { exact: true }).fill("Empresa E2E");
  await page.getByLabel("Localização / restrição geográfica").fill("São Paulo");
  await page
    .getByLabel("Modelo de trabalho", { exact: true })
    .selectOption("remote");
  await page.getByLabel("Senioridade", { exact: true }).selectOption("junior");
  await page.getByRole("button", { name: "Salvar e analisar" }).click();
  await expect(
    page.getByRole("heading", { name: "Opportunity Score", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Com evidência", { exact: true })).toBeVisible();
  const jobUrl = page.url();
  await page
    .getByLabel("Documento utilizado")
    .selectOption({ label: "curriculo-e2e.pdf" });
  await page.getByRole("button", { name: "Já me candidatei" }).click();
  await expect(page.getByLabel("Etapa do pipeline")).toHaveValue("applied");
  await expect(page.getByText("Pendente", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Mensagens", exact: true }).click();
  await page.getByRole("button", { name: "Gerar rascunho" }).click();
  await expect(page.getByLabel("Mensagem editável")).toHaveValue(/Empresa E2E/);
  await page
    .getByLabel("Mensagem editável")
    .fill(
      "Olá! Tenho interesse na vaga de Engenheiro de Dados e gostaria de compartilhar meu projeto real.",
    );
  await page.getByRole("button", { name: "Salvar edição" }).click();
  await page.getByRole("button", { name: "Marcar como enviada" }).click();
  await expect(
    page.getByText("Envio registrado", { exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Entrevistas", exact: true }).click();
  await page.getByLabel("Título da entrevista").fill("Conversa técnica E2E");
  const next = new Date(Date.now() + 86400000);
  await page
    .getByLabel("Data e hora local")
    .fill(
      `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}T14:00`,
    );
  await page
    .getByRole("button", { name: "Agendar entrevista", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Conversa técnica E2E" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Preparar roteiro", exact: true })
    .click();
  await expect(
    page.getByText("STAR — PREENCHA COM FATOS", { exact: false }),
  ).toBeVisible();
  await page.goto("/pipeline");
  await page
    .getByLabel("Etapa de Engenheiro de Dados")
    .selectOption("technical");
  await expect(page.getByLabel("Etapa de Engenheiro de Dados")).toHaveValue(
    "technical",
  );
  await page.reload();
  await expect(page.getByLabel("Etapa de Engenheiro de Dados")).toHaveValue(
    "technical",
  );
  await page.goto(jobUrl);
  await page.getByRole("tab", { name: "Timeline" }).click();
  await expect(
    page.getByText("Candidatura enviada → Entrevista técnica", { exact: true }),
  ).toBeVisible();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Olá, Candidato/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/dashboard-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Alternar tema" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/dashboard-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByTitle("Sair da conta").click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("button", { name: "Já tenho conta. Entrar" }).click();
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page
    .getByLabel("Senha", { exact: true })
    .fill("E2E-password-long-123!");
  await page.getByRole("button", { name: "Entrar no workspace" }).click();
  await expect(
    page.getByRole("heading", { name: /Olá, Candidato/ }),
  ).toBeVisible();
  await page.goto(jobUrl);
  await expect(page.getByLabel("Etapa do pipeline")).toHaveValue("technical");
  expect(errors).toEqual([]);
});
