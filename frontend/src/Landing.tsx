import { lazy, Suspense, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  Database,
  Download,
  FileSpreadsheet,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Play,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import type { ReactNode } from "react";
import { demoPeriods, questions } from "./data/demo";
const RevenueChart = lazy(() => import("./RevenueChart"));

function Brand() {
  return (
    <a className="brand" href="#home" aria-label="SmartAnalytics AI home">
      <span className="brand-mark">
        <BarChart3 size={22} strokeWidth={2.5} />
      </span>
      SmartAnalytics<span className="ai-label">AI</span>
    </a>
  );
}
function LinkButton({
  children,
  href,
  secondary = false,
}: {
  children: ReactNode;
  href: string;
  secondary?: boolean;
}) {
  return (
    <a className={`button ${secondary ? "button-secondary" : ""}`} href={href}>
      {children}
    </a>
  );
}
function SectionHeading({
  eyebrow,
  title,
  accent,
  children,
}: {
  eyebrow: string;
  title: string;
  accent: string;
  children?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <span className="eyebrow">{eyebrow}</span>
      <h2>
        {title} <em>{accent}</em>
      </h2>
      {children && <p>{children}</p>}
    </div>
  );
}

function Dashboard() {
  const [period, setPeriod] = useState<keyof typeof demoPeriods>("6 months");
  const demo = demoPeriods[period];
  function download() {
    const blob = new Blob(
      [
        "month,revenue\n" +
          demo.data.map((row) => `${row.month},${row.revenue}`).join("\n"),
      ],
      { type: "text/csv;charset=utf-8" },
    );
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "smartanalytics-demo.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section
      id="demo"
      className="preview-section"
      aria-label="Interactive analytics demo"
    >
      <div className="preview-caption">
        <span>
          <span className="status-dot" /> A little clarity. A lot of
          possibility.
        </span>
        <span>
          INTERACTIVE PRODUCT PREVIEW <ArrowDown size={13} />
        </span>
      </div>
      <div className="dashboard-wrap">
        <aside className="floating-note">
          <span className="icon-tile">
            <Sparkles size={18} />
          </span>
          <div>
            <b>Your next insight, uncovered.</b>
            <p>Revenue is trending upward.</p>
            <span>Illustrative AI insight</span>
          </div>
        </aside>
        <div className="dashboard">
          <aside className="dash-sidebar">
            <div className="mini-brand">
              <span className="brand-mark">
                <BarChart3 size={18} />
              </span>
              <b>SmartAnalytics</b>
            </div>
            <div className="workspace-name">
              <span>N</span> Northstar workspace <ChevronDown size={12} />
            </div>
            <div className="sidebar-label">WORKSPACE</div>
            <div className="side-active">
              <LayoutDashboard size={15} /> Overview
            </div>
            <div>
              <Database size={15} /> Data sources
            </div>
            <div>
              <BarChart3 size={15} /> Reports
            </div>
            <div>
              <Sparkles size={15} /> AI assistant
            </div>
            <div className="sidebar-bottom">
              <span className="status-dot" /> Sample workspace
            </div>
          </aside>
          <div className="dash-main">
            <div className="dash-top">
              <span>
                Workspace <span className="muted">/</span> Overview
              </span>
              <span className="demo-label">DEMO DATA</span>
            </div>
            <div className="dash-title">
              <div>
                <h3>Your business, at a glance</h3>
                <p>A clearer picture of what’s moving your business.</p>
              </div>
              <button className="export-button" onClick={download}>
                <Download size={13} /> Export CSV
              </button>
            </div>
            <div className="metrics">
              {[
                ["Total revenue", demo.revenue, "+18.6%"],
                ["Active customers", demo.customers, "+12.8%"],
                ["Conversion rate", demo.conversion, "+2.4%"],
              ].map(([label, value, change]) => (
                <div className="metric" key={label}>
                  <span>
                    {label}
                    <ArrowUpRight size={14} />
                  </span>
                  <strong>{value}</strong>
                  <small>
                    <TrendingUp size={12} /> {change}{" "}
                    <span>illustrative change</span>
                  </small>
                </div>
              ))}
            </div>
            <div className="dash-charts">
              <div className="revenue-chart">
                <div className="chart-heading">
                  <div>
                    <b>Revenue overview</b>
                    <p>
                      <span className="legend-dot" /> Revenue{" "}
                      <span className="muted">· USD</span>
                    </p>
                  </div>
                  <label className="period-select">
                    <span className="sr-only">Demo period</span>
                    <select
                      value={period}
                      onChange={(event) =>
                        setPeriod(
                          event.target.value as keyof typeof demoPeriods,
                        )
                      }
                    >
                      {Object.keys(demoPeriods).map((key) => (
                        <option key={key}>{key}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <div
                  className="chart"
                  role="img"
                  aria-label={`Demo revenue chart for ${period}: ${demo.data.map((d) => `${d.month} $${d.revenue}`).join(", ")}`}
                >
                  <Suspense
                    fallback={
                      <div className="chart-loading">Loading sample chart?</div>
                    }
                  >
                    <RevenueChart data={demo.data} />
                  </Suspense>
                </div>
              </div>
              <div className="sources-card">
                <b>Revenue by channel</b>
                <p>Sample channel mix</p>
                <div className="donut">
                  <div>
                    <strong>100%</strong>
                    <span>total revenue</span>
                  </div>
                </div>
                <div className="channel-legend">
                  <span>
                    <i /> Organic <b>48%</b>
                  </span>
                  <span>
                    <i /> Direct <b>32%</b>
                  </span>
                  <span>
                    <i /> Referral <b>20%</b>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="floating-growth">
          <span className="growth-icon">
            <TrendingUp size={20} />
          </span>
          <span>
            Less guesswork.
            <br />
            <b>More forward.</b>
          </span>
          <ArrowUpRight size={23} />
        </div>
      </div>
      <p className="demo-disclaimer">
        A glimpse of the experience. All figures are sample data; connections
        and AI responses are illustrative.
      </p>
    </section>
  );
}

function Assistant() {
  const [selected, setSelected] = useState(0);
  return (
    <section id="assistant" className="assistant-section section-shell">
      <div className="assistant-copy">
        <span className="eyebrow">MEET YOUR AI THINKING PARTNER</span>
        <h2>
          Big questions.
          <br />
          <em>Clear answers.</em>
        </h2>
        <p>
          Explore what a conversation with your data could look like. Less
          digging through spreadsheets. More understanding what comes next.
        </p>
        <ul>
          <li>
            <Check size={16} /> Ask in everyday language
          </li>
          <li>
            <Check size={16} /> Understand the story behind the numbers
          </li>
          <li>
            <Check size={16} /> Turn a question into a next step
          </li>
        </ul>
        <a className="text-link" href="#assistant-demo">
          Try a sample question <ArrowRight size={17} />
        </a>
      </div>
      <div id="assistant-demo" className="assistant-card">
        <div className="assistant-header">
          <span className="icon-tile">
            <Sparkles size={19} />
          </span>
          <div>
            <b>SmartAnalytics Assistant</b>
            <p>Scripted preview · no live AI</p>
          </div>
          <span className="demo-label">DEMO</span>
        </div>
        <div className="chat-question">{questions[selected].question}</div>
        <div className="chat-response" aria-live="polite">
          <Sparkles size={19} />
          <div>
            <b>Here’s what your sample data tells us.</b>
            <p>{questions[selected].answer}</p>
            <div className="answer-stat">
              <TrendingUp size={18} />
              <strong>{questions[selected].stat}</strong>
              <span>{questions[selected].label}</span>
            </div>
            <small>Source: fictional Northstar dataset</small>
          </div>
        </div>
        <div className="suggestions">
          <span>EXPLORE A SAMPLE QUESTION</span>
          {questions.map((question, index) => (
            <button
              key={question.question}
              aria-pressed={selected === index}
              onClick={() => setSelected(index)}
            >
              {question.question}
              <ArrowUpRight size={14} />
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function Landing() {
  const [copyrightYear] = useState(() => new Date().getFullYear());
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header id="home" className="navbar section-shell">
        <Brand />
        <nav
          aria-label="Main navigation"
          className={menuOpen ? "nav-links open" : "nav-links"}
        >
          <a onClick={() => setMenuOpen(false)} href="#features">
            Features
          </a>
          <a onClick={() => setMenuOpen(false)} href="#how-it-works">
            How it works
          </a>
          <a onClick={() => setMenuOpen(false)} href="#assistant">
            AI Assistant <span className="nav-new">NEW</span>
          </a>
        </nav>
        <a className="nav-cta" href="#demo">
          Explore the demo <ArrowUpRight size={16} />
        </a>
        <button
          className="mobile-toggle"
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X /> : <Menu />}
        </button>
      </header>
      <main id="main">
        <section className="hero section-shell">
          <div className="hero-badge">
            <span className="status-dot" /> A fresh perspective on your data{" "}
            <ArrowUpRight size={13} />
          </div>
          <h1>
            Less data overload.
            <br />
            More <em>“now I get it.”</em>
            <span className="hero-spark">✳</span>
          </h1>
          <p>
            Your data has a story. Let’s make it clear.
            <br />
            {" "}Turn everyday numbers into meaningful insights, with AI by your
            side.
          </p>
          <div className="hero-actions">
            <LinkButton href="/app">
              Start Analyzing <ArrowUpRight size={17} />
            </LinkButton>
            <LinkButton href="#how-it-works" secondary>
              <span className="play-icon">
                <Play size={11} fill="currentColor" />
              </span>{" "}
              See how it works
            </LinkButton>
          </div>
          <div className="hero-footnote">
            <span>
              <Check size={13} /> Interactive preview, no account needed
            </span>
            <span>
              <Check size={13} /> Private account for real data
            </span>
          </div>
          <span className="hero-decoration decoration-one" aria-hidden="true">
            ✳
          </span>
          <span className="hero-decoration decoration-two" aria-hidden="true">
            ✧
          </span>
        </section>
        <Dashboard />
        <div className="format-strip section-shell">
          <span>FROM SCATTERED NUMBERS TO A SHARED PICTURE</span>
          <div>
            <FileSpreadsheet /> Spreadsheets <i /> <Database /> Databases <i />{" "}
            <BarChart3 /> Business metrics <i /> <Sparkles /> Clearer insights
          </div>
          <small>
            A vision for connected analytics. Integrations are not available in
            this preview.
          </small>
        </div>
        <section id="features" className="features-section section-shell">
          <SectionHeading
            eyebrow="LESS FRICTION. MORE UNDERSTANDING."
            title="A clearer way to"
            accent="see your business."
          >
            Built around the questions that matter, and the people asking them.
          </SectionHeading>
          <div className="feature-grid">
            <article className="feature-card">
              <div className="feature-visual source-visual">
                <div>
                  <FileSpreadsheet size={21} />
                  <span>sales_data.csv</span>
                  <Check size={14} />
                </div>
                <div>
                  <Database size={21} />
                  <span>One shared picture</span>
                  <ArrowRight size={15} />
                </div>
                <span className="visual-caption">
                  THE VISION: EVERYTHING CONNECTED
                </span>
              </div>
              <span className="feature-number">01 / CONNECT</span>
              <h3>Bring your data together.</h3>
              <p>
                Imagine your spreadsheets and business data in one place, ready
                to explore.
              </p>
            </article>
            <article className="feature-card">
              <div className="feature-visual bars-visual">
                <span className="mini-chart-label">
                  The bigger picture <TrendingUp size={14} />
                </span>
                <div className="mini-bars">
                  {[34, 49, 42, 63, 56, 77, 91].map((height, index) => (
                    <span key={index} style={{ height: `${height}%` }} />
                  ))}
                </div>
                <span className="visual-caption">ILLUSTRATIVE CHART</span>
              </div>
              <span className="feature-number">02 / EXPLORE</span>
              <h3>Find the signal in the noise.</h3>
              <p>
                Make patterns easier to spot with thoughtful dashboards and
                clear visual stories.
              </p>
            </article>
            <article className="feature-card">
              <div className="feature-visual insight-visual">
                <span className="icon-tile">
                  <Sparkles size={18} />
                </span>
                <b>A little insight goes a long way.</b>
                <p>“What’s driving our growth?”</p>
                <span className="insight-pill">
                  Let’s connect the dots <ArrowUpRight size={12} />
                </span>
              </div>
              <span className="feature-number">03 / UNDERSTAND</span>
              <h3>Ask better. Understand more.</h3>
              <p>
                A conversational approach to analytics, designed to make the
                next step clearer.
              </p>
            </article>
          </div>
        </section>
        <section id="how-it-works" className="how-section">
          <div className="section-shell">
            <SectionHeading
              eyebrow="FROM NUMBERS TO YOUR NEXT MOVE"
              title="A simple path to"
              accent="your aha moment."
            >
              The experience we’re building, in three thoughtful steps.
            </SectionHeading>
            <div className="steps">
              {[
                {
                  icon: Database,
                  title: "Start with your data",
                  text: "Bring the numbers you already work with. The future platform will connect your sources.",
                },
                {
                  icon: MessageSquare,
                  title: "Follow your curiosity",
                  text: "Explore a dashboard or ask a question in plain language. Start with our sample preview.",
                },
                {
                  icon: TrendingUp,
                  title: "See your next step",
                  text: "Understand patterns and put your findings into perspective. Make room for better decisions.",
                },
              ].map(({ icon: Icon, title, text }, index) => (
                <article key={title}>
                  <div className="step-top">
                    <span className="step-icon">
                      <Icon size={23} />
                    </span>
                    <span>0{index + 1}</span>
                  </div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
        <Assistant />
        <section className="final-cta section-shell">
          <span className="cta-star" aria-hidden="true">
            ✳
          </span>
          <span className="eyebrow">YOUR NEXT AHA MOMENT STARTS HERE</span>
          <h2>
            Make space for
            <br />
            <em>clearer thinking.</em>
          </h2>
          <p>Get a feel for a more intuitive relationship with your data.</p>
          <LinkButton href="#demo">
            Take a look around <ArrowUpRight size={17} />
          </LinkButton>
          <span className="cta-note">
            <ShieldCheck size={13} /> Sample data only. No account required.
          </span>
        </section>
      </main>
      <footer className="footer section-shell">
        <div className="footer-main">
          <div>
            <Brand />
            <p>A fresh perspective on your data.</p>
          </div>
          <nav aria-label="Footer navigation">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#assistant">AI Assistant</a>
            <a href="#demo">
              Explore demo <ArrowUpRight size={13} />
            </a>
          </nav>
        </div>
        <div className="footer-bottom">
          <span>© {copyrightYear} SmartAnalytics AI</span>
          <span>Thoughtfully built. A little more clarity.</span>
          <span className="prototype-label">
            <span className="status-dot" /> Landing page prototype
          </span>
        </div>
      </footer>
    </>
  );
}
export default Landing;
