# 资讯库 HTTPS 源发布实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 发布一个只包含公开官方财税摘要的 HTTPS 资讯清单与 feed，并让桌面版成功联网刷新。

**Architecture:** 在独立发布分支中维护一个 manifest 和一个全国税务 feed；使用标准库测试校验 JSON 契约、HTTPS 边界、官方来源域名与无企业数据约束。发布后通过 GitHub Raw 地址供桌面版读取，再保存到本机应用设置并调用现有刷新接口验收。

**Tech Stack:** JSON、Python 3 `unittest`、Git/GitHub、现有中国财务 AI 助手更新与资讯库 API。

## Global Constraints

- 仅发布公开政策摘要和官方原文链接，不上传企业财务数据、账套信息、令牌或本机路径。
- manifest、feed 和每条文章来源必须使用 HTTPS。
- 首批文章来源限于 `chinatax.gov.cn` 官方域名。
- 发布分支固定为 `codex/information-source-publication`，避免推送当前开发分支的其他提交。
- 桌面配置使用发布分支的 GitHub Raw manifest；合并到 `main` 后再迁移到主分支地址。

---

### Task 1: 建立发布契约测试

**Files:**
- Create: `tests/test_information_source_distribution.py`

**Interfaces:**
- Consumes: `updates/information-manifest.json` 与 `updates/information-feeds/national-tax-2026.json`。
- Produces: `python -m unittest tests.test_information_source_distribution -v` 的自动验收入口。

- [ ] **Step 1: 写入会因发布文件不存在而失败的测试**

```python
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "updates" / "information-manifest.json"
FEED = ROOT / "updates" / "information-feeds" / "national-tax-2026.json"


class InformationSourceDistributionTests(unittest.TestCase):
    def test_manifest_and_feed_are_safe_public_https_artifacts(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        feed = json.loads(FEED.read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 1)
        self.assertEqual(len(manifest["sources"]), 1)
        self.assertEqual(urlparse(manifest["sources"][0]["url"]).scheme, "https")
        self.assertGreaterEqual(len(feed["articles"]), 5)
        for article in feed["articles"]:
            parsed = urlparse(article["source_url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.hostname == "chinatax.gov.cn" or parsed.hostname.endswith(".chinatax.gov.cn"))
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `python -m unittest tests.test_information_source_distribution -v`

Expected: `FileNotFoundError` 指向 `updates/information-manifest.json`，证明测试会捕获缺失发布物。

### Task 2: 创建清单与官方资讯 feed

**Files:**
- Create: `updates/information-manifest.json`
- Create: `updates/information-feeds/national-tax-2026.json`
- Modify: `tests/test_information_source_distribution.py`

**Interfaces:**
- Consumes: 国家税务总局政策法规库公开原文链接。
- Produces: 现有 `InformationManifest` 与 `InformationFeedPayload` 可读取的 JSON。

- [ ] **Step 1: 创建 manifest**

```json
{
  "manifest_version": 1,
  "version": "2026.07.13",
  "published_at": "2026-07-13T22:00:00+08:00",
  "sources": [
    {
      "id": "national-tax-2026",
      "name": "国家税务总局政策法规库（2026）",
      "url": "https://raw.githubusercontent.com/hafeezakthar48-maker/ycc/refs/heads/codex/information-source-publication/updates/information-feeds/national-tax-2026.json",
      "enabled": true,
      "ttl_hours": 168,
      "reliability": "official",
      "region": "全国"
    }
  ]
}
```

- [ ] **Step 2: 创建包含至少五条官方资讯的 feed**

每条资讯必须包含稳定 ID、标题、来源、分类、地区、发布日期、更新时间、HTTPS 官方原文、关键词、短摘要、复核提示和 `official` 可靠性标记。

- [ ] **Step 3: 加强测试，校验唯一 ID、必填字段、禁止企业数据字段**

```python
article_ids = [article["id"] for article in feed["articles"]]
self.assertEqual(len(article_ids), len(set(article_ids)))
serialized = json.dumps({"manifest": manifest, "feed": feed}, ensure_ascii=False).lower()
for forbidden in ("company_name", "account_set_id", "session_token", "localappdata"):
    self.assertNotIn(forbidden, serialized)
```

- [ ] **Step 4: 运行测试并确认 GREEN**

Run: `python -m unittest tests.test_information_source_distribution -v`

Expected: `OK`，1 个测试通过。

### Task 3: 发布并配置桌面版

**Files:**
- Modify: `README.md`
- Runtime config: `%LOCALAPPDATA%/ChinaFinanceAIAssistant/app-settings.json`

**Interfaces:**
- Consumes: GitHub Raw manifest URL。
- Produces: 可公开访问的发布分支、草稿 PR、桌面版资讯库缓存和来源状态。

- [ ] **Step 1: 在 README 记录 manifest 地址、用途与安全边界**

- [ ] **Step 2: 复跑发布契约测试并检查提交范围**

Run: `python -m unittest tests.test_information_source_distribution -v`

Expected: `OK`。

Run: `git status -sb`

Expected: 仅 README、计划、测试和 `updates` 发布物发生变化。

- [ ] **Step 3: 提交、推送独立分支并创建草稿 PR**

Commit: `feat: publish finance information source`

Push: `git push -u origin codex/information-source-publication`

PR target: `hafeezakthar48-maker/ycc:main`。

- [ ] **Step 4: 从 GitHub Raw 读取 manifest 与 feed**

Expected: 两个 URL 均返回 HTTP 200，JSON 可解析，文章来源均为官方 HTTPS。

- [ ] **Step 5: 保存桌面资讯源并执行联网刷新**

保存 `information_source_url` 后调用现有资讯库刷新 API；预期状态为 `updated`，文章数不少于 5，来源状态为已更新。

- [ ] **Step 6: 在桌面界面确认资讯库不再显示“未配置资讯源”**

Expected: 界面显示来源名称、最近更新时间和官方资讯列表；外链仍由用户主动打开并要求人工复核。

