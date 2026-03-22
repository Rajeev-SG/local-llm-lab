const highlights = [
  { value: "22B", label: "largest model proven through Open WebUI" },
  { value: "8", label: "useful local models verified on this machine" },
  { value: "48 GB", label: "Apple Silicon host memory behind the lab" },
  { value: "Playwright", label: "real browser proof, not script-only smoke tests" },
];

const pillars = [
  {
    title: "Actually tested",
    text: "This lab is built around proof. Models were pulled, run, and then verified in a live Open WebUI browser session with Playwright.",
  },
  {
    title: "Role tuned",
    text: "Instead of one vague default, the setup uses helper roles for fast compression, safer summaries, code-aware extraction, heavier synthesis, and opt-in reasoning.",
  },
  {
    title: "Honest about limits",
    text: "The current Docker Ollama runtime only sees about 15.7 GiB, so 30B+ experiments are documented as constrained rather than hand-waved as 'should work'.",
  },
];

const models = [
  {
    role: "Fast helper",
    alias: "local-helper-fast",
    model: "qwen3.5:9b",
    note: "Best for context compression and clustering when you want speed and cleaner output with thinking disabled.",
  },
  {
    role: "Safe helper",
    alias: "local-helper-safe",
    model: "phi4",
    note: "Great for conservative summaries, checklists, and lower-drama utility work.",
  },
  {
    role: "Code helper",
    alias: "local-coder-helper",
    model: "qwen2.5-coder:14b",
    note: "Best local coding-focused helper for API surfaces, diffs, and contract extraction.",
  },
  {
    role: "Heavy helper",
    alias: "local-helper-heavy",
    model: "mistral-small:22b",
    note: "The strongest clean local general model proven in both CLI and Open WebUI on this machine.",
  },
  {
    role: "Reasoning fallback",
    alias: "local-reasoner-clean",
    model: "gpt-oss:20b",
    note: "Useful when you want heavier reasoning behavior, but it works best with lower visible thinking in tuned clients.",
  },
  {
    role: "Synthesis fallback",
    alias: "local-thinker-clean",
    model: "qwen2.5:14b",
    note: "Good for broader synthesis when the fast helper starts feeling too lossy.",
  },
];

const workflow = [
  {
    step: "01",
    title: "Retrieve narrowly",
    text: "Start with search and direct evidence: rg, probe, qmd, context7, or logs. The cheapest token win is not sending junk upstream.",
  },
  {
    step: "02",
    title: "Compress locally",
    text: "Offload repetitive context digestion to a tuned local helper with deterministic settings and a clear role.",
  },
  {
    step: "03",
    title: "Reason where it counts",
    text: "Keep final planning, code edits, and judgment with the stronger primary agent or the heaviest proven local fallback.",
  },
  {
    step: "04",
    title: "Prove behavior",
    text: "Validate with real browser behavior, logs, and artifacts so the lab stays grounded in what works on this hardware.",
  },
];

const evidence = [
  "Open WebUI chat was tested in a real browser session and returned a live model answer.",
  "mistral-small:22b is the biggest model proven working locally right now.",
  "qwen2.5-coder:14b is the best verified coding-oriented local model in the sweet spot.",
  "The setup documents why 30B+ attempts fail instead of pretending capacity is unlimited.",
];

export default function App() {
  return (
    <div className="page-shell">
      <div className="noise" />
      <header className="topbar">
        <a className="brand" href="#top">
          <span className="brand-mark" />
          <span>
            <strong>Local LLM Lab</strong>
            <em>Proof-backed local AI on Apple Silicon</em>
          </span>
        </a>
        <nav className="nav">
          <a href="#models">Models</a>
          <a href="#proof">Proof</a>
          <a href="#workflow">Workflow</a>
          <a href="#start">Start</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy reveal">
            <p className="eyebrow">Local AI that earns trust the hard way</p>
            <h1>Build, test, and ship a serious local LLM workstation.</h1>
            <p className="lede">
              Local LLM Lab packages Ollama, Open WebUI, role-tuned helper models,
              and browser-backed validation into one credible Apple Silicon setup.
              It is equal parts workstation, benchmark notebook, and public proof.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#start">
                Run the lab
              </a>
              <a className="button button-secondary" href="#proof">
                See proof
              </a>
            </div>
            <div className="hero-note">
              <span>Reality check</span>
              <p>
                Current Docker Ollama capacity favors the 9B to 14B class, with
                <strong> mistral-small:22b </strong>
                as the heaviest browser-proven model.
              </p>
            </div>
          </div>

          <aside className="hero-panel reveal">
            <div className="panel-label">Featured proof</div>
            <h2>Open WebUI validated with a real prompt</h2>
            <p>
              The browser session selected a tuned helper role, submitted a prompt,
              and confirmed a clean answer in the live transcript.
            </p>
            <img
              src="/assets/openwebui-proof.png"
              alt="Open WebUI proof screenshot showing a local helper response"
            />
            <dl className="mini-stats">
              <div>
                <dt>Runtime</dt>
                <dd>Docker Ollama + Docker Open WebUI</dd>
              </div>
              <div>
                <dt>Browser</dt>
                <dd>Playwright acceptance proof</dd>
              </div>
              <div>
                <dt>Outcome</dt>
                <dd>Local prompt-response path verified</dd>
              </div>
            </dl>
          </aside>
        </section>

        <section className="stats-grid reveal">
          {highlights.map((item) => (
            <article className="stat-card" key={item.label}>
              <span>{item.value}</span>
              <p>{item.label}</p>
            </article>
          ))}
        </section>

        <section className="section reveal">
          <div className="section-heading">
            <p className="eyebrow">Why this lab exists</p>
            <h2>Local AI is most compelling when it is both useful and accountable.</h2>
          </div>
          <div className="pillars">
            {pillars.map((pillar) => (
              <article className="pillar-card" key={pillar.title}>
                <h3>{pillar.title}</h3>
                <p>{pillar.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section reveal" id="models">
          <div className="section-heading split">
            <div>
              <p className="eyebrow">Role-tuned local models</p>
              <h2>Use the model that matches the job, not the one that sounds biggest.</h2>
            </div>
            <p className="section-copy">
              The lab’s strongest setup is a helper tier: fast, safe, coding-focused,
              heavy, and reasoning-flavored roles that fit the machine’s real envelope.
            </p>
          </div>
          <div className="model-grid">
            {models.map((model) => (
              <article className="model-card" key={model.alias}>
                <p className="model-role">{model.role}</p>
                <h3>{model.alias}</h3>
                <p className="model-base">{model.model}</p>
                <p>{model.note}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section reveal" id="proof">
          <div className="proof-layout">
            <div className="proof-copy">
              <p className="eyebrow">Proof-backed recommendations</p>
              <h2>Not just “compatible.” Actually run, actually seen, actually documented.</h2>
              <ul className="evidence-list">
                {evidence.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="proof-callout">
              <p className="callout-label">Current recommendation</p>
              <h3>Best clean general model</h3>
              <p className="callout-main">mistral-small:22b</p>
              <h3>Best coding-focused helper</h3>
              <p className="callout-main">qwen2.5-coder:14b</p>
              <h3>Best fast helper</h3>
              <p className="callout-main">qwen3.5:9b</p>
            </div>
          </div>
        </section>

        <section className="section reveal" id="workflow">
          <div className="section-heading">
            <p className="eyebrow">Agent offload architecture</p>
            <h2>A practical local workflow for coding agents and heavy context.</h2>
          </div>
          <div className="workflow-grid">
            {workflow.map((item) => (
              <article className="workflow-card" key={item.step}>
                <span>{item.step}</span>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section reveal" id="start">
          <div className="section-heading split">
            <div>
              <p className="eyebrow">Get started</p>
              <h2>Stand up the lab, create the role aliases, then validate in the browser.</h2>
            </div>
            <p className="section-copy">
              This setup is designed to be educational as well as practical, so the
              repo includes the scripts, model roles, and proof artifacts side by side.
            </p>
          </div>
          <div className="start-grid">
            <pre className="terminal-card">
              <code>{`./scripts/start-ollama.sh
./scripts/start-openwebui.sh
./scripts/setup-agent-offload-models.sh
OPENWEBUI_PASSWORD='<your-password>' ./scripts/setup-openwebui-role-models.sh`}</code>
            </pre>
            <div className="start-card">
              <h3>What you get</h3>
              <ul className="check-list">
                <li>Open WebUI running against your local Ollama runtime</li>
                <li>Role-named helper models for offload workflows</li>
                <li>Proof notes documenting what passed and what failed</li>
                <li>A clean landing page for sharing the project publicly</li>
              </ul>
              <div className="local-ui-card">
                <p className="callout-label">Open WebUI on this machine</p>
                <div className="local-ui-actions">
                  <a
                    className="button button-primary"
                    href="http://open-webui-lab.orb.local"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open via OrbStack
                  </a>
                  <a
                    className="button button-secondary"
                    href="http://localhost:3001"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Use localhost fallback
                  </a>
                </div>
                <p className="local-ui-note">
                  This only works on the Mac that is actually running the lab. If
                  the OrbStack hostname does not resolve, open OrbStack and make
                  sure the <strong>ollama-lab</strong> and <strong>open-webui-lab</strong>
                  containers are up, then fall back to the local port reported by
                  <code> ./scripts/status.sh</code>.
                </p>
                <p className="local-ui-note tailscale-note">
                  For safer access on your own devices from anywhere, this lab can
                  expose Open WebUI through private Tailscale HTTPS with
                  <code> ./scripts/enable-tailscale-openwebui.sh</code>. That keeps
                  the app inside your tailnet instead of publishing it openly to
                  the internet.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <p>Local LLM Lab is a practical Apple Silicon lab for local AI, model role design, and proof-backed workflows.</p>
      </footer>
    </div>
  );
}
