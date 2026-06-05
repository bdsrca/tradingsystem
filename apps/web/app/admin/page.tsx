"use client";

import { type FormEvent, useEffect, useState } from "react";

import AppNav from "../../components/AppNav";
import {
  fetchJson,
  type AdminActionResult,
  type AdminHealth,
  type AdminSettings
} from "../../lib/api";

type EditableAdminSettings = Omit<AdminSettings, "secrets">;

const ADMIN_HEADER = "X-Admin-Passcode";
const ADMIN_PASSCODE = "8888";
const ADMIN_SESSION_KEY = "trading-system-admin-passcode";

export default function AdminPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [draft, setDraft] = useState<EditableAdminSettings | null>(null);
  const [health, setHealth] = useState<AdminHealth | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [adminPasscode, setAdminPasscode] = useState<string | null>(null);
  const [passcodeInput, setPasscodeInput] = useState("");

  function adminOptions(init: RequestInit = {}, passcode = adminPasscode): RequestInit {
    return {
      ...init,
      headers: {
        ...(init.headers as Record<string, string> | undefined),
        [ADMIN_HEADER]: passcode ?? ""
      }
    };
  }

  function clearAdminSession() {
    setAuthorized(false);
    setAdminPasscode(null);
    setSettings(null);
    setDraft(null);
    setHealth(null);
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
  }

  async function loadAdmin(passcode = adminPasscode) {
    if (!passcode) {
      return;
    }
    setError(null);
    try {
      const [loadedSettings, loadedHealth] = await Promise.all([
        fetchJson<AdminSettings>("/admin/settings", adminOptions({}, passcode)),
        fetchJson<AdminHealth>("/admin/health", adminOptions({}, passcode))
      ]);
      setSettings(loadedSettings);
      setDraft(toEditable(loadedSettings));
      setHealth(loadedHealth);
      setAuthorized(true);
    } catch (err) {
      if (err instanceof Error && err.message.includes("401")) {
        clearAdminSession();
      }
      setError(err instanceof Error ? err.message : "Failed to load admin");
    }
  }

  useEffect(() => {
    const saved = sessionStorage.getItem(ADMIN_SESSION_KEY);
    if (saved === ADMIN_PASSCODE) {
      setAdminPasscode(saved);
      void loadAdmin(saved);
    }
  }, []);

  async function unlockAdmin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);
    if (passcodeInput !== ADMIN_PASSCODE) {
      setError("Invalid admin password");
      return;
    }
    sessionStorage.setItem(ADMIN_SESSION_KEY, passcodeInput);
    setAdminPasscode(passcodeInput);
    await loadAdmin(passcodeInput);
  }

  async function saveSettings() {
    if (!draft) {
      return;
    }
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      const saved = await fetchJson<AdminSettings>(
        "/admin/settings",
        adminOptions({
          method: "PATCH",
          body: JSON.stringify(draft)
        })
      );
      setSettings(saved);
      setDraft(toEditable(saved));
      setStatus("Settings saved");
      setHealth(await fetchJson<AdminHealth>("/admin/health", adminOptions()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function runAdminAction(label: string, path: string) {
    setRunningAction(label);
    setStatus(null);
    setError(null);
    try {
      const result = await fetchJson<AdminActionResult>(path, adminOptions({ method: "POST" }));
      setStatus(`${label}: ${result.message}`);
      setHealth(await fetchJson<AdminHealth>("/admin/health", adminOptions()));
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`);
    } finally {
      setRunningAction(null);
    }
  }

  async function runDailyNow() {
    setRunningAction("Run daily now");
    setStatus(null);
    setError(null);
    try {
      await fetchJson("/daily/run", { method: "POST" });
      setStatus("Daily run completed");
      setHealth(await fetchJson<AdminHealth>("/admin/health", adminOptions()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Daily run failed");
    } finally {
      setRunningAction(null);
    }
  }

  function update<K extends keyof EditableAdminSettings>(key: K, value: EditableAdminSettings[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Admin</h1>
          <p>Runtime settings and service health.</p>
        </div>
        <AppNav />
      </header>

      {!authorized ? (
        <section className="admin-login" aria-label="Admin login">
          <h2>Admin password</h2>
          <form className="inline-form" onSubmit={(event) => void unlockAdmin(event)}>
            <input
              autoComplete="current-password"
              autoFocus
              onChange={(event) => setPasscodeInput(event.target.value)}
              placeholder="Password"
              type="password"
              value={passcodeInput}
            />
            <button type="submit">Unlock</button>
          </form>
          {error ? <p className="error">{error}</p> : null}
        </section>
      ) : (
        <>
          <div className="action-row">
            <button disabled={saving || !draft} onClick={saveSettings} type="button">
              {saving ? "Saving" : "Save settings"}
            </button>
            <button onClick={() => void loadAdmin()} type="button">
              Refresh health
            </button>
            <button className="secondary-button" onClick={clearAdminSession} type="button">
              Lock
            </button>
            {status ? <span>{status}</span> : null}
          </div>

          {error ? <p className="error">{error}</p> : null}

          {draft && settings ? (
            <>
              <section className="admin-section" aria-label="Settings">
                <h2>Settings</h2>
                <div className="settings-grid">
                  <label className="field">
                    <span>Preferred provider</span>
                    <select
                      onChange={(event) => update("provider_preference", event.target.value)}
                      value={draft.provider_preference}
                    >
                      <option value="twelve_data">Twelve Data</option>
                    </select>
                  </label>
                  <ReadOnlyField label="Twelve Data key" value={settings.secrets.twelve_data_api_key} />

                  <label className="field">
                    <span>LLM provider</span>
                    <select
                      onChange={(event) => update("llm_provider_type", event.target.value)}
                      value={draft.llm_provider_type}
                    >
                      <option value="openai">OpenAI</option>
                      <option value="ollama">Ollama</option>
                      <option value="deepseek">DeepSeek</option>
                    </select>
                  </label>
                  <TextField
                    label="LLM base URL"
                    onChange={(value) => update("llm_base_url", value)}
                    value={draft.llm_base_url}
                  />
                  <TextField
                    label="LLM model"
                    onChange={(value) => update("llm_model_name", value)}
                    value={draft.llm_model_name}
                  />
                  <CheckboxField
                    checked={draft.tradingagents_enabled}
                    label="TradingAgents enabled"
                    onChange={(value) => update("tradingagents_enabled", value)}
                  />
                  <NumberField
                    label="Debate rounds"
                    min={1}
                    onChange={(value) => update("max_debate_rounds", value)}
                    value={draft.max_debate_rounds}
                  />
                  <NumberField
                    label="Risk rounds"
                    min={1}
                    onChange={(value) => update("max_risk_discuss_rounds", value)}
                    value={draft.max_risk_discuss_rounds}
                  />
                  <ReadOnlyField label="Remote LLM key" value={settings.secrets.remote_llm_api_key} />

                  <TextField
                    label="SMTP host"
                    onChange={(value) => update("smtp_host", value)}
                    value={draft.smtp_host}
                  />
                  <NumberField
                    label="SMTP port"
                    min={1}
                    onChange={(value) => update("smtp_port", value)}
                    value={draft.smtp_port}
                  />
                  <TextField
                    label="SMTP user"
                    onChange={(value) => update("smtp_user", value)}
                    value={draft.smtp_user}
                  />
                  <TextField
                    label="From address"
                    onChange={(value) => update("smtp_from", value)}
                    value={draft.smtp_from}
                  />
                  <TextField
                    label="To address"
                    onChange={(value) => update("smtp_to", value)}
                    value={draft.smtp_to}
                  />
                  <ReadOnlyField label="SMTP password" value={settings.secrets.smtp_password} />
                  <CheckboxField
                    checked={draft.daily_digest_enabled}
                    label="Daily digest"
                    onChange={(value) => update("daily_digest_enabled", value)}
                  />
                  <NumberField
                    label="Alert threshold"
                    max={1}
                    min={0}
                    onChange={(value) => update("strong_signal_alert_threshold", value)}
                    step={0.01}
                    value={draft.strong_signal_alert_threshold}
                  />
                  <NumberField
                    label="Debounce days"
                    min={0}
                    onChange={(value) => update("email_debounce_days", value)}
                    value={draft.email_debounce_days}
                  />

                  <CheckboxField
                    checked={draft.scheduler_enabled}
                    label="Auto-run"
                    onChange={(value) => update("scheduler_enabled", value)}
                  />
                  <NumberField
                    label="Trigger hour"
                    max={23}
                    min={0}
                    onChange={(value) => update("daily_trigger_hour", value)}
                    value={draft.daily_trigger_hour}
                  />
                  <NumberField
                    label="Trigger minute"
                    max={59}
                    min={0}
                    onChange={(value) => update("daily_trigger_minute", value)}
                    value={draft.daily_trigger_minute}
                  />
                  <TextField
                    label="Timezone"
                    onChange={(value) => update("scheduler_timezone", value ?? "America/Toronto")}
                    value={draft.scheduler_timezone}
                  />
                  <CheckboxField
                    checked={draft.kronos_enabled}
                    label="Kronos daily"
                    onChange={(value) => update("kronos_enabled", value)}
                  />
                </div>
              </section>

              <section className="admin-section" aria-label="Services">
                <h2>Services</h2>
                <div className="table-shell">
                  <table>
                    <thead>
                      <tr>
                        <th>Service</th>
                        <th>Status</th>
                        <th>Latency</th>
                        <th>Checked</th>
                      </tr>
                    </thead>
                    <tbody>
                      {health?.services.map((service) => (
                        <tr key={service.service_name}>
                          <td>{service.service_name}</td>
                          <td>
                            <span className={`severity ${healthClass(service.status)}`}>
                              {service.status}
                            </span>
                          </td>
                          <td>{service.latency_ms === null ? "-" : `${service.latency_ms}ms`}</td>
                          <td>{new Date(service.checked_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="admin-section" aria-label="Jobs and logs">
                <h2>Jobs & Logs</h2>
                <div className="action-row">
                  <button disabled={runningAction !== null} onClick={runDailyNow} type="button">
                    {runningAction === "Run daily now" ? "Running" : "Run daily now"}
                  </button>
                  <button
                    disabled={runningAction !== null}
                    onClick={() => void runAdminAction("Run smoke test", "/admin/run-smoke")}
                    type="button"
                  >
                    {runningAction === "Run smoke test" ? "Running" : "Run smoke test"}
                  </button>
                  <button
                    disabled={runningAction !== null}
                    onClick={() => void runAdminAction("Check provider", "/admin/check-provider")}
                    type="button"
                  >
                    Check provider
                  </button>
                  <button
                    disabled={runningAction !== null}
                    onClick={() => void runAdminAction("Test LLM", "/admin/test-llm")}
                    type="button"
                  >
                    Test LLM
                  </button>
                  <button
                    disabled={runningAction !== null}
                    onClick={() => void runAdminAction("Test email", "/admin/test-email")}
                    type="button"
                  >
                    Test email
                  </button>
                </div>
              </section>

              <section className="admin-section" aria-label="Safety notes">
                <h2>Safety Notes</h2>
                <p className="muted">Secrets are loaded from environment variables.</p>
                <p className="muted">Settings changes affect the next run and do not mutate historical signals.</p>
              </section>
            </>
          ) : (
            <p className="muted">Loading admin settings...</p>
          )}
        </>
      )}
    </main>
  );
}

function toEditable(settings: AdminSettings): EditableAdminSettings {
  const { secrets: _secrets, ...editable } = settings;
  return editable;
}

function TextField({
  label,
  onChange,
  value
}: {
  label: string;
  onChange: (value: string | null) => void;
  value: string | null;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input onChange={(event) => onChange(event.target.value || null)} value={value ?? ""} />
    </label>
  );
}

function NumberField({
  label,
  max,
  min,
  onChange,
  step,
  value
}: {
  label: string;
  max?: number;
  min: number;
  onChange: (value: number) => void;
  step?: number;
  value: number;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        max={max}
        min={min}
        onChange={(event) => onChange(Number(event.target.value))}
        step={step}
        type="number"
        value={value}
      />
    </label>
  );
}

function CheckboxField({
  checked,
  label,
  onChange
}: {
  checked: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="field checkbox-field">
      <input checked={checked} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
      <span>{label}</span>
    </label>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="field readonly-field">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function healthClass(status: string) {
  if (status === "ok") {
    return "severity-signal";
  }
  if (status === "unreachable") {
    return "severity-error";
  }
  return "severity-warning";
}
