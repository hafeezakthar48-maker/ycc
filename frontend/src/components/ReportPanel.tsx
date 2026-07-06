import { useState } from "react";
import { downloadManagementReport } from "../services/dashboardApi";
import type { ManagementReport } from "../types/dashboard";

interface ReportPanelProps {
  report: ManagementReport;
}

export default function ReportPanel({ report }: ReportPanelProps) {
  const [exporting, setExporting] = useState<"docx" | "pdf" | null>(null);

  async function handleExport(format: "docx" | "pdf") {
    setExporting(format);
    try {
      await downloadManagementReport(report, format);
    } finally {
      setExporting(null);
    }
  }

  return (
    <section className="panel report-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">AI 报告</span>
          <h2>{report.title}</h2>
        </div>
        <div className="report-actions">
          <button
            type="button"
            className="button-secondary"
            onClick={() => handleExport("docx")}
            disabled={exporting !== null}
          >
            {exporting === "docx" ? "导出中..." : "导出 Word"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => handleExport("pdf")}
            disabled={exporting !== null}
          >
            {exporting === "pdf" ? "导出中..." : "导出 PDF"}
          </button>
        </div>
      </div>
      <div className="report-sections">
        {report.sections.map((section) => (
          <article key={section.title}>
            <h3>{section.title}</h3>
            <p>{section.content}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
