import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("企业设置接入联网更新中心并展示每月一号自动更新", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/UpdateCenterPanel.tsx"), "utf8");

  assert.match(layout, /UpdateCenterPanel/);
  assert.match(panel, /fetchUpdateCenterStatus/);
  assert.match(panel, /checkUpdateCenterNow/);
  assert.match(panel, /checkApplicationUpdateNow/);
  assert.match(panel, /每月 1 号/);
  assert.match(panel, /联网更新中心/);
  assert.match(panel, /软件本体更新/);
});
