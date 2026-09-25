import { test, expect } from "@playwright/test";
test("busca persistida → worker → radar → arquivar/restaurar → follow-up", async ({
  page,
}) => {
  await page.goto("/login");
  const signup = page.getByRole("button", { name: "Criar conta", exact: true });
  if (await signup.isVisible()) await signup.click();
  await page.getByLabel("Seu nome", { exact: true }).fill("Radar E2E");
  await page
    .getByLabel("E-mail", { exact: true })
    .fill(`radar-${Date.now()}@example.com`);
  await page
    .getByLabel("Senha", { exact: true })
    .fill("Radar-testing-password-123!");
  await page.getByRole("button", { name: "Criar meu workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Career DNA", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Cargos desejados", { exact: false })
    .fill("Engenheiro de Dados");
  await page.getByRole("button", { name: "Salvar Career DNA" }).click();
  await expect(
    page.getByText("Career DNA salvo.", { exact: false }),
  ).toBeVisible();
  await page.goto("/radar");
  await page.getByText("Gerenciar buscas automáticas", { exact: true }).click();
  await page
    .getByLabel("Nome da busca", { exact: true })
    .fill("Minha busca de dados");
  await page.getByLabel("Termos de busca", { exact: true }).fill("Python");
  await page.getByRole("button", { name: "Salvar busca", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Minha busca de dados" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Executar busca", exact: true })
    .click();
  await expect(page.getByText(/1 encontradas · 1 novas/)).toBeVisible({
    timeout: 30000,
  });
  await page.reload();
  const card = page
    .locator(".job-card")
    .filter({ hasText: "Empresa Radar E2E" });
  await expect(
    card.getByText("Opportunity Score", { exact: true }),
  ).toBeVisible();
  await card
    .getByRole("button", { name: "Arquivar vaga", exact: true })
    .click();
  await expect(card).toHaveCount(0);
  await page.getByLabel("Arquivadas", { exact: true }).check();
  await card
    .getByRole("button", { name: "Restaurar vaga", exact: true })
    .click();
  await page.getByLabel("Arquivadas", { exact: true }).uncheck();
  await card.getByRole("link", { name: "Engenheiro de Dados Fixture" }).click();
  await page.getByLabel("Etapa do pipeline").selectOption("applied");

  await page.reload();
  await expect(page.getByLabel("Etapa do pipeline")).toHaveValue("applied");
  await expect(page.locator(".follow-item").first()).toBeVisible();
  await page
    .getByRole("link", { name: "Selecionar fatos e exportar currículo" })
    .click();
  await page
    .getByRole("button", { name: "Revisar currículo selecionado" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Prévia para revisão" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Aprovar e salvar versão" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exportar DOCX", exact: true }).click();
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();
  const htmlLink = await page
    .getByRole("link", { name: "Exportar HTML para imprimir / PDF" })
    .getAttribute("href");
  const html = await page.request.get(htmlLink!);
  expect(html.status()).toBe(200);
  await page.screenshot({
    path: "test-results/resume-review.png",
    fullPage: true,
  });
  await page.goto("/settings");
  await expect(
    page.getByRole("heading", { name: "Diagnóstico", exact: true }),
  ).toBeVisible();
  const zip = await page.request.get("/api/export");
  expect(zip.status()).toBe(200);
  expect(zip.headers()["content-type"]).toContain("application/zip");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/radar");
  await page.getByText("Gerenciar buscas automáticas", { exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Minha busca de dados" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/radar-search-mobile.png",
    fullPage: true,
  });
});
