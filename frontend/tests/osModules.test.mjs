import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

const modulesPath = resolve("src/navigation/osModules.json");

async function loadModules() {
  const content = await readFile(modulesPath, "utf8");
  return JSON.parse(content);
}

test("China Finance AI OS 注册十二个一级模块", async () => {
  const modules = await loadModules();

  assert.equal(modules.length, 12);
  assert.deepEqual(
    modules.map((module) => module.id),
    [
      "ai-home",
      "finance-center",
      "tax-center",
      "analysis-center",
      "bi-center",
      "ecommerce-center",
      "ocr-center",
      "knowledge-base",
      "ai-assistant",
      "risk-center",
      "system-admin",
      "open-platform"
    ]
  );
});

test("现有 MVP 功能归入 FRD 对应模块", async () => {
  const modules = await loadModules();
  const byId = Object.fromEntries(modules.map((module) => [module.id, module]));

  assert.ok(byId["ai-home"].items.some((item) => item.anchor === "ai-home"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "voucher-center"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "accounting-archive-panel"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "receivable-payable-panel"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "fixed-asset-panel"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "payroll-panel"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "financial-statements-panel"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "voucher-draft"));
  assert.ok(byId["finance-center"].items.some((item) => item.anchor === "audit-review"));
  assert.ok(byId["tax-center"].items.some((item) => item.anchor === "policy-library"));
  assert.ok(byId["analysis-center"].items.some((item) => item.anchor === "profit"));
  assert.ok(byId["bi-center"].items.some((item) => item.anchor === "overview"));
  assert.ok(byId["ecommerce-center"].items.some((item) => item.anchor === "ecommerce"));
  assert.ok(byId["ocr-center"].items.some((item) => item.anchor === "invoice-ocr"));
  assert.ok(byId["ai-assistant"].items.some((item) => item.anchor === "finance-qa"));
  assert.ok(byId["risk-center"].items.some((item) => item.anchor === "risk"));
});

test("未落地模块保留规划状态和接入位", async () => {
  const modules = await loadModules();
  const planned = modules.filter((module) => module.status === "规划");

  assert.deepEqual(planned.map((module) => module.id), ["system-admin", "open-platform"]);
  assert.ok(planned.every((module) => module.items.length > 0));
});

test("每个一级模块都声明 FRD 规划能力和下一步接入点", async () => {
  const modules = await loadModules();

  assert.ok(modules.every((module) => Array.isArray(module.roadmap) && module.roadmap.length >= 3));
  assert.ok(modules.every((module) => typeof module.nextIntegration === "string" && module.nextIntegration.length > 0));
});

test("FRD 核心规划项覆盖财务、税务、BI、OCR、知识库、开放平台", async () => {
  const modules = await loadModules();
  const byId = Object.fromEntries(modules.map((module) => [module.id, module]));

  assert.ok(byId["finance-center"].roadmap.includes("总账"));
  assert.ok(byId["finance-center"].roadmap.includes("往来核算"));
  assert.ok(byId["finance-center"].roadmap.includes("固定资产"));
  assert.ok(byId["finance-center"].roadmap.includes("工资管理"));
  assert.ok(byId["tax-center"].roadmap.includes("企业所得税"));
  assert.ok(byId["tax-center"].roadmap.includes("出口退税"));
  assert.ok(byId["bi-center"].roadmap.includes("点击钻取分析"));
  assert.ok(byId["ocr-center"].roadmap.includes("银行回单"));
  assert.ok(byId["ocr-center"].roadmap.includes("Word扫描件"));
  assert.ok(byId["knowledge-base"].roadmap.includes("RAG知识库"));
  assert.ok(byId["knowledge-base"].roadmap.includes("版本管理"));
  assert.ok(byId["open-platform"].roadmap.includes("OAuth2"));
  assert.ok(byId["open-platform"].roadmap.includes("限流"));
});
