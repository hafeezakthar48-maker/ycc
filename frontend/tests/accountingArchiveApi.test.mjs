import assert from "node:assert/strict";
import test from "node:test";

import {
  createAccountingArchiveCase,
  downloadAccountingArchivePackage,
  fetchAccountingArchiveDocuments
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const payload = payloads[url] ?? payloads.default ?? {};
    return {
      ok: true,
      status: 200,
      headers: {
        get: (name) => name.toLowerCase() === "content-disposition"
          ? 'attachment; filename="accounting-archive-default-2026-06-voucher.zip"'
          : null
      },
      json: async () => payload,
      blob: async () => new Blob(["zip"], { type: "application/zip" })
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("会计档案 API helper 获取文档、创建案卷并下载归档包", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/accounting-archive/documents?account_set_id=default&period=2026-06": {
      total: 1,
      documents: [{ archive_document_id: "arch_doc_1", filename: "invoice.txt" }]
    },
    "http://api.local/api/v1/accounting-archive/cases": {
      archive_case_id: "arch_case_1",
      document_count: 1
    }
  });

  const documents = await fetchAccountingArchiveDocuments("default", "2026-06", "http://api.local", fetcher);
  const archiveCase = await createAccountingArchiveCase(
    {
      account_set_id: "default",
      period: "2026-06",
      case_type: "voucher",
      title: "2026-06 凭证档案",
      document_ids: ["arch_doc_1"],
      created_by: "finance-manager"
    },
    "http://api.local",
    fetcher
  );
  const download = await downloadAccountingArchivePackage("arch_case_1", "http://api.local", fetcher);

  assert.equal(documents.total, 1);
  assert.equal(archiveCase.archive_case_id, "arch_case_1");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.equal(fetcher.calls[1].init.method, "POST");
  assert.equal(JSON.parse(fetcher.calls[1].init.body).document_ids[0], "arch_doc_1");
  assert.equal(
    fetcher.calls.at(-1).url,
    "http://api.local/api/v1/accounting-archive/cases/arch_case_1/download"
  );
  assert.equal(download.filename, "accounting-archive-default-2026-06-voucher.zip");
});
