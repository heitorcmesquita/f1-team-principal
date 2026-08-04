import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const SAVE_KEY = "f1manager.save";

export default function Settings({ playerTeam, onLoaded }) {
  const [exporting, setExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);

  const [saveMeta, setSaveMeta] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveDone, setSaveDone] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [loadDone, setLoadDone] = useState(false);
  const [loadError, setLoadError] = useState("");

  const [importing, setImporting] = useState(false);
  const [importDone, setImportDone] = useState(false);
  const [resetDone, setResetDone] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    api
      .get("/race/save/meta")
      .then((r) => setSaveMeta(r.data))
      .catch(() => {});
  }, []);

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

  async function handleSave() {
    setSaving(true);
    try {
      const resp = await api.post("/race/save");
      setSaveMeta(resp.data);
      setSaveDone(true);
      setTimeout(() => setSaveDone(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleLoad() {
    setLoadingSave(true);
    setLoadError("");
    try {
      const resp = await api.post("/race/load");
      if (onLoaded) onLoaded(resp.data);
      setLoadDone(true);
      setTimeout(() => setLoadDone(false), 3000);
    } catch (err) {
      setLoadError(err?.response?.data?.detail || err?.message || "Failed to load save");
    } finally {
      setLoadingSave(false);
    }
  }

  const canSave = Boolean(playerTeam);
  const saveLabel = saveMeta?.lap != null ? `Lap ${saveMeta.lap} · ${saveMeta.circuit}` : saveMeta?.circuit || "—";

  async function handleExportSave() {
    try {
      const resp = await api.get("/race/save/data");
      const blob = new Blob([JSON.stringify(resp.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "f1-manager-save.json";
      a.click();
      URL.revokeObjectURL(url);
      setExportDone(true);
      setTimeout(() => setExportDone(false), 3000);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleImportFile(e) {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setImporting(true);
    setLoadError("");
    try {
      const text = await file.text();
      const blob = JSON.parse(text);
      const resp = await api.post("/race/load", blob);
      localStorage.setItem(SAVE_KEY, text);
      if (onLoaded) onLoaded(resp.data);
      setImportDone(true);
      setTimeout(() => setImportDone(false), 3000);
    } catch (err) {
      setLoadError(err?.response?.data?.detail || err?.message || "Failed to import save");
    } finally {
      setImporting(false);
    }
  }

  async function handleResetBrowser() {
    setLoadError("");
    try {
      await api.post("/race/reset");
      localStorage.removeItem(SAVE_KEY);
      if (onLoaded) onLoaded(null);
      setResetDone(true);
      setTimeout(() => setResetDone(false), 3000);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="shell-panel">
      <div className="shell-panel-head">
        <h2>Settings</h2>
      </div>

      <div className="settings-stack">
        <section className="panel-card">
          <h3>Save Game</h3>
          {canSave ? (
            <>
              <p className="settings-desc">
                Save your current season to disk. You can restore it from the Load card below, even
                after restarting the server.
              </p>
              <button className="export-btn" onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : saveDone ? "Saved ✓" : "Save Game"}
              </button>
              {saveDone && <p className="settings-hint">Save written for {playerTeam.name}.</p>}
            </>
          ) : (
            <p className="settings-desc">
              Start a season before saving — a save needs a player team and a live weekend.
            </p>
          )}
        </section>

        <section className="panel-card">
          <h3>Load Game</h3>
          {saveMeta && saveMeta.exists ? (
            <>
              <p className="settings-desc">
                {saveMeta.player_team ? `Save: ${saveMeta.player_team}` : "Save"} · {saveLabel} ·{" "}
                {saveMeta.saved_at}
              </p>
              <button className="export-btn" onClick={handleLoad} disabled={loadingSave}>
                {loadingSave ? "Loading..." : loadDone ? "Loaded ✓" : "Load Game"}
              </button>
              {loadError && <p className="settings-error">{loadError}</p>}
            </>
          ) : (
            <p className="settings-desc">No save file found yet. Save your game to enable loading.</p>
          )}
        </section>

        <section className="panel-card">
          <h3>My Save (Browser)</h3>
          <p className="settings-desc">
            Your game is saved automatically in this browser after every move. Export the save to
            back it up or move it to another device; import one to restore it.
          </p>
          <div className="settings-row">
            <button className="export-btn" onClick={handleExportSave}>
              {exportDone ? "Exported ✓" : "Export Save"}
            </button>
            <button className="export-btn" onClick={() => fileRef.current && fileRef.current.click()} disabled={importing}>
              {importing ? "Importing..." : importDone ? "Imported ✓" : "Import Save"}
            </button>
            <button className="export-btn" onClick={handleResetBrowser}>
              {resetDone ? "Reset ✓" : "Reset Game"}
            </button>
          </div>
          <input ref={fileRef} type="file" accept="application/json,.json" style={{ display: "none" }} onChange={handleImportFile} />
          {loadError && <p className="settings-error">{loadError}</p>}
        </section>

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
