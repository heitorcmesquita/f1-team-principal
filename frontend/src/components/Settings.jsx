import { useState } from "react";
import { api } from "../api";

export default function Settings({ playerTeam }) {
  const [exporting, setExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);

  async function handleExport() {
    try {
      setExporting(true);
      const resp = await api.get("/race/export");
      const csv = resp.data && resp.data.csv;
      if (!csv) return;
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "telemetry.csv";
      a.click();
      URL.revokeObjectURL(url);
      setExportDone(true);
      setTimeout(() => setExportDone(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="shell-panel">
      <div className="shell-panel-head">
        <h2>Settings</h2>
      </div>

      <div className="settings-stack">
        <section className="panel-card">
          <h3>Data</h3>
          <p className="settings-desc">
            Export the current race lap telemetry as a CSV file for analysis.
          </p>
          <button className="export-btn" onClick={handleExport} disabled={exporting}>
            {exporting ? "Exporting..." : exportDone ? "Downloaded ✓" : "Export Telemetry (CSV)"}
          </button>
        </section>

        <section className="panel-card">
          <h3>About</h3>
          <p className="settings-desc">
            F1 Team Principal — manage your drivers, tyres and strategy across a full season.
            {playerTeam ? ` You are managing ${playerTeam.name}.` : ""}
          </p>
        </section>
      </div>
    </div>
  );
}
