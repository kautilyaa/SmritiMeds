import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const REMINDER_STORAGE_KEY = "smritimeds.reminders.v2";
const IMPORT_STORAGE_KEY = "smritimeds.last-import.v2";

const MODES = [
  {
    value: "auto",
    title: "Auto Route",
    subtitle: "Best default for hackathon demos",
    blurb: "Routes document-style uploads into OCR and bottle images into vision analysis.",
  },
  {
    value: "bottle_label",
    title: "Bottle / Blister",
    subtitle: "Claude Vision-first",
    blurb: "Best for curved labels, blister packs, and pharmacy bottles.",
  },
  {
    value: "printed_document",
    title: "Printed Medical Doc",
    subtitle: "OCR + Claude fallback",
    blurb: "For prescriptions, lab reports, and forms with printed or semi-structured text.",
  },
  {
    value: "handwritten_prescription",
    title: "Handwritten Rx",
    subtitle: "Handwriting OCR + fallback",
    blurb: "For handwritten prescriptions and rough doctor notes.",
  },
];

const REMINDER_TIME_OPTIONS = {
  Morning: "08:00",
  Noon: "12:00",
  Evening: "18:00",
  Bedtime: "21:00",
  Custom: "09:00",
};

function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value ?? "");
  } catch {
    return fallback;
  }
}

function createId() {
  return globalThis.crypto?.randomUUID?.() || `reminder-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatModeLabel(mode) {
  return mode?.replaceAll("_", " ") || "analysis";
}

function timeToMinutes(value) {
  if (!value || !value.includes(":")) return Number.POSITIVE_INFINITY;
  const [hours, minutes] = value.split(":").map((part) => Number(part));
  return hours * 60 + minutes;
}

function nextReminderLabel(reminders) {
  const pending = reminders
    .filter((item) => item.active && !item.completed)
    .sort((a, b) => timeToMinutes(a.time) - timeToMinutes(b.time));

  if (!pending.length) return "All caught up";
  const next = pending[0];
  return `${next.time || "Any time"} · ${next.title}`;
}

function buildSuggestionKey(result) {
  const analysis = result?.analysis;
  if (!analysis?.schedule?.length) return "";
  return JSON.stringify({
    medication: analysis.medication_name || "",
    instructions: analysis.instructions_raw || "",
    schedule: analysis.schedule,
  });
}

function mapScheduleToReminders(result) {
  const analysis = result?.analysis || {};
  const medicationName = analysis.medication_name || "Medication reminder";
  const sourceKey = buildSuggestionKey(result);

  return (analysis.schedule || []).map((entry, index) => ({
    id: createId(),
    sourceKey: `${sourceKey}:${index}`,
    importedFrom: result.mode,
    title: entry.label || `${entry.time_of_day} reminder`,
    medicationName,
    dose: entry.dose || analysis.strength || "",
    slot: entry.time_of_day || "Custom",
    time: REMINDER_TIME_OPTIONS[entry.time_of_day] || REMINDER_TIME_OPTIONS.Custom,
    notes: entry.notes || analysis.instructions_raw || "",
    active: true,
    completed: false,
  }));
}

function createManualReminder() {
  return {
    id: createId(),
    sourceKey: "",
    importedFrom: "manual",
    title: "Custom reminder",
    medicationName: "",
    dose: "",
    slot: "Custom",
    time: REMINDER_TIME_OPTIONS.Custom,
    notes: "",
    active: true,
    completed: false,
  };
}

function StatPill({ label, value, tone = "neutral" }) {
  return (
    <div className={`stat-pill stat-pill--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FallbackBanner({ ocr }) {
  if (!ocr?.fallback) return null;

  const title =
    ocr.fallback === "claude_vision"
      ? "Using Claude fallback"
      : "Fallback path triggered";

  return (
    <div className="fallback-banner">
      <strong>{title}</strong>
      <p>{ocr.fallback_reason || "The OCR model was unavailable or returned unusable text."}</p>
    </div>
  );
}

function ReminderCard({ reminder, onChange, onDelete }) {
  return (
    <article
      className={`reminder-card ${!reminder.active ? "reminder-card--inactive" : ""} ${
        reminder.completed ? "reminder-card--done" : ""
      }`}
    >
      <div className="reminder-card__top">
        <div>
          <div className="reminder-meta">
            <span className="reminder-chip">{reminder.slot}</span>
            <span className="reminder-chip reminder-chip--subtle">
              {reminder.importedFrom === "manual" ? "Manual" : formatModeLabel(reminder.importedFrom)}
            </span>
          </div>
          <input
            className="reminder-title-input"
            value={reminder.title}
            onChange={(event) => onChange(reminder.id, "title", event.target.value)}
            placeholder="Reminder title"
          />
        </div>

        <button className="ghost-button ghost-button--danger" type="button" onClick={() => onDelete(reminder.id)}>
          Delete
        </button>
      </div>

      <div className="field-grid">
        <label className="field">
          <span>Medication</span>
          <input
            value={reminder.medicationName}
            onChange={(event) => onChange(reminder.id, "medicationName", event.target.value)}
            placeholder="Medication name"
          />
        </label>

        <label className="field">
          <span>Dose</span>
          <input
            value={reminder.dose}
            onChange={(event) => onChange(reminder.id, "dose", event.target.value)}
            placeholder="e.g. 1 tablet / 25 mg"
          />
        </label>

        <label className="field">
          <span>Time of day</span>
          <select value={reminder.slot} onChange={(event) => onChange(reminder.id, "slot", event.target.value)}>
            {Object.keys(REMINDER_TIME_OPTIONS).map((slot) => (
              <option key={slot} value={slot}>
                {slot}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Reminder time</span>
          <input
            type="time"
            value={reminder.time}
            onChange={(event) => onChange(reminder.id, "time", event.target.value)}
          />
        </label>
      </div>

      <label className="field">
        <span>Notes</span>
        <textarea
          rows="3"
          value={reminder.notes}
          onChange={(event) => onChange(reminder.id, "notes", event.target.value)}
          placeholder="Add meal timing, caution notes, or manual reminders..."
        />
      </label>

      <div className="reminder-actions">
        <button
          className={`toggle-button ${reminder.active ? "toggle-button--active" : ""}`}
          type="button"
          onClick={() => onChange(reminder.id, "active", !reminder.active)}
        >
          {reminder.active ? "Active" : "Paused"}
        </button>
        <button
          className={`toggle-button ${reminder.completed ? "toggle-button--complete" : ""}`}
          type="button"
          onClick={() => onChange(reminder.id, "completed", !reminder.completed)}
        >
          {reminder.completed ? "Completed" : "Mark done"}
        </button>
      </div>
    </article>
  );
}

function App() {
  const [mode, setMode] = useState("auto");
  const [runLocalVision, setRunLocalVision] = useState(false);
  const [labelImage, setLabelImage] = useState(null);
  const [verificationImage, setVerificationImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [statusNotice, setStatusNotice] = useState("");
  const [reminders, setReminders] = useState(() =>
    safeJsonParse(window.localStorage.getItem(REMINDER_STORAGE_KEY), [])
  );
  const [lastImportedKey, setLastImportedKey] = useState(() =>
    window.localStorage.getItem(IMPORT_STORAGE_KEY) || ""
  );

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setHealth({ ok: false, error: String(err) }));
  }, []);

  useEffect(() => {
    window.localStorage.setItem(REMINDER_STORAGE_KEY, JSON.stringify(reminders));
  }, [reminders]);

  useEffect(() => {
    window.localStorage.setItem(IMPORT_STORAGE_KEY, lastImportedKey);
  }, [lastImportedKey]);

  useEffect(() => {
    const suggestionKey = buildSuggestionKey(result);
    if (!suggestionKey || suggestionKey === lastImportedKey) return;

    const generatedReminders = mapScheduleToReminders(result);
    if (!generatedReminders.length) return;

    setReminders((previous) => {
      const knownSourceKeys = new Set(previous.map((item) => item.sourceKey).filter(Boolean));
      const additions = generatedReminders.filter((item) => !knownSourceKeys.has(item.sourceKey));
      return additions.length ? [...additions, ...previous] : previous;
    });
    setLastImportedKey(suggestionKey);
    setStatusNotice(`Imported ${generatedReminders.length} reminder${generatedReminders.length > 1 ? "s" : ""} from the latest analysis.`);
  }, [result, lastImportedKey]);

  const currentMode = useMemo(
    () => MODES.find((item) => item.value === mode) || MODES[0],
    [mode]
  );

  const reminderStats = useMemo(() => {
    const active = reminders.filter((item) => item.active).length;
    const completed = reminders.filter((item) => item.completed).length;
    const managed = reminders.length;
    return {
      active,
      completed,
      managed,
      next: nextReminderLabel(reminders),
    };
  }, [reminders]);

  function updateReminder(id, field, value) {
    setReminders((previous) =>
      previous.map((item) => {
        if (item.id !== id) return item;
        const nextItem = { ...item, [field]: value };
        if (field === "slot" && (!item.time || item.time === REMINDER_TIME_OPTIONS[item.slot])) {
          nextItem.time = REMINDER_TIME_OPTIONS[value] || item.time;
        }
        return nextItem;
      })
    );
  }

  function deleteReminder(id) {
    setReminders((previous) => previous.filter((item) => item.id !== id));
  }

  function addManualReminder() {
    setReminders((previous) => [createManualReminder(), ...previous]);
    setStatusNotice("Added a manual reminder.");
  }

  function clearCompletedReminders() {
    setReminders((previous) => previous.filter((item) => !item.completed));
    setStatusNotice("Cleared completed reminders.");
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setStatusNotice("");

    if (!labelImage) {
      setError("Add a primary medication or document image first.");
      return;
    }

    const form = new FormData();
    form.append("mode", mode);
    form.append("run_local_vision", String(runLocalVision));
    form.append("label_image", labelImage);
    if (verificationImage) {
      form.append("verification_image", verificationImage);
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) {
        throw new Error(data.error || "Analysis failed.");
      }
      setResult(data);
      setStatusNotice("Analysis complete. Reminder suggestions updated below.");
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-shell">
      <div className="aurora aurora--violet" />
      <div className="aurora aurora--teal" />
      <main className="app-shell">
        <section className="hero-card">
          <div className="hero-copy-wrap">
            <p className="eyebrow">SmritiMeds 2.1</p>
            <h1>Adaptive medication reminders that you can actually manage.</h1>
            <p className="hero-copy">
              Upload a medication image, turn the result into editable reminders, and manage each reminder with
              times, notes, completion state, and local persistence.
            </p>
          </div>
          <div className="hero-stats">
            <StatPill label="Managed reminders" value={reminderStats.managed} tone="violet" />
            <StatPill label="Active reminders" value={reminderStats.active} tone="teal" />
            <StatPill label="Next reminder" value={reminderStats.next} tone="amber" />
          </div>
        </section>

        <section className="panel-grid">
          <form className="glass-card glass-card--tall" onSubmit={submit}>
            <div className="section-header section-header--stack-mobile">
              <div>
                <h2>Upload and route</h2>
                <p className="section-subtitle">Choose the smartest analysis path, then import reminders from the output.</p>
              </div>
              <span className="badge badge--live">{currentMode.subtitle}</span>
            </div>

            <div className="mode-grid">
              {MODES.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  className={`mode-card ${mode === item.value ? "mode-card--active" : ""}`}
                  onClick={() => setMode(item.value)}
                >
                  <strong>{item.title}</strong>
                  <span>{item.blurb}</span>
                </button>
              ))}
            </div>

            <div className="field-grid field-grid--uploads">
              <label className="upload-field">
                <span>Primary image</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => setLabelImage(event.target.files?.[0] || null)}
                />
                <small>{labelImage ? labelImage.name : "Upload a prescription, bottle label, or medical document."}</small>
              </label>

              <label className="upload-field">
                <span>Optional pill verification image</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => setVerificationImage(event.target.files?.[0] || null)}
                />
                <small>{verificationImage ? verificationImage.name : "Use this only when you want visual pill cross-checking."}</small>
              </label>
            </div>

            <label className="toggle-row toggle-row--card">
              <input
                type="checkbox"
                checked={runLocalVision}
                onChange={(event) => setRunLocalVision(event.target.checked)}
              />
              <div>
                <strong>Run local YOLO + Hugging Face pill beta</strong>
                <span>Keep this off for the most reliable demo path unless you specifically want the experimental local models.</span>
              </div>
            </label>

            <div className="button-row">
              <button className="primary-button" disabled={loading} type="submit">
                {loading ? "Analyzing..." : "Analyze medication"}
              </button>
              <button className="secondary-button" type="button" onClick={addManualReminder}>
                Add manual reminder
              </button>
            </div>

            {statusNotice ? <p className="status-text">{statusNotice}</p> : null}
            {error ? <p className="error-text">{error}</p> : null}
          </form>

          <aside className="glass-card glass-card--tall">
            <div className="section-header section-header--stack-mobile">
              <div>
                <h2>Backend status</h2>
                <p className="section-subtitle">Know which models are ready before you demo.</p>
              </div>
              <span className="badge">{health?.ok ? "Online" : "Checking"}</span>
            </div>
            {health ? (
              <>
                <div className="status-grid">
                  <StatPill
                    label="Anthropic"
                    value={health.anthropic_configured ? "Configured" : "Missing key"}
                    tone={health.anthropic_configured ? "teal" : "amber"}
                  />
                  <StatPill label="Printed OCR" value={health.ocr_backends?.medocr_vision?.package_ready ? "Installed" : "Unavailable"} tone="violet" />
                  <StatPill label="Handwritten OCR" value={health.ocr_backends?.handwritten_donut?.package_ready ? "Installed" : "Unavailable"} tone="amber" />
                </div>

                <div className="health-block">
                  <h3>OCR backends</h3>
                  <div className="stack-list">
                    {Object.entries(health.ocr_backends || {}).map(([key, value]) => (
                      <div key={key} className="info-card">
                        <strong>{key}</strong>
                        <p>{value.notes}</p>
                        <small>
                          package: {value.package_ready ? "ready" : "not ready"} · local cache:{" "}
                          {value.local_model_cached ? "present" : "not cached"}
                        </small>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="health-block">
                  <h3>Local vision cache</h3>
                  <pre>{JSON.stringify(health.local_vision, null, 2)}</pre>
                </div>
              </>
            ) : (
              <p>Loading health panel...</p>
            )}
          </aside>
        </section>

        {result ? (
          <section className="results-grid">
            <div className="glass-card result-card">
              <div className="section-header section-header--stack-mobile">
                <div>
                  <h2>Structured medication result</h2>
                  <p className="section-subtitle">This result feeds the reminder manager below.</p>
                </div>
                <span className="badge badge--violet">{formatModeLabel(result.mode)}</span>
              </div>

              <div className="metric-grid">
                <StatPill label="Medication" value={result.analysis?.medication_name || "Unknown"} tone="violet" />
                <StatPill label="Strength" value={result.analysis?.strength || "Unknown"} tone="teal" />
                <StatPill label="Times / day" value={result.analysis?.times_per_day ?? 0} tone="amber" />
              </div>

              <div className="callout">
                {result.analysis?.needs_manual_review ? (
                  <span>⚠️ Manual review recommended before relying on this schedule.</span>
                ) : (
                  <span>✅ Enough signal found to generate a reminder schedule.</span>
                )}
              </div>

              <FallbackBanner ocr={result.ocr} />

              {result.ocr?.raw_text ? (
                <div className="content-block">
                  <h3>OCR extraction</h3>
                  <p>{result.ocr.raw_text}</p>
                </div>
              ) : null}

              {result.ocr?.error ? (
                <div className="content-block">
                  <h3>OCR backend status</h3>
                  <p className="muted-text">{result.ocr.error}</p>
                </div>
              ) : null}

              {result.analysis?.instructions_raw ? (
                <div className="content-block">
                  <h3>Instructions</h3>
                  <p>{result.analysis.instructions_raw}</p>
                </div>
              ) : null}

              <div className="content-block">
                <h3>Suggested reminder schedule</h3>
                <div className="schedule-grid">
                  {(result.analysis?.schedule || []).length ? (
                    result.analysis.schedule.map((entry, index) => (
                      <article key={`${entry.time_of_day}-${index}`} className="schedule-card">
                        <p className="schedule-time">{entry.time_of_day}</p>
                        <h4>{entry.label}</h4>
                        <p>{(entry.items || []).join(", ")}</p>
                        {entry.dose ? <small>Dose: {entry.dose}</small> : null}
                        {entry.notes ? <small>{entry.notes}</small> : null}
                      </article>
                    ))
                  ) : (
                    <p className="muted-text">No reliable schedule was generated.</p>
                  )}
                </div>
              </div>

              <div className="content-block">
                <h3>Confidence notes</h3>
                <ul className="stacked-bullets">
                  {(result.analysis?.confidence_notes || []).map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="glass-card result-card">
              <div className="section-header section-header--stack-mobile">
                <div>
                  <h2>Verification and beta vision</h2>
                  <p className="section-subtitle">Useful for debugging or showcasing hybrid analysis paths.</p>
                </div>
                <span className="badge badge--teal">Hybrid</span>
              </div>

              <div className="content-block">
                <h3>Verification summary</h3>
                <p>{result.analysis?.verification_summary || "No verification summary returned."}</p>
              </div>

              {result.local_vision ? (
                <div className="content-block">
                  <h3>Local vision</h3>
                  {result.local_vision.error ? <p>{result.local_vision.error}</p> : null}
                  {result.local_vision.classifier_warning ? (
                    <p className="muted-text">{result.local_vision.classifier_warning}</p>
                  ) : null}
                  <p>Detected pill regions: {result.local_vision.count ?? 0}</p>
                  <div className="detection-list">
                    {(result.local_vision.detections || []).map((item) => (
                      <div key={item.pill_index} className="detection-card">
                        <strong>Pill {item.pill_index}</strong>
                        <span>Detection confidence: {item.confidence?.toFixed?.(2) ?? "n/a"}</span>
                        {item.best_match ? (
                          <span>
                            Best textual match: {item.best_match.label} ({item.best_match.match_score?.toFixed?.(2)})
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="muted-text">Local vision was not requested for this run.</p>
              )}

              <div className="content-block">
                <h3>Raw model output</h3>
                <pre>{result.raw_model_output || "No raw model output stored."}</pre>
              </div>
            </div>
          </section>
        ) : null}

        <section className="glass-card reminder-section">
          <div className="section-header section-header--stack-mobile">
            <div>
              <h2>Reminder manager</h2>
              <p className="section-subtitle">Edit times, pause reminders, mark doses complete, or create your own schedule manually.</p>
            </div>
            <div className="button-row button-row--compact">
              <button className="secondary-button" type="button" onClick={addManualReminder}>
                Add reminder
              </button>
              <button className="ghost-button" type="button" onClick={clearCompletedReminders}>
                Clear completed
              </button>
            </div>
          </div>

          <div className="reminder-stats-grid">
            <StatPill label="Managed" value={reminderStats.managed} tone="violet" />
            <StatPill label="Active" value={reminderStats.active} tone="teal" />
            <StatPill label="Completed" value={reminderStats.completed} tone="amber" />
            <StatPill label="Next up" value={reminderStats.next} tone="neutral" />
          </div>

          {reminders.length ? (
            <div className="reminder-grid">
              {reminders
                .slice()
                .sort((a, b) => {
                  if (a.completed !== b.completed) return Number(a.completed) - Number(b.completed);
                  if (a.active !== b.active) return Number(b.active) - Number(a.active);
                  return timeToMinutes(a.time) - timeToMinutes(b.time);
                })
                .map((reminder) => (
                  <ReminderCard
                    key={reminder.id}
                    reminder={reminder}
                    onChange={updateReminder}
                    onDelete={deleteReminder}
                  />
                ))}
            </div>
          ) : (
            <div className="reminder-empty">
              <h3>No reminders yet</h3>
              <p>Analyze an image to import suggested reminders, or add one manually to start managing medication timing.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
