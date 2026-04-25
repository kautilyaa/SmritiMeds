import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const MODES = [
  {
    value: "auto",
    title: "Auto Route",
    subtitle: "Best default for hackathon demos",
    blurb: "Tries to route document-style uploads into OCR and bottle images into vision analysis.",
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
    subtitle: "medocr-vision",
    blurb: "For prescriptions, lab reports, and forms with printed or semi-structured text.",
  },
  {
    value: "handwritten_prescription",
    title: "Handwritten Rx",
    subtitle: "Donut OCR fallback",
    blurb: "For handwritten prescriptions and rough doctor notes.",
  },
];

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

function App() {
  const [mode, setMode] = useState("auto");
  const [runLocalVision, setRunLocalVision] = useState(false);
  const [labelImage, setLabelImage] = useState(null);
  const [verificationImage, setVerificationImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setHealth({ ok: false, error: String(err) }));
  }, []);

  const currentMode = useMemo(
    () => MODES.find((item) => item.value === mode) || MODES[0],
    [mode]
  );

  async function submit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
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
          <div>
            <p className="eyebrow">SmritiMeds 2.0</p>
            <h1>Remember better. Verify smarter.</h1>
            <p className="hero-copy">
              Vibrant medication intelligence for hackathon demos: Claude Vision,
              document OCR routing, YOLO pill detection, and reminder generation in one flow.
            </p>
          </div>
          <div className="hero-stats">
            <StatPill label="Primary OCR" value="medocr-vision" tone="violet" />
            <StatPill label="Handwritten Fallback" value="Donut OCR" tone="teal" />
            <StatPill label="Visual Label Flow" value="Claude Vision" tone="amber" />
          </div>
        </section>

        <section className="panel-grid">
          <form className="glass-card" onSubmit={submit}>
            <div className="section-header">
              <h2>Upload and route</h2>
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

            <label className="upload-field">
              <span>Primary image</span>
              <input
                type="file"
                accept="image/*"
                onChange={(event) => setLabelImage(event.target.files?.[0] || null)}
              />
            </label>

            <label className="upload-field">
              <span>Optional pill verification image</span>
              <input
                type="file"
                accept="image/*"
                onChange={(event) => setVerificationImage(event.target.files?.[0] || null)}
              />
            </label>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={runLocalVision}
                onChange={(event) => setRunLocalVision(event.target.checked)}
              />
              <span>Run local YOLO + Hugging Face pill beta</span>
            </label>

            <button className="primary-button" disabled={loading} type="submit">
              {loading ? "Analyzing..." : "Analyze medication"}
            </button>

            {error ? <p className="error-text">{error}</p> : null}
          </form>

          <aside className="glass-card">
            <div className="section-header">
              <h2>Backend status</h2>
              <span className="badge">{health?.ok ? "Online" : "Checking"}</span>
            </div>
            {health ? (
              <>
                <StatPill
                  label="Anthropic"
                  value={health.anthropic_configured ? "Configured" : "Missing key"}
                  tone={health.anthropic_configured ? "teal" : "amber"}
                />
                <div className="health-block">
                  <h3>OCR backends</h3>
                  <ul>
                    {Object.entries(health.ocr_backends || {}).map(([key, value]) => (
                      <li key={key}>
                        <strong>{key}</strong>: {value.package_ready ? "ready" : "not installed"} —{" "}
                        {value.notes}
                      </li>
                    ))}
                  </ul>
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
              <div className="section-header">
                <h2>Structured medication result</h2>
                <span className="badge badge--violet">{result.mode}</span>
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
                <h3>Reminder schedule</h3>
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
                <ul>
                  {(result.analysis?.confidence_notes || []).map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="glass-card result-card">
              <div className="section-header">
                <h2>Verification and beta vision</h2>
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
      </main>
    </div>
  );
}

export default App;
