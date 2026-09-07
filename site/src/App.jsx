import { useMemo, useState } from "react";
import guide from "./current-models.json";

const runtimeLabels = {
  mlx: "MLX · text",
  mlx_vlm: "MLX · vision",
  mlx_audio: "MLX · audio",
  ollama: "Ollama",
  apfel: "Apple system",
};

const benchmarkLabels = {
  passed: "Full benchmark",
  benchmarked: "Full benchmark",
  passed_with_notes: "Smoke test notes",
  runtime_failed: "Earlier load failed",
};

const capabilityFilters = [
  { value: "all", label: "All capabilities" },
  { value: "vision", label: "Image input" },
  { value: "code", label: "Coding" },
  { value: "tools", label: "Tools" },
  { value: "thinking", label: "Reasoning mode" },
  { value: "audio", label: "Audio" },
];

const runtimeFilters = [
  { value: "all", label: "All runtimes" },
  { value: "mlx", label: "MLX" },
  { value: "ollama", label: "Ollama" },
  { value: "apfel", label: "Apple system" },
];

function compactNumber(value, suffix = "") {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(1)}${suffix}`;
}

function contextLabel(tokens) {
  if (!tokens) return "—";
  if (tokens >= 1000) {
    const thousands = tokens / 1000;
    return `${Number.isInteger(thousands) ? thousands : thousands.toFixed(1)}K`;
  }
  return String(tokens);
}

function matchesRuntime(model, runtime) {
  if (runtime === "all") return true;
  if (runtime === "mlx") return model.runtime.startsWith("mlx");
  return model.runtime === runtime;
}

function matchesCapability(model, capability) {
  if (capability === "all") return true;
  const terms = [...model.modalities, ...model.capabilities].map((item) =>
    item.toLowerCase(),
  );
  if (capability === "vision") return terms.includes("image") || terms.includes("vision");
  return terms.some((term) => term.includes(capability));
}

function benchmarkStatus(model) {
  if (!model.benchmark) return "Not in text suite";
  return benchmarkLabels[model.benchmark.status] || model.benchmark.status;
}

function ModelRow({ model }) {
  const benchmark = model.benchmark;

  return (
    <li className="model-row" data-runtime={model.runtime}>
      <div className="rank-cell" aria-label={benchmark?.rank ? `Rank ${benchmark.rank}` : "Unranked"}>
        {benchmark?.rank ? (
          <>
            <span className="rank-number">{benchmark.rank}</span>
            <span className="rank-label">local</span>
          </>
        ) : (
          <span className="rank-dash">—</span>
        )}
      </div>

      <div className="model-identity">
        <div className="model-title-line">
          <h3>{model.label}</h3>
          <span className={`runtime-tag runtime-${model.runtime}`}>
            {runtimeLabels[model.runtime]}
          </span>
        </div>
        <p className="model-id">{model.model_name}</p>
        <p className="best-for">{model.best_for}</p>
        <div className="tag-line" aria-label="Inputs and capabilities">
          {model.modalities.map((item) => (
            <span className="tag tag-input" key={item}>
              {item}
            </span>
          ))}
          {model.capabilities.map((item) => (
            <span className="tag" key={item}>
              {item}
            </span>
          ))}
        </div>
      </div>

      <dl className="spec-cell">
        <div>
          <dt>Model</dt>
          <dd>{model.parameters}</dd>
        </div>
        <div>
          <dt>Context</dt>
          <dd>{contextLabel(model.context_tokens)}</dd>
        </div>
        <div>
          <dt>Local file</dt>
          <dd>{compactNumber(model.size_gb, " GB")}</dd>
        </div>
      </dl>

      <div className="evidence-cell">
        {benchmark?.work_fit_score !== null &&
        benchmark?.work_fit_score !== undefined ? (
          <div className="score-lockup">
            <span className="score">{compactNumber(benchmark.work_fit_score)}</span>
            <span className="score-label">work-fit / 100</span>
          </div>
        ) : (
          <div className="score-lockup score-empty">
            <span className="score">—</span>
            <span className="score-label">not comparable</span>
          </div>
        )}
        <dl className="benchmark-mini">
          <div>
            <dt>Quality</dt>
            <dd>{compactNumber(benchmark?.quality_score)}</dd>
          </div>
          <div>
            <dt>Speed</dt>
            <dd>
              {benchmark?.generation_tokens_per_second
                ? compactNumber(benchmark.generation_tokens_per_second, " tok/s")
                : "—"}
            </dd>
          </div>
          <div>
            <dt>Peak memory</dt>
            <dd>{compactNumber(benchmark?.peak_memory_gb, " GB")}</dd>
          </div>
        </dl>
        <span className={`proof-status proof-${benchmark?.status || "none"}`}>
          {benchmarkStatus(model)}
        </span>
      </div>

      <details className="model-details">
        <summary>Details and source</summary>
        <div className="details-layout">
          <div>
            <span className="detail-label">Use with care</span>
            <p>{model.caution}</p>
          </div>
          <div>
            <span className="detail-label">Build</span>
            <p>
              {model.quantization}
              {model.aliases?.length ? ` · aliases: ${model.aliases.join(", ")}` : ""}
            </p>
          </div>
          <div>
            <span className="detail-label">Evidence</span>
            <p>
              {benchmark?.artifact ? (
                <a href={`https://github.com/Rajeev-SG/local-llm-lab/blob/main/${benchmark.artifact}`}>
                  Open local benchmark artifact
                </a>
              ) : (
                "No comparable text benchmark yet"
              )}
            </p>
          </div>
          <div>
            <span className="detail-label">Model information</span>
            <p>
              <a href={model.source_url} target="_blank" rel="noreferrer">
                Open the exact model page ↗
              </a>
            </p>
          </div>
        </div>
      </details>
    </li>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [runtime, setRuntime] = useState("all");
  const [capability, setCapability] = useState("all");
  const [sort, setSort] = useState("rank");

  const installed = Array.isArray(guide.installed_models) ? guide.installed_models : [];
  const aliases = Array.isArray(guide.aliases) ? guide.aliases : [];
  const previouslyTested = Array.isArray(guide.previously_tested) ? guide.previously_tested : [];
  const recommendations = {
    code: installed.find((model) => model.benchmark?.rank === 1),
    broad: installed.find((model) => model.benchmark?.rank === 2),
    compact: installed.find((model) => model.benchmark?.rank === 3),
    speech: installed.find((model) => model.runtime === "mlx_audio"),
  };

  const visibleModels = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const result = installed.filter((model) => {
      const searchable = [
        model.label,
        model.model_name,
        model.best_for,
        model.caution,
        ...model.modalities,
        ...model.capabilities,
        ...(model.aliases || []),
      ]
        .join(" ")
        .toLowerCase();
      return (
        (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        matchesRuntime(model, runtime) &&
        matchesCapability(model, capability)
      );
    });

    return result.sort((a, b) => {
      if (sort === "score") {
        return (
          (b.benchmark?.work_fit_score ?? -1) - (a.benchmark?.work_fit_score ?? -1)
        );
      }
      if (sort === "speed") {
        return (
          (b.benchmark?.generation_tokens_per_second ?? -1) -
          (a.benchmark?.generation_tokens_per_second ?? -1)
        );
      }
      if (sort === "size") return (a.size_gb ?? Infinity) - (b.size_gb ?? Infinity);
      if (sort === "name") return a.label.localeCompare(b.label);
      return (
        (a.benchmark?.rank ?? 10_000) - (b.benchmark?.rank ?? 10_000) ||
        a.label.localeCompare(b.label)
      );
    });
  }, [capability, installed, query, runtime, sort]);

  const generatedDate = guide.generated_at
    ? new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
      }).format(new Date(guide.generated_at))
    : "date unavailable";
  const snapshotAgeDays = guide.generated_at
    ? Math.max(0, Math.floor((Date.now() - new Date(guide.generated_at).getTime()) / 86_400_000))
    : null;
  const snapshotStatus = snapshotAgeDays === null
    ? "Date unavailable"
    : snapshotAgeDays > 31
      ? "Stale snapshot"
      : "Dated snapshot";

  return (
    <div className="page-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Local LLM Lab home">
          <span className="brand-mark" aria-hidden="true">
            L
          </span>
          <span>
            <strong>Local LLM Lab</strong>
            <em>Rajeev’s Apple Silicon model field guide</em>
          </span>
        </a>
        <nav className="nav" aria-label="Page sections">
          <a href="#recommendations">Start here</a>
          <a href="#inventory">All models</a>
          <a href="#aliases">Aliases</a>
          <a href="#method">Method</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">{snapshotStatus} · {generatedDate}</p>
            <h1>Models from this Mac, in one dated guide.</h1>
            <p className="lede">
              Choose a model without reopening benchmark notes or searching model
              cards. This page joins a dated installed-inventory snapshot with measured
              local quality, speed, memory, context length, modalities, capabilities,
              tuned aliases, and exact source builds.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#inventory">
                Compare all models
              </a>
              <a className="button button-secondary" href="#recommendations">
                See the short list
              </a>
            </div>
          </div>

          <aside className="inventory-summary" aria-label="Current inventory summary">
            <p className="summary-kicker">Snapshot scope</p>
            <dl>
              <div>
                <dt>Installed builds</dt>
                <dd>{guide.summary.installed_builds}</dd>
              </div>
              <div>
                <dt>Comparable local scores</dt>
                <dd>{guide.summary.ranked_installed_builds}</dd>
              </div>
              <div>
                <dt>Tuned names</dt>
                <dd>{guide.summary.aliases}</dd>
              </div>
              <div>
                <dt>Model data</dt>
                <dd>{guide.summary.installed_storage_gb} GB</dd>
              </div>
            </dl>
            <p className="summary-note">
              This is a dated, machine-specific snapshot—not a live inventory feed.
              MLX uses host unified memory directly, while Ollama provides the easiest
              chat path. Missing scores mean that exact build was not comparable.
            </p>
          </aside>
        </section>

        <section className="recommendations section" id="recommendations">
          <div className="section-heading split-heading">
            <div>
              <p className="eyebrow">Start here</p>
              <h2>{installed.length ? "Four models cover most local work." : "No recommendations are available."}</h2>
            </div>
            <p>
              These are recommendations from this Mac’s dated local measurements, not
              vendor benchmark claims. They do not imply current availability.
            </p>
          </div>
          <div className="recommendation-grid">
            <article>
              <p className="recommendation-role">Coding default</p>
              <h3>{recommendations.code?.label}</h3>
              <p>{recommendations.code?.best_for}</p>
              <a href="#inventory">{recommendations.code ? "Local rank #1 · measured here" : "Unavailable in this snapshot"}</a>
            </article>
            <article>
              <p className="recommendation-role">Broad and visual</p>
              <h3>{recommendations.broad?.label}</h3>
              <p>{recommendations.broad?.best_for}</p>
              <a href="#inventory">{recommendations.broad ? "Local rank #2 · measured here" : "Unavailable in this snapshot"}</a>
            </article>
            <article>
              <p className="recommendation-role">Small high-quality helper</p>
              <h3>{recommendations.compact?.label}</h3>
              <p>{recommendations.compact?.best_for}</p>
              <a href="#inventory">{recommendations.compact ? "Local rank #3 · measured here" : "Unavailable in this snapshot"}</a>
            </article>
            <article>
              <p className="recommendation-role">Speech</p>
              <h3>{recommendations.speech?.label}</h3>
              <p>{recommendations.speech?.best_for}</p>
              <a href="#inventory">{recommendations.speech ? "Audio input · measured here" : "Unavailable in this snapshot"}</a>
            </article>
          </div>
        </section>

        <section className="inventory section" id="inventory">
          <div className="section-heading split-heading">
            <div>
              <p className="eyebrow">Dated installed snapshot</p>
              <h2>Compare every exact build.</h2>
            </div>
            <p>
              Different runtime builds stay separate because their speed, memory use,
              and reliability can differ even when the base model name is the same.
            </p>
          </div>

          <div className="filter-panel">
            <label className="search-field">
              <span>Search</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Model, task, capability, or alias"
              />
            </label>
            <label className="sort-field">
              <span>Sort</span>
              <select value={sort} onChange={(event) => setSort(event.target.value)}>
                <option value="rank">Local recommendation</option>
                <option value="score">Work-fit score</option>
                <option value="speed">Generation speed</option>
                <option value="size">Smallest file</option>
                <option value="name">Model name</option>
              </select>
            </label>
            <fieldset>
              <legend>Runtime</legend>
              <div className="filter-buttons">
                {runtimeFilters.map((item) => (
                  <button
                    type="button"
                    key={item.value}
                    aria-pressed={runtime === item.value}
                    onClick={() => setRuntime(item.value)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>Capability</legend>
              <div className="filter-buttons">
                {capabilityFilters.map((item) => (
                  <button
                    type="button"
                    key={item.value}
                    aria-pressed={capability === item.value}
                    onClick={() => setCapability(item.value)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </fieldset>
          </div>

          <div className="results-line" aria-live="polite">
            <strong>{visibleModels.length}</strong> of {installed.length} installed builds
          </div>

          {visibleModels.length ? (
            <ol className="model-list">
              {visibleModels.map((model) => (
                <ModelRow model={model} key={model.build_id} />
              ))}
            </ol>
          ) : (
            <div className="empty-state">
              <h3>{installed.length ? "No installed model matches those filters." : "No model snapshot is available."}</h3>
              <p>{installed.length ? "Try a broader search or clear the filters." : "The public guide is waiting for a validated dated packet."}</p>
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setRuntime("all");
                  setCapability("all");
                }}
              >
                Clear filters
              </button>
            </div>
          )}
        </section>

        <section className="section reference-grid" id="aliases">
          <div>
            <p className="eyebrow">Tuned Ollama names</p>
            <h2>Aliases change behaviour, not weights.</h2>
            <p className="section-intro">
              These names reuse an installed base model with deterministic settings
              and a narrower job. They do not consume another full copy of the model.
            </p>
          </div>
          <div className="alias-table" role="table" aria-label="Tuned model aliases">
            <div className="alias-head" role="row">
              <span role="columnheader">Use this name</span>
              <span role="columnheader">Based on</span>
            </div>
            {aliases.map((item) => (
              <div className="alias-row" role="row" key={item.alias}>
                <code role="cell">{item.alias}</code>
                <span role="cell">{item.base_model}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="section historical" id="historical">
          <div className="section-heading split-heading">
            <div>
              <p className="eyebrow">Previously tested, not installed</p>
              <h2>Old evidence stays visible.</h2>
            </div>
            <p>
              These builds were removed from the cache on 30 July 2026. Their results
              remain in the historical leaderboard, but they are not presented as
              currently available.
            </p>
          </div>
          <div className="historical-table">
            {previouslyTested.map((model) => (
              <article key={model.build_id}>
                <div>
                  <h3>{model.label}</h3>
                  <p>{model.runtime}</p>
                </div>
                <dl>
                  <div>
                    <dt>Old rank</dt>
                    <dd>{model.rank || "—"}</dd>
                  </div>
                  <div>
                    <dt>Work-fit</dt>
                    <dd>{compactNumber(model.work_fit_score)}</dd>
                  </div>
                  <div>
                    <dt>Quality</dt>
                    <dd>{compactNumber(model.quality_score)}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </section>

        <section className="section method" id="method">
          <div>
            <p className="eyebrow">How to read the numbers</p>
            <h2>Local evidence first.</h2>
          </div>
          <div className="method-columns">
            <article>
              <span>01</span>
              <h3>Work-fit score</h3>
              <p>
                A 100-point local score: 80% task quality, 15% response-time
                usefulness, and 5% successful invocations. Tasks favour shell work,
                structured data, classification, and concise technical writing.
              </p>
            </article>
            <article>
              <span>02</span>
              <h3>Quality score</h3>
              <p>
                The weighted result from the shared eight-task suite without the
                speed adjustment. A dash means the exact build did not complete the
                comparable suite.
              </p>
            </article>
            <article>
              <span>03</span>
              <h3>Speed and memory</h3>
              <p>
                MLX text speed uses three fixed 512-token prompt and 128-token
                completion trials. Vision-model speed uses end-to-end requests, so
                it should not be compared directly with isolated text trials.
              </p>
            </article>
          </div>
          <div className="method-links">
            <a href="https://github.com/Rajeev-SG/local-llm-lab/blob/main/overall-leaderboard.md">
              Read the complete leaderboard
            </a>
            <a href="https://github.com/Rajeev-SG/local-llm-lab/tree/main/output/benchmarks">
              Inspect raw benchmark data
            </a>
            <a href="https://github.com/Rajeev-SG/local-llm-lab">
              Open the repository
            </a>
          </div>
        </section>

        <section className="section run-guide" id="run">
          <div>
            <p className="eyebrow">Run the models</p>
            <h2>Three local entry points.</h2>
          </div>
          <div className="run-columns">
            <article>
              <h3>Ollama and Open WebUI</h3>
              <pre>
                <code>{`./scripts/start-ollama.sh
./scripts/start-openwebui.sh
ollama run qwen3.5:9b`}</code>
              </pre>
              <div className="run-links">
                <a href="http://open-webui-lab.orb.local">OrbStack</a>
                <a href="http://localhost:3001">Localhost</a>
                <a href="https://rajeevs-macbook-pro-2.tail33d641.ts.net/">
                  Private remote link
                </a>
              </div>
            </article>
            <article>
              <h3>Direct MLX</h3>
              <pre>
                <code>{`mlx_lm.generate \\
  --model mlx-community/Qwen3.6-35B-A3B-4bit \\
  --prompt "Summarise this repository"`}</code>
              </pre>
              <p>Use MLX directly for the leading benchmarked builds and full host memory.</p>
            </article>
            <article>
              <h3>Apple system model</h3>
              <pre>
                <code>{`apfel "Summarise this text"
apfel --model-info`}</code>
              </pre>
              <p>No separate download; best for small private text tasks.</p>
            </article>
          </div>
        </section>
      </main>

      <footer className="footer">
        <p>
          Generated from a dated local evidence snapshot on {generatedDate}. Historical
          benchmark evidence is preserved when a model is removed; this page is not live.
        </p>
        <a href="#top">Back to top ↑</a>
      </footer>
    </div>
  );
}
