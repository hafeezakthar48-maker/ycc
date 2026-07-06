import { useEffect, useState } from "react";
import DataEntryPanel from "./components/DataEntryPanel";
import DashboardLayout from "./components/DashboardLayout";
import osModuleDefinitions from "./navigation/osModules.json";
import {
  analyzeRecords,
  analyzeHomeDashboard,
  fetchHomeDashboard,
  fetchOverview,
  fetchReport,
  fetchSampleData
} from "./services/dashboardApi";
import { fetchModuleRegistry, mergeModuleRegistry } from "./services/moduleRegistryApi";
import type { DashboardOverview, ManagementReport, MonthlyFinanceRecord } from "./types/dashboard";
import type { HomeDashboard } from "./types/homeDashboard";
import type { NavigationOsModule } from "./types/moduleRegistry";

const DEFAULT_PERIOD = "2026-06";
const LOCAL_OS_MODULES = osModuleDefinitions as NavigationOsModule[];

export default function App() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [homeDashboard, setHomeDashboard] = useState<HomeDashboard | null>(null);
  const [report, setReport] = useState<ManagementReport | null>(null);
  const [records, setRecords] = useState<MonthlyFinanceRecord[]>([]);
  const [osModules, setOsModules] = useState<NavigationOsModule[]>(LOCAL_OS_MODULES);
  const [showDataEntry, setShowDataEntry] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const [homePayload, overviewPayload, reportPayload, sampleRecords, backendModules] = await Promise.all([
          fetchHomeDashboard(DEFAULT_PERIOD),
          fetchOverview(DEFAULT_PERIOD),
          fetchReport(DEFAULT_PERIOD),
          fetchSampleData(),
          fetchModuleRegistry().catch(() => [])
        ]);

        if (!cancelled) {
          setHomeDashboard(homePayload);
          setOverview(overviewPayload);
          setReport(reportPayload);
          setOsModules(mergeModuleRegistry(LOCAL_OS_MODULES, backendModules));
          const stored = window.localStorage.getItem("finance_ai_manual_records");
          setRecords(stored ? JSON.parse(stored) as MonthlyFinanceRecord[] : sampleRecords);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载驾驶舱失败");
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!homeDashboard || !overview || !report || !window.location.hash) {
      return;
    }
    const scrollToHash = () => {
      document.querySelector(window.location.hash)?.scrollIntoView({ block: "start" });
    };
    window.requestAnimationFrame(scrollToHash);
    window.setTimeout(scrollToHash, 350);
  }, [homeDashboard, overview, report]);

  if (error) {
    return (
      <main className="app-state">
        <h1>China Finance AI Assistant</h1>
        <p>{error}</p>
        <p>请确认后端服务已启动：http://127.0.0.1:8000/health</p>
      </main>
    );
  }

  if (!homeDashboard || !overview || !report) {
    return (
      <main className="app-state">
        <h1>China Finance AI Assistant</h1>
        <p>正在加载示例企业经营分析驾驶舱...</p>
      </main>
    );
  }

  async function applyRecords(nextRecords: MonthlyFinanceRecord[], period: string) {
    const [response, homePayload] = await Promise.all([
      analyzeRecords(period, nextRecords),
      analyzeHomeDashboard(period, nextRecords)
    ]);
    setHomeDashboard(homePayload);
    setOverview(response.overview);
    setReport(response.report);
    setRecords(nextRecords);
    window.localStorage.setItem("finance_ai_manual_records", JSON.stringify(nextRecords));
    setShowDataEntry(false);
  }

  async function restoreSampleData() {
    const sampleRecords = await fetchSampleData();
    const response = await analyzeRecords(DEFAULT_PERIOD, sampleRecords);
    const homePayload = await fetchHomeDashboard(DEFAULT_PERIOD);
    setHomeDashboard(homePayload);
    setOverview(response.overview);
    setReport(response.report);
    setRecords(sampleRecords);
    window.localStorage.removeItem("finance_ai_manual_records");
    setShowDataEntry(false);
  }

  return (
    <>
      <DashboardLayout
        modules={osModules}
        homeDashboard={homeDashboard}
        overview={overview}
        report={report}
        onOpenDataEntry={() => setShowDataEntry(true)}
      />
      {showDataEntry ? (
        <DataEntryPanel
          records={records}
          defaultPeriod={overview.period}
          onApply={applyRecords}
          onRestoreSample={restoreSampleData}
          onClose={() => setShowDataEntry(false)}
        />
      ) : null}
    </>
  );
}
