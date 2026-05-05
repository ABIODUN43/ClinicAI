import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { clearStoredUser, loadStoredUser, persistUser } from "./auth";
import {
  analyzeNewsRecord,
  createNewsRecord,
  createNotification,
  createSignal,
  deleteSymptomReport,
  createSymptomReport,
  createWeatherRecord,
  fetchAlertsData,
  fetchAlertsList,
  fetchAnalyticsData,
  fetchClinicReports,
  fetchContactPreferences,
  fetchCurrentUser,
  fetchDatasetStatus,
  fetchHomeData,
  fetchHistoricalReports,
  fetchModelHistory,
  fetchModelStatus,
  fetchNewsRecords,
  fetchNotifications,
  fetchPredictions,
  fetchRecommendations,
  fetchSignals,
  fetchSymptomReports,
  fetchWeatherRecords,
  generateDailyReport,
  generateNotifications,
  loginWithGoogle,
  runLiveWeatherIngestion,
  runAutoDatasetRefresh,
  saveContactPreference,
  sendQueuedEmailNotifications,
  sendQueuedSmsNotifications,
  sendQueuedWhatsAppNotifications,
  runTrustedNewsIngestion,
  trainModel,
  updateSymptomReport,
  runPipelineAnalysis
} from "./api";

const ROLE_CAPABILITIES = {
  clinic: {
    analytics: false,
    dataOps: false
  },
  public_health: {
    analytics: true,
    dataOps: false
  },
  admin: {
    analytics: true,
    dataOps: true
  }
};

function getRole(user) {
  return user?.role || "admin";
}

function canAccess(user, area) {
  const role = getRole(user);
  const capabilities = ROLE_CAPABILITIES[role] || ROLE_CAPABILITIES.admin;
  return capabilities[area] ?? true;
}

function normalizeNigeriaPhone(value) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "+234";
  }
  if (trimmed === "+") {
    return "+234";
  }
  if (trimmed.startsWith("+234")) {
    return `+234${trimmed.slice(4).replace(/\D/g, "")}`;
  }
  if (trimmed.startsWith("234")) {
    return `+234${trimmed.slice(3).replace(/\D/g, "")}`;
  }
  if (trimmed.startsWith("0")) {
    return `+234${trimmed.slice(1).replace(/\D/g, "")}`;
  }
  const digits = trimmed.replace(/\D/g, "");
  return `+234${digits}`;
}

function readableError(error) {
  if (!error) {
    return "Something went wrong.";
  }
  if (typeof error === "string") {
    return error;
  }
  if (typeof error.message === "string" && error.message) {
    return error.message;
  }
  try {
    return JSON.stringify(error);
  } catch {
    return "Something went wrong.";
  }
}

function emptyAnalyticsData() {
  return {
    summary_metrics: [],
    disease_probabilities: [],
    classified_signals: [],
    recommendations: [],
    demo_scenario: {
      copy: "Analytics is not part of the clinic role workspace."
    }
  };
}

function App() {
  const [session, setSession] = useState(() => loadStoredUser());
  const [homeData, setHomeData] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [alertsData, setAlertsData] = useState(null);
  const [dataError, setDataError] = useState("");
  const user = session?.user || null;

  useEffect(() => {
    if (session) {
      persistUser(session);
    }
  }, [session]);

  useEffect(() => {
    if (!session?.access_token) {
      return;
    }

    let cancelled = false;

    async function loadDashboard() {
      try {
        const profile = await fetchCurrentUser(session.access_token);
        const [home, alerts, analytics] = await Promise.all([
          fetchHomeData(session.access_token),
          fetchAlertsData(session.access_token),
          canAccess(profile, "analytics")
            ? fetchAnalyticsData(session.access_token)
            : Promise.resolve(emptyAnalyticsData())
        ]);

        if (cancelled) {
          return;
        }

        setSession((current) => ({
          ...(current || {}),
          access_token: current?.access_token || session.access_token,
          user: profile
        }));
        setHomeData(home);
        setAnalyticsData(analytics);
        setAlertsData(alerts);
        setDataError("");
      } catch (error) {
        if (cancelled) {
          return;
        }

        clearStoredUser();
        setSession(null);
        setHomeData(null);
        setAnalyticsData(null);
        setAlertsData(null);
        setDataError(error.message);
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [session?.access_token]);

  const initials = useMemo(() => {
    if (!user?.name) {
      return "CA";
    }

    return user.name
      .split(" ")
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("");
  }, [user]);

  if (!session?.access_token || !user) {
    return <LoginScreen onLogin={setSession} error={dataError} />;
  }

  if (!homeData || !analyticsData || !alertsData) {
    return (
      <div className="login-page">
        <div className="login-panel">
          <div className="brand">
            <BrandMark />
            <div className="brand-copy">
              <h1>ClinicAI Sentinel</h1>
              <p>Loading outbreak intelligence</p>
            </div>
          </div>
          <p className="muted">Connecting to the FastAPI backend and loading dashboard data.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar user={user} />
      <main className="main">
        <Routes>
          <Route path="/" element={<HomePage initials={initials} user={user} data={homeData} token={session.access_token} />} />
          <Route path="/risk-map" element={<RiskMapPage initials={initials} user={user} data={homeData} alertsData={alertsData} />} />
          <Route path="/recommendations" element={<RecommendationsPage initials={initials} user={user} token={session.access_token} />} />
          <Route path="/clinic-intake" element={<ClinicIntakePage initials={initials} user={user} token={session.access_token} />} />
          <Route path="/news" element={<NewsPage initials={initials} user={user} token={session.access_token} />} />
          <Route path="/weather" element={<WeatherPage initials={initials} user={user} token={session.access_token} />} />
          <Route
            path="/analytics"
            element={
              canAccess(user, "analytics")
                ? <AnalyticsPage initials={initials} user={user} data={analyticsData} token={session.access_token} />
                : <RestrictedPage initials={initials} user={user} area="Analytics" />
            }
          />
          <Route path="/alerts" element={<AlertsPage initials={initials} user={user} data={alertsData} />} />
          <Route
            path="/data-ops"
            element={
              canAccess(user, "dataOps")
                ? <DataOpsPage initials={initials} user={user} token={session.access_token} />
                : <RestrictedPage initials={initials} user={user} area="Data Ops" />
            }
          />
        </Routes>
      </main>
      <button
        className="floating-logout"
        type="button"
        onClick={() => {
          if (window.google?.accounts?.id) {
            window.google.accounts.id.disableAutoSelect();
          }

          clearStoredUser();
          setSession(null);
          setHomeData(null);
          setAnalyticsData(null);
          setAlertsData(null);
        }}
      >
        Sign out
      </button>
    </div>
  );
}

function LoginScreen({ onLogin, error: upstreamError }) {
  const [error, setError] = useState("");
  const [selectedRole, setSelectedRole] = useState("admin");
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const canUseGoogle = Boolean(clientId);

  useEffect(() => {
    if (!canUseGoogle) {
      setError("Google login is not configured yet. You can still open the demo dashboard below.");
      return;
    }

    let mounted = true;
    let attempts = 0;

    const mountButton = () => {
      if (!mounted) {
        return;
      }

      if (!window.google?.accounts?.id) {
        attempts += 1;

        if (attempts < 30) {
          window.setTimeout(mountButton, 250);
          return;
        }

        setError("Google Identity Services could not load. Check your connection and client ID.");
        return;
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            const session = await loginWithGoogle(response.credential, selectedRole);
            onLogin(session);
          } catch (loginError) {
            setError(loginError.message);
          }
        }
      });

      const target = document.getElementById("google-signin");

      if (!target) {
        return;
      }

      target.innerHTML = "";
      window.google.accounts.id.renderButton(target, {
        theme: "outline",
        size: "large",
        width: 320,
        shape: "pill",
        text: "signin_with"
      });
    };

    mountButton();

    return () => {
      mounted = false;
    };
  }, [canUseGoogle, clientId, onLogin, selectedRole]);

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="brand">
          <BrandMark />
          <div className="brand-copy">
            <h1>ClinicAI Sentinel</h1>
            <p>AI early warning for clinics in Nigeria</p>
          </div>
        </div>
        <div className="tag red">Secure access</div>
        <h2>Sign in to the ClinicAI Sentinel response workspace.</h2>
        <p className="muted">
          This workspace combines early warning, Lassa fever risk prediction, and decision support for healthcare teams. Sign in with Google to access the live dashboard.
        </p>
        <div className="login-points">
          <div className="priority-item">
            <span>After login</span>
            <strong>Open the surveillance home page</strong>
          </div>
          <div className="priority-item">
            <span>Analytics</span>
            <strong>Review prediction and classification trends</strong>
          </div>
          <div className="priority-item">
            <span>Alerts</span>
            <strong>Compare all diseases in one board</strong>
          </div>
        </div>
        <div id="google-signin" className="google-button-slot"></div>
        <button
          className="btn primary demo-button"
          type="button"
          onClick={() =>
            onLogin({
              access_token: selectedRole === "admin" ? "demo-session-admin" : selectedRole === "public_health" ? "demo-session-public_health" : "demo-session-clinic",
              user: {
                email: selectedRole === "admin" ? "admin@clinicai-sentinel.local" : selectedRole === "public_health" ? "publichealth@clinicai-sentinel.local" : "clinic@clinicai-sentinel.local",
                name: selectedRole === "admin" ? "Admin User" : selectedRole === "public_health" ? "Public Health Officer" : "Clinic User",
                role: selectedRole
              }
            })
          }
        >
          Continue with local access
        </button>
        <label className="filter-field">
          <span className="tiny muted">Access role</span>
          <select value={selectedRole} onChange={(event) => setSelectedRole(event.target.value)}>
            <option value="admin">Admin / Data Ops</option>
            <option value="public_health">Public Health Officer</option>
            <option value="clinic">Clinic User</option>
          </select>
        </label>
        {error || upstreamError ? <p className="auth-error">{error || upstreamError}</p> : null}
        <p className="tiny muted">
          Expected env key: <code>VITE_GOOGLE_CLIENT_ID</code>
        </p>
      </div>
    </div>
  );
}

function Sidebar({ user }) {
  const role = getRole(user);
  return (
    <aside className="sidebar">
      <div className="brand">
        <BrandMark />
        <div className="brand-copy">
          <h1>ClinicAI Sentinel</h1>
          <p>Clinic early warning for Nigeria</p>
        </div>
      </div>

      <div className="nav-group">
        <p className="section-title">Main</p>
        <AppNavLink end to="/">
          Home
        </AppNavLink>
        <AppNavLink to="/recommendations">Recommendations</AppNavLink>
        <AppNavLink to="/clinic-intake">Clinic Intake</AppNavLink>
        <AppNavLink to="/risk-map">Risk Map</AppNavLink>
        <AppNavLink to="/news">News Feed</AppNavLink>
        <AppNavLink to="/weather">Weather Feed</AppNavLink>
        {canAccess(user, "analytics") ? <AppNavLink to="/analytics">Analytics</AppNavLink> : null}
        <AppNavLink to="/alerts">Disease Alerts</AppNavLink>
        {canAccess(user, "dataOps") ? <AppNavLink to="/data-ops">Data Ops</AppNavLink> : null}
      </div>

      <div className="sidebar-card">
        <p className="section-title">Today</p>
        <div className="status-chip green">Role: {role.replace("_", " ")}</div>
        <div className="status-chip red">High surveillance focus</div>
        <p className="muted">
          Lassa fever mentions and case-like signals remain elevated in Ondo, Edo, and Ebonyi.
        </p>
      </div>
    </aside>
  );
}

function AppNavLink({ children, ...props }) {
  return (
    <NavLink
      {...props}
      className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
    >
      <span className="nav-dot"></span>
      {children}
    </NavLink>
  );
}

function BrandMark() {
  const logoSources = ["/brand-virus-logo.png", "/brand-virus-logo.svg"];
  const [logoIndex, setLogoIndex] = useState(0);

  return (
    <div className="brand-mark" aria-hidden="true">
      {logoIndex < logoSources.length ? (
        <img
          className="brand-logo-image"
          src={logoSources[logoIndex]}
          alt=""
          onError={() => setLogoIndex((current) => current + 1)}
        />
      ) : (
        <svg viewBox="0 0 120 120" className="brand-virus" role="presentation">
          <defs>
            <radialGradient id="virusBody" cx="38%" cy="34%" r="62%">
              <stop offset="0%" stopColor="#ffd4e3" />
              <stop offset="22%" stopColor="#f08ab0" />
              <stop offset="60%" stopColor="#c41f54" />
              <stop offset="100%" stopColor="#6d0820" />
            </radialGradient>
            <radialGradient id="virusTip" cx="35%" cy="35%" r="70%">
              <stop offset="0%" stopColor="#ffe6ef" />
              <stop offset="38%" stopColor="#e4688f" />
              <stop offset="100%" stopColor="#781028" />
            </radialGradient>
            <linearGradient id="virusStem" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f2a6c4" />
              <stop offset="100%" stopColor="#7c102a" />
            </linearGradient>
          </defs>

          <g className="virus-spikes">
            <g transform="translate(60 60) rotate(0)">
              <rect x="-2.2" y="-48" width="4.4" height="22" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-50" r="6.7" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(30)">
              <rect x="-2.2" y="-49" width="4.4" height="20" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-51" r="6.5" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(58)">
              <rect x="-2.2" y="-50" width="4.4" height="22" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-52" r="7" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(88)">
              <rect x="-2.2" y="-53" width="4.4" height="24" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-55" r="8.2" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(122)">
              <rect x="-2.2" y="-49" width="4.4" height="21" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-51" r="6.8" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(150)">
              <rect x="-2.2" y="-47" width="4.4" height="20" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-49" r="6.3" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(182)">
              <rect x="-2.2" y="-52" width="4.4" height="23" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-54" r="7.8" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(210)">
              <rect x="-2.2" y="-50" width="4.4" height="21" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-52" r="7" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(238)">
              <rect x="-2.2" y="-48" width="4.4" height="20" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-50" r="6.4" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(268)">
              <rect x="-2.2" y="-50" width="4.4" height="21" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-52" r="6.8" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(300)">
              <rect x="-2.2" y="-52" width="4.4" height="23" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-54" r="7.3" fill="url(#virusTip)" />
            </g>
            <g transform="translate(60 60) rotate(332)">
              <rect x="-2.2" y="-49" width="4.4" height="20" rx="2.2" fill="url(#virusStem)" />
              <circle cx="0" cy="-51" r="6.2" fill="url(#virusTip)" />
            </g>
          </g>

          <circle cx="60" cy="60" r="34" fill="url(#virusBody)" />
          <circle cx="50" cy="49" r="5" fill="rgba(255, 232, 241, 0.55)" />
          <circle cx="79" cy="52" r="4" fill="rgba(255, 212, 226, 0.42)" />
          <circle cx="41" cy="74" r="3.5" fill="rgba(255, 212, 226, 0.28)" />
          <ellipse cx="73" cy="73" rx="12" ry="17" fill="rgba(91, 3, 22, 0.22)" />
        </svg>
      )}
    </div>
  );
}

function Topbar({ title, subtitle, chipTone, chipText, user, initials }) {
  return (
    <div className="topbar">
      <div className="page-title">
        <p className="muted">{subtitle}</p>
        <h2>{title}</h2>
      </div>
      <div className="profile">
        <div className={`status-chip ${chipTone}`}>{chipText}</div>
        <div className="user-card">
          {user?.imageUrl ? <img className="avatar-image" src={user.imageUrl} alt={user.name} /> : <div className="avatar">{initials}</div>}
          <div>
            <strong>{user?.name}</strong>
            <div className="tiny muted">{user?.email}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function NotificationContactCard({ token, user, title, description }) {
  const role = getRole(user);
  const [form, setForm] = useState({
    name: user?.name || "",
    email: user?.email || "",
    location: "",
    sms_number: "+234",
    whatsapp_number: "+234"
  });
  const [status, setStatus] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadPreference() {
      try {
        const records = await fetchContactPreferences(token, {
          email: user?.email,
          role
        });
        if (cancelled || !records.length) {
          return;
        }
        const latest = records[0];
        setForm({
          name: latest.name || user?.name || "",
          email: latest.email || user?.email || "",
          location: latest.location || "",
          sms_number: latest.sms_number || "+234",
          whatsapp_number: latest.whatsapp_number || "+234"
        });
      } catch {
        // Keep the page usable even if preference lookup fails.
      }
    }

    if (token && user?.email) {
      loadPreference();
    }

    return () => {
      cancelled = true;
    };
  }, [token, user?.email, user?.name, role]);

  async function savePreference() {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/api/contact-preferences`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          ...form,
          role
        })
      });
      const saved = await response.json();
      if (!response.ok) {
        throw new Error(readableError(saved?.detail));
      }
      const savedChannels = [
        saved.sms_number ? "SMS" : null,
        saved.whatsapp_number ? "WhatsApp" : null,
        saved.email ? "email" : null
      ].filter(Boolean);
      setStatus(
        savedChannels.length
          ? `Submitted successfully. Saved for ${savedChannels.join(", ")} notifications.`
          : "Submitted successfully."
      );
    } catch (error) {
      setStatus(readableError(error));
    }
  }

  return (
    <article className="card">
      <div className="card-header">
        <div>
          <h3>{title}</h3>
          <p className="muted">{description}</p>
        </div>
      </div>
      <div className="form-grid form-grid-2">
        <FilterInput label="Name" value={form.name} onChange={(value) => setForm((current) => ({ ...current, name: value }))} placeholder="Your name" />
        <FilterInput label="Location" value={form.location} onChange={(value) => setForm((current) => ({ ...current, location: value }))} placeholder="Ondo" />
        <FilterInput label="Email" value={form.email} onChange={(value) => setForm((current) => ({ ...current, email: value }))} placeholder="your@email.com" />
        <FilterInput label="SMS number" value={form.sms_number} onChange={(value) => setForm((current) => ({ ...current, sms_number: normalizeNigeriaPhone(value) }))} placeholder="+2348000000000" />
        <FilterInput label="WhatsApp number" value={form.whatsapp_number} onChange={(value) => setForm((current) => ({ ...current, whatsapp_number: normalizeNigeriaPhone(value) }))} placeholder="+2348000000000" />
      </div>
      <div className="form-actions">
        <button className="btn secondary" type="button" onClick={savePreference}>
          Save contact details
        </button>
      </div>
      <div className="footer-note">
        Save your notification contacts here first. Live phone delivery still depends on a real SMS or WhatsApp provider being configured for the system.
      </div>
      {status ? <p className="success-copy">{status}</p> : null}
    </article>
  );
}

function HomePage({ initials, user, data, token }) {
  const role = getRole(user);

  if (role === "clinic") {
    return <ClinicHomePage initials={initials} user={user} data={data} token={token} />;
  }

  if (role === "public_health") {
    return <PublicHealthHomePage initials={initials} user={user} data={data} token={token} />;
  }

  return <AdminHomePage initials={initials} user={user} data={data} />;
}

function AdminHomePage({ initials, user, data }) {
  return (
    <>
      <Topbar
        title={data.product.tagline}
        subtitle="Home page"
        chipTone="amber"
        chipText="42 new unreviewed signals"
        user={user}
        initials={initials}
      />

      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="tag red">{data.hero.tag}</div>
            <h2>{data.hero.title}</h2>
            <p>{data.hero.description}</p>
            <div className="footer-note hero-note">{data.product.summary}</div>
            <div className="hero-actions">
              <NavLink className="btn primary" to="/analytics">
                Open analytics view
              </NavLink>
              <NavLink className="btn secondary" to="/alerts">
                Compare disease alerts
              </NavLink>
            </div>
          </div>

          <div className="hero-side">
            {data.hero.metrics.map((item) => (
              <MetricPanel
                key={item.label}
                value={item.value}
                label={item.label}
                tone={item.tone}
                status={item.status}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="grid-3">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Why ClinicAI Sentinel matters</h3>
              <p className="muted">A competition-ready articulation of the problem and your value.</p>
            </div>
          </div>
          <div className="feed">
            {data.why_cards.map((item) => (
              <InfoRow key={item.title} title={item.title} copy={item.copy} />
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Five-layer system design</h3>
              <p className="muted">Frontend and backend now reflect the full system architecture.</p>
            </div>
          </div>
          <div className="feed">
            {data.layers.map((item) => (
              <InfoRow key={item.title} title={item.title} copy={item.copy} />
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Quick action panel</h3>
              <p className="muted">Designed to reduce time from detection to response.</p>
            </div>
          </div>
          <div className="feed">
            {data.actions.map((item) => (
              <ActionRow key={item.title} title={item.title} tone={item.tone} status={item.status} />
            ))}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Monitored data sources</h3>
              <p className="muted">The inputs that make the system more credible and more useful.</p>
            </div>
          </div>
          <div className="feed">
            {data.data_sources.map((item) => (
              <InfoRow key={item.title} title={item.title} copy={item.copy} />
            ))}
          </div>
        </article>

        <article className="card map-card">
          <div className="card-header">
            <div>
              <h3>Nigeria surveillance map</h3>
              <p className="muted">Hotspot-first visual for rapid situational awareness.</p>
            </div>
            <div className="status-chip red">3 severe clusters</div>
          </div>
          <div className="nigeria-map">
            <div className="map-shape"></div>
            <div className="map-pill pill-ondo">Ondo: Red</div>
            <div className="map-pill pill-ebonyi">Ebonyi: Red</div>
            <div className="map-pill pill-bauchi">Bauchi: Amber</div>
            <div className="map-pill pill-edo">Edo: Red</div>
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Latest high-signal feed</h3>
              <p className="muted">Curated cards should prioritize confidence and location.</p>
            </div>
          </div>
          <div className="feed">
            {data.feed.map((item) => (
              <div className="feed-item" key={item.title}>
                <div>
                  <div className="signal-title">{item.title}</div>
                  <div className="feed-meta">
                    {item.tags.map((tag) => (
                      <span className={`tag ${tag.tone}`} key={tag.label}>
                        {tag.label}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Admin oversight</h3>
              <p className="muted">A high-level view of platform operations for the admin role.</p>
            </div>
          </div>
          <div className="disease-stats">
            <StatBox value="Live" label="Ingestion status" />
            <StatBox value="Daily" label="Automation cycle" />
            <StatBox value="3" label="Priority channels active" />
            <StatBox value="Ready" label="Model baseline state" />
          </div>
          <div className="feed">
            <InfoRow title="Data layer" copy="Historical data, weather, symptom intake, and news ingestion are all part of the current operational stack." />
            <InfoRow title="Decision layer" copy="Predictions, alerts, recommendations, and notification generation are available from one admin workspace." />
            <InfoRow title="What to check next" copy="Use Data Ops for ingestion refresh, notifications, training status, and report export verification." />
          </div>
        </article>

        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Priority states to review</h3>
              <p className="muted">Ranked for investigator focus and field response planning.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>State</th>
                <th>Disease</th>
                <th>Alert</th>
                <th>Signal count</th>
              </tr>
            </thead>
            <tbody>
              {data.priority_states.map((row) => (
                <tr key={`${row.state}-${row.disease}`}>
                  <td>{row.state}</td>
                  <td>{row.disease}</td>
                  <td>
                    <span className={`tag ${row.alert.toLowerCase()}`}>{row.alert}</span>
                  </td>
                  <td>{row.signals}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Summary and impact</h3>
              <p className="muted">Summary and impact.</p>
            </div>
          </div>
          <div className="footer-note">
            {data.product.summary}
          </div>
          <div className="feed">
            {data.impact_points.map((item) => (
              <InfoRow key={item} title="Impact" copy={item} />
            ))}
          </div>
          <div className="feed differentiator-list">
            {data.differentiators.map((item) => (
              <InfoRow key={item} title="What makes you different" copy={item} />
            ))}
          </div>
          <div className="footer-note">
            The product should feel calm, operational, and useful inside clinics. Prediction is only half the story; the recommendation layer is what makes ClinicAI Sentinel competitive.
          </div>
        </article>
      </section>
    </>
  );
}

function ClinicHomePage({ initials, user, data, token }) {
  return (
    <>
      <Topbar
        title="Clinic response workspace"
        subtitle="Clinic home"
        chipTone="red"
        chipText="Frontline operations"
        user={user}
        initials={initials}
      />

      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="tag red">Clinical focus</div>
            <h2>Act quickly on screening, alerts, and response guidance.</h2>
            <p>
              This view is tailored for healthcare teams that need immediate awareness of high-risk signals, symptom escalation,
              and what to do next inside the clinic.
            </p>
            <div className="footer-note hero-note">
              Prediction is only useful if it changes frontline action. This clinic view keeps the workload focused on reporting,
              alerts, and response steps.
            </div>
            <div className="hero-actions">
              <NavLink className="btn primary" to="/clinic-intake">
                Submit symptom intake
              </NavLink>
              <NavLink className="btn secondary" to="/recommendations">
                Open recommendations
              </NavLink>
            </div>
          </div>

          <div className="hero-side">
            <MetricPanel value="High" label="Current clinic watch level" tone="red" status="Escalate triage" />
            <MetricPanel value="3" label="States with severe Lassa clusters" tone="amber" status="Review daily" />
            <MetricPanel value="4" label="Immediate action steps recommended" tone="green" status="Ready now" />
          </div>
        </div>
      </section>

      <section className="grid-3">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>What clinic teams should do now</h3>
              <p className="muted">Short operational guidance instead of system internals.</p>
            </div>
          </div>
          <div className="feed">
            {data.actions.slice(0, 4).map((item) => (
              <ActionRow key={item.title} title={item.title} tone={item.tone} status={item.status} />
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Immediate symptoms to watch</h3>
              <p className="muted">The symptom pattern with the highest triage value for Lassa fever review.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Fever and weakness" copy="Escalate repeated fever with unusual weakness, especially when clustered in the same community." />
            <InfoRow title="Vomiting and bleeding signs" copy="Treat these as high-priority indicators when paired with known outbreak history or rodent exposure." />
            <InfoRow title="Contact and exposure history" copy="Ask about rodent exposure, shared food storage, and contact with suspected infected persons." />
            <InfoRow title="Next step in the app" copy="Open Clinic Intake to capture the symptom report that will feed surveillance analysis." />
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Recommended clinic actions</h3>
              <p className="muted">Keep the response layer visible at all times.</p>
            </div>
          </div>
          <div className="feed">
            {data.actions.slice(0, 3).map((item) => (
              <InfoRow key={`clinic-action-${item.title}`} title={item.title} copy={`Status: ${item.status}.`} />
            ))}
            <InfoRow title="Isolation readiness" copy="Prepare the isolation area and brief the duty team when alert pressure rises." />
            <InfoRow title="Data capture" copy="Use Clinic Intake every day so symptom trends from your facility become part of the evidence base." />
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Fast navigation for clinics</h3>
              <p className="muted">The pages most relevant to day-to-day clinical response.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Clinic Intake" copy="Use this page first to submit symptom counts from the clinic or community outreach team." />
            <InfoRow title="Disease Alerts" copy="Use this first when you need to compare red, amber, and green outcomes across diseases." />
            <InfoRow title="News Feed" copy="Check verified outbreak narratives and community signal context before escalation." />
            <InfoRow title="Weather Feed" copy="Use this to understand environmental pressure that may affect rodent-human contact risk." />
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Clinic summary message</h3>
              <p className="muted">A calm, practical framing for healthcare workers.</p>
            </div>
          </div>
          <div className="footer-note">
            ClinicAI Sentinel should feel like an early warning teammate for hospital staff: simple, fast, and centered on
            what to screen, what to escalate, and what to prepare next.
          </div>
        </article>
      </section>

      <section className="grid-2">
        <NotificationContactCard
          token={token}
          user={user}
          title="Clinic notification contacts"
          description="Save the clinic phone numbers you want to receive SMS or WhatsApp outbreak alerts on."
        />
      </section>
    </>
  );
}

function PublicHealthHomePage({ initials, user, data, token }) {
  const focusOptions = data.priority_states.map((item) => item.state);
  const [selectedState, setSelectedState] = useState(focusOptions[0] || "");
  const selectedPriorityState = data.priority_states.find((item) => item.state === selectedState) || data.priority_states[0];
  const regionalTrend = data.priority_states.slice(0, 5);
  const maxSignalCount = Math.max(1, ...regionalTrend.map((item) => item.signalCount || item.signals || 0));
  const situationBrief = selectedPriorityState
    ? [
        "ClinicAI Sentinel Public Health Situation Brief",
        "",
        `Location: ${selectedPriorityState.state}`,
        `Disease: ${selectedPriorityState.disease}`,
        `Alert level: ${selectedPriorityState.alert}`,
        `Tracked signals: ${selectedPriorityState.signalCount || selectedPriorityState.signals}`,
        `Recommended response: ${selectedPriorityState.action}`,
        "",
        `Interpretation: ${selectedPriorityState.state} remains a priority review location because the current surveillance evidence supports continued public-health monitoring.`,
        "Operational note: Use this brief for internal coordination, field escalation, and fast stakeholder updates."
      ].join("\n")
    : "";

  return (
    <>
      <Topbar
        title="Public health monitoring workspace"
        subtitle="Public health home"
        chipTone="amber"
        chipText="Regional surveillance"
        user={user}
        initials={initials}
      />

      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="tag amber">Public health focus</div>
            <h2>Track location risk, signal spread, and response pressure across monitored states.</h2>
            <p>
              This view is tailored for officers who need rapid regional understanding, not backend operations screens. It
              emphasizes trends, hotspots, and alert interpretation.
            </p>
            <div className="footer-note hero-note">
              The public health view should help teams answer three questions fast: where is risk rising, why is it rising,
              and which communities need attention first.
            </div>
            <div className="hero-actions">
              <NavLink className="btn primary" to="/analytics">
                Open analytics
              </NavLink>
              <NavLink className="btn secondary" to="/news">
                Review verified news
              </NavLink>
            </div>
          </div>

          <div className="hero-side">
            <MetricPanel value="9" label="Historical weeks loaded" tone="green" status="Growing evidence" />
            <MetricPanel value="3" label="High-priority hotspot states" tone="red" status="Escalate review" />
            <MetricPanel value="119" label="Training rows supporting risk model" tone="amber" status="Active baseline" />
          </div>
        </div>
      </section>

      <section className="grid-3">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Regional priorities</h3>
              <p className="muted">Keep the overview state-focused and surveillance-oriented.</p>
            </div>
          </div>
          <div className="feed">
            {data.priority_states.slice(0, 4).map((item) => (
              <InfoRow
                key={`priority-${item.state}-${item.disease}`}
                title={`${item.state} | ${item.disease}`}
                copy={`Risk: ${item.risk}. Action: ${item.action}.`}
              />
            ))}
          </div>
        </article>

        <article className="card map-card">
          <div className="card-header">
            <div>
              <h3>Hotspot interpretation</h3>
              <p className="muted">Designed for officers prioritizing where to look first.</p>
            </div>
            <div className="status-chip red">Hotspot watch</div>
          </div>
          <div className="feed">
            <InfoRow title="Ondo and Bauchi" copy="These states remain the clearest places to watch when signal pressure and clinic-reported symptoms align." />
            <InfoRow title="Edo and Ebonyi" copy="These stay important because even moderate signal changes can matter when historical burden is persistent." />
            <InfoRow title="Cross-source alignment" copy="Public health review should focus where weather, symptoms, and verified news agree." />
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>What this role should open next</h3>
              <p className="muted">Recommended movement through the app for public-health review.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Analytics" copy="Use model output, classified signals, and probability panels to inspect why risk is moving." />
            <InfoRow title="Disease Alerts" copy="Use this to compare multi-disease alert posture and response load." />
            <InfoRow title="News Feed and Weather Feed" copy="Use these for context and evidence, not just the final classification outcome." />
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Regional focus selector</h3>
              <p className="muted">Choose a state to read a cleaner public-health situation summary.</p>
            </div>
          </div>
          <FilterField
            label="Focus state"
            value={selectedState}
            onChange={setSelectedState}
            options={focusOptions}
          />
          {selectedPriorityState ? (
            <div className="footer-note">
              <strong>{selectedPriorityState.state}</strong>
              <div>Disease: {selectedPriorityState.disease}</div>
              <div>Alert: {selectedPriorityState.alert}</div>
              <div>Signals: {selectedPriorityState.signalCount || selectedPriorityState.signals}</div>
              <div>Recommended action: {selectedPriorityState.action}</div>
            </div>
          ) : (
            <div className="empty-state">No priority states are loaded yet.</div>
          )}
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Situation summary by location</h3>
              <p className="muted">A public-health-ready interpretation for the currently selected state.</p>
            </div>
          </div>
          {selectedPriorityState ? (
            <div className="feed">
              <InfoRow
                title={`${selectedPriorityState.state} risk posture`}
                copy={`${selectedPriorityState.alert} alert conditions are active for ${selectedPriorityState.disease}, with ${selectedPriorityState.signalCount || selectedPriorityState.signals} tracked supporting signals.`}
              />
              <InfoRow
                title="Why this state stands out"
                copy={`The current posture suggests cross-source agreement from surveillance evidence, so ${selectedPriorityState.state} should stay on the public-health watchlist.`}
              />
              <InfoRow
                title="Recommended response cue"
                copy={selectedPriorityState.action}
              />
            </div>
          ) : (
            <div className="empty-state">Select a state to view the public health summary.</div>
          )}
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Regional trend comparison</h3>
              <p className="muted">A compact comparison of the most important states currently under surveillance.</p>
            </div>
          </div>
          <div className="bars">
            {regionalTrend.map((item) => {
              const count = item.signalCount || item.signals || 0;
              return (
                <div className="bar-row" key={`regional-trend-${item.state}`}>
                  <span>{item.state}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(count / maxSignalCount) * 100}%` }}></div>
                  </div>
                  <strong>{count}</strong>
                </div>
              );
            })}
          </div>
          <div className="legend">
            <span className="legend-item"><span className="swatch brand"></span>Signal pressure by state</span>
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Public health export view</h3>
              <p className="muted">Generate a simple shareable situation brief for the currently selected location.</p>
            </div>
          </div>
          {selectedPriorityState ? (
            <>
              <div className="footer-note">
                <strong>{selectedPriorityState.state} situation brief</strong>
                <div className="tiny" style={{ whiteSpace: "pre-line", marginTop: "10px" }}>{situationBrief}</div>
              </div>
              <div className="form-actions">
                <button
                  className="btn primary"
                  type="button"
                  onClick={() => downloadTextFile(`clinicai_${selectedPriorityState.state.toLowerCase()}_brief.txt`, situationBrief)}
                >
                  Download brief
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">Choose a focus state to generate a situation brief.</div>
          )}
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Public health summary</h3>
              <p className="muted">This role should see the surveillance story, not the data-engineering machinery.</p>
            </div>
          </div>
          <div className="footer-note">
            ClinicAI Sentinel should help public-health officers monitor spread, interpret emerging patterns, and justify early
            response decisions with understandable evidence from multiple sources.
          </div>
        </article>

        <NotificationContactCard
          token={token}
          user={user}
          title="Public health notification contacts"
          description="Save the phone numbers and contact email that should receive public-health outbreak notifications."
        />
      </section>
    </>
  );
}

function AnalyticsPage({ initials, user, data, token }) {
  const [liveMetrics, setLiveMetrics] = useState({
    predictions: [],
    alerts: [],
    signals: []
  });
  const [liveError, setLiveError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadAnalyticsDetails() {
      if (!token) {
        return;
      }
      try {
        const [predictions, alerts, signals] = await Promise.all([
          fetchPredictions(token, { disease: "Lassa fever", limit: 12 }),
          fetchAlertsList(token, { disease: "Lassa fever", limit: 12 }),
          fetchSignals(token, { disease: "Lassa fever", limit: 18 })
        ]);
        if (!active) {
          return;
        }
        setLiveMetrics({
          predictions: Array.isArray(predictions) ? predictions : [],
          alerts: Array.isArray(alerts) ? alerts : [],
          signals: Array.isArray(signals) ? signals : []
        });
        setLiveError("");
      } catch (error) {
        if (active) {
          setLiveError(readableError(error));
        }
      }
    }
    loadAnalyticsDetails();
    return () => {
      active = false;
    };
  }, [token]);

  const recentPredictions = useMemo(() => (
    [...liveMetrics.predictions]
      .sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0))
      .slice(0, 6)
  ), [liveMetrics.predictions]);

  const alertSplit = useMemo(() => {
    const counts = { Red: 0, Amber: 0, Green: 0 };
    liveMetrics.alerts.forEach((item) => {
      const level = item.level || item.alert_level || item.classification;
      if (level && counts[level] !== undefined) {
        counts[level] += 1;
      }
    });
    const total = counts.Red + counts.Amber + counts.Green;
    const percent = (value) => (total ? Math.round((value / total) * 100) : 0);
    return {
      counts,
      total,
      red: percent(counts.Red),
      amber: percent(counts.Amber),
      green: percent(counts.Green)
    };
  }, [liveMetrics.alerts]);
  const donutStyle = {
    background: `conic-gradient(var(--danger) 0 ${alertSplit.red}%, var(--warning) ${alertSplit.red}% ${alertSplit.red + alertSplit.amber}%, var(--success) ${alertSplit.red + alertSplit.amber}% 100%)`
  };

  const regionalSignalPressure = useMemo(() => {
    const grouped = new Map();
    liveMetrics.signals.forEach((item) => {
      const key = item.location || "Unknown";
      const current = grouped.get(key) || { label: key, count: 0, confidenceTotal: 0 };
      current.count += 1;
      current.confidenceTotal += Number(item.confidence || 0);
      grouped.set(key, current);
    });
    const values = Array.from(grouped.values())
      .map((item) => ({
        label: item.label,
        count: item.count,
        averageConfidence: item.count ? Math.round((item.confidenceTotal / item.count) * 100) : 0
      }))
      .sort((left, right) => right.count - left.count)
      .slice(0, 5);
    const maxCount = values[0]?.count || 1;
    return values.map((item) => ({
      ...item,
      width: Math.max(18, Math.round((item.count / maxCount) * 100))
    }));
  }, [liveMetrics.signals]);

  const topPrediction = recentPredictions[0];
  const interpretationTitle = topPrediction
    ? `${topPrediction.location || "Priority state"} at ${Math.round(Number(topPrediction.risk_score || 0) * 100)}%`
    : "Live model interpretation will appear here";
  const interpretationCopy = topPrediction
    ? `The latest Lassa fever model output is ${topPrediction.risk_level || "under review"} for ${topPrediction.location || "the monitored location"}, supported by ${liveMetrics.signals.length} recent structured signal${liveMetrics.signals.length === 1 ? "" : "s"} and ${liveMetrics.alerts.length} active alert${liveMetrics.alerts.length === 1 ? "" : "s"}.`
    : "As live predictions arrive, this card will summarize the highest-risk location, current score, and why the model response posture changed.";
  const classifiedSignals = liveMetrics.signals.length
    ? liveMetrics.signals.slice(0, 6).map((row) => ({
        source: row.source_name || row.source || "Live signal",
        location: row.location || "Unknown",
        level: row.classification || "Amber",
        confidence: `${Math.round(Number(row.confidence || 0) * 100)}%`
      }))
    : data.classified_signals;

  return (
    <>
      <Topbar
        title="Prediction, classification, and decision-support intelligence"
        subtitle="Analytics page"
        chipTone="red"
        chipText="Lassa: elevated risk"
        user={user}
        initials={initials}
      />

      <section className="grid-3">
        {data.summary_metrics.map((item) => (
          <article className="card" key={item.label}>
            <div className="metric">
              <strong>{item.value}</strong>
              <span className="muted">{item.label}</span>
            </div>
          </article>
        ))}
      </section>

      <section className="analytics-grid">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Recent model output activity</h3>
              <p className="muted">Live backend predictions ranked by latest risk score and location.</p>
            </div>
            <div className="status-chip amber">
              {recentPredictions[0]?.created_at ? `Updated ${formatDateTime(recentPredictions[0].created_at)}` : "Waiting for live predictions"}
            </div>
          </div>
          {recentPredictions.length ? (
            <div className="bars">
              {recentPredictions.map((item) => {
                const score = Math.round(Number(item.risk_score || 0) * 100);
                return (
                  <div className="bar-row" key={`prediction-${item.id}`}>
                    <span>{item.location || "Unknown"}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${Math.max(score, 4)}%` }}></div>
                    </div>
                    <strong>{score}%</strong>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">Live predictions have not been generated yet.</div>
          )}
          <div className="legend">
            <span className="legend-item"><span className="swatch brand"></span>Latest risk score</span>
            <span className="legend-item"><span className="swatch accent"></span>{recentPredictions.length} live prediction{recentPredictions.length === 1 ? "" : "s"}</span>
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Live classification split</h3>
              <p className="muted">A backend-driven read of current red, amber, and green alert posture.</p>
            </div>
          </div>
          <div className="donut" style={donutStyle}>
            <div className="donut-center">
              <strong>{alertSplit.total || 0}</strong>
              <span>Classifications</span>
            </div>
          </div>
          <div className="legend">
            <span className="legend-item"><span className="swatch danger"></span>Red alert: {alertSplit.red}%</span>
            <span className="legend-item"><span className="swatch warning"></span>Amber alert: {alertSplit.amber}%</span>
            <span className="legend-item"><span className="swatch success"></span>Green alert: {alertSplit.green}%</span>
          </div>
          <div className="footer-note">
            {alertSplit.total ? `${alertSplit.total} live alert classifications are currently informing this split.` : "Generate live alerts to replace the placeholder split with active backend counts."}
          </div>
        </article>
      </section>

      <section className="analytics-grid">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Disease probability by model output</h3>
              <p className="muted">Use this panel to compare future disease classes beyond Lassa fever.</p>
            </div>
          </div>
          <div className="bars">
            {data.disease_probabilities.map((item) => (
              <div className="bar-row" key={item.label}>
                <span>{item.label}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${item.value}%` }}></div>
                </div>
                <strong>{item.value}%</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Regional signal pressure</h3>
              <p className="muted">Signal clustering by location based on live classified evidence.</p>
            </div>
            <div className={`status-chip ${topPrediction?.risk_level?.toLowerCase() === "low" ? "green" : topPrediction?.risk_level?.toLowerCase() === "medium" ? "amber" : "red"}`}>
              {topPrediction?.risk_level || "Watch"}
            </div>
          </div>
          {regionalSignalPressure.length ? (
            <div className="bars">
              {regionalSignalPressure.map((item) => (
                <div className="bar-row" key={`signal-pressure-${item.label}`}>
                  <span>{item.label}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${item.width}%` }}></div>
                  </div>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">Live signal clustering will appear here after ingestion and classification.</div>
          )}
          <div className="feed">
            <InfoRow title={interpretationTitle} copy={interpretationCopy} />
            <InfoRow title="Average signal confidence" copy={regionalSignalPressure.length ? `${regionalSignalPressure[0].label} currently leads this view with ${regionalSignalPressure[0].averageConfidence}% average confidence across its recent signal set.` : data.demo_scenario.copy} />
          </div>
        </article>
      </section>

      <section className="analytics-grid">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Top classified signals</h3>
              <p className="muted">Show analysts why the model arrived at its prediction.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Location</th>
                <th>Class</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {classifiedSignals.map((row) => (
                <tr key={`${row.source}-${row.location}`}>
                  <td>{row.source}</td>
                  <td>{row.location}</td>
                  <td>
                    <span className={`tag ${row.level.toLowerCase()}`}>{row.level}</span>
                  </td>
                  <td>{row.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="list-card">
          <div className="card-header">
            <div>
              <h3>Action layer recommendations</h3>
              <p className="muted">The part of the system that turns analytics into clinic decisions.</p>
            </div>
          </div>
          <div className="feed">
            {data.recommendations.map((item) => (
              <InfoRow key={item.title} title={item.title} copy={item.copy} />
            ))}
          </div>
        </article>
      </section>
      {liveError ? <div className="footer-note">{liveError}</div> : null}
    </>
  );
}

function AlertsPage({ initials, user, data }) {
  return (
    <>
      <Topbar
        title="Monitor all diseases in one response-focused view"
        subtitle="Disease alert board"
        chipTone="amber"
        chipText="6 diseases tracked"
        user={user}
        initials={initials}
      />

      <section className="alerts-grid">
        {data.diseases.map((card) => (
          <article className={`disease-card ${card.tone}`} key={card.name}>
            <div className="disease-top">
              <div>
                <div className={`tag ${card.tone}`}>{card.alert}</div>
                <h3>{card.name}</h3>
                <p className="muted">{card.copy}</p>
              </div>
              <div className={`status-chip ${card.tone}`}>{card.status}</div>
            </div>
            <div className="disease-stats">
              <StatBox value={card.probability} label="Outbreak probability" />
              <StatBox value={card.weekly_signals} label="Weekly signals" />
              <StatBox value={card.states} label={card.tone === "green" ? "Watch state" : `${card.tone === "red" ? "Red" : "Amber"} states`} />
            </div>
            <div className="priority-list">
              <div className="priority-item">
                <span>Primary states</span>
                <strong>{card.primary_states}</strong>
              </div>
              <div className="priority-item">
                <span>Response cue</span>
                <strong>{card.cue}</strong>
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Alert table</h3>
              <p className="muted">A compact list view for teams who prefer rows over cards.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Disease</th>
                <th>Alert level</th>
                <th>States</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.table.map((row) => (
                <tr key={row.disease}>
                  <td>{row.disease}</td>
                  <td>
                    <span className={`tag ${row.level.toLowerCase()}`}>{row.level}</span>
                  </td>
                  <td>{row.states}</td>
                  <td>{row.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="list-card">
          <div className="card-header">
            <div>
              <h3>Clinic decision playbook</h3>
              <p className="muted">Alert levels should always map to a simple operational response.</p>
            </div>
          </div>
          <div className="feed">
            {data.clinic_actions.map((item) => (
              <InfoRow key={item.title} title={item.title} copy={item.copy} />
            ))}
          </div>
        </article>
      </section>
    </>
  );
}

function RiskMapPage({ initials, user, data, alertsData }) {
  const hotspots = (data?.priority_states || []).slice(0, 8).map((item, index) => ({
    ...item,
    tone: item.alert?.toLowerCase?.() || "amber",
    position: stateMapPosition(item.state, index)
  }));

  const severeCount = hotspots.filter((item) => item.tone === "red").length;
  const mediumCount = hotspots.filter((item) => item.tone === "amber").length;
  const calmCount = Math.max((alertsData?.table?.length || hotspots.length) - severeCount - mediumCount, 0);

  return (
    <>
      <Topbar
        title="Risk map and hotspot intelligence"
        subtitle="Geospatial surveillance view"
        chipTone="red"
        chipText={`${severeCount} severe hotspots`}
        user={user}
        initials={initials}
      />

      <section className="grid-2">
        <article className="card map-page-card">
          <div className="card-header">
            <div>
              <h3>Nigeria hotspot map</h3>
              <p className="muted">A larger state-first view for understanding where outbreak pressure is clustering right now.</p>
            </div>
            <div className="legend">
              <span className="tag red">Red {severeCount}</span>
              <span className="tag amber">Amber {mediumCount}</span>
              <span className="tag green">Green {calmCount}</span>
            </div>
          </div>
          <div className="nigeria-map large">
            <div className="map-shape"></div>
            {hotspots.map((item) => (
              <div
                key={`hotspot-${item.state}-${item.disease}`}
                className={`map-pill hotspot-pill ${item.tone}`}
                style={{ top: item.position.top, left: item.position.left }}
              >
                <strong>{item.state}</strong>
                <span>{item.alert} | {item.signalCount} signals</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Hotspot interpretation</h3>
              <p className="muted">Designed to help teams answer where to act first and why.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Red states" copy="These are the most immediate operational priorities because alert pressure and signal volume are both elevated." />
            <InfoRow title="Amber states" copy="These need close review because they can move into red when news, symptoms, and weather align in the same week." />
            <InfoRow title="Map reading rule" copy="Treat clustered red-and-amber states as shared surveillance corridors rather than isolated events." />
          </div>
          <div className="footer-note">
            This page turns the surveillance story into a quick location picture for clinics, public-health officers, and judges.
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Priority hotspot table</h3>
              <p className="muted">Use this alongside the map when you need a fast ranked list.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>State</th>
                <th>Disease</th>
                <th>Alert</th>
                <th>Signals</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {hotspots.map((item) => (
                <tr key={`map-table-${item.state}-${item.disease}`}>
                  <td>{item.state}</td>
                  <td>{item.disease}</td>
                  <td><span className={`tag ${item.tone}`}>{item.alert}</span></td>
                  <td>{item.signalCount}</td>
                  <td>{item.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>What this adds to the demo</h3>
              <p className="muted">A stronger visual argument that the platform supports public-health decision making.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Spatial clarity" copy="Judges and response teams can now see that the system is not only analytical, but location-aware." />
            <InfoRow title="Outbreak storytelling" copy="The map makes it easier to explain why Ondo, Bauchi, Edo, and nearby states matter at different moments." />
            <InfoRow title="Role fit" copy="Clinic users get a simplified hotspot picture, while public-health users get a stronger regional monitoring view." />
          </div>
        </article>
      </section>
    </>
  );
}

function NewsPage({ initials, user, token }) {
  const [newsRecords, setNewsRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  async function loadNews() {
    setLoading(true);
    setError("");
    try {
      const records = await fetchNewsRecords(token, { disease: "Lassa fever", limit: 18 });
      setNewsRecords(records);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNews();
  }, [token]);

  async function handleFetchNow() {
    setRefreshing(true);
    setError("");
    try {
      await runTrustedNewsIngestion(token, {
        disease: "Lassa fever",
        max_items_per_source: 2
      });
      await loadNews();
    } catch (refreshError) {
      setError(refreshError.message);
    } finally {
      setRefreshing(false);
    }
  }

  const latest = newsRecords[0] || null;

  return (
    <>
      <Topbar
        title="Verified news intelligence feed"
        subtitle="Live news page"
        chipTone="amber"
        chipText={`${newsRecords.length} live articles`}
        user={user}
        initials={initials}
      />

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>News surveillance overview</h3>
              <p className="muted">Trusted outbreak signals from verified Nigerian and health-source reporting.</p>
            </div>
            <div className="status-chip amber">{loading ? "Loading feed" : "Live feed"}</div>
          </div>
          {latest ? (
            <div className="hero-story">
              <div className={`story-media ${storyTone(latest.location)}`}>
                <div className="story-media-badge">{latest.source_name}</div>
                <strong>{latest.location}</strong>
                <span>{formatDateTime(latest.published_at)}</span>
              </div>
              <div className="story-copy">
                <div className="story-meta">
                  <span className="status-chip green">{latest.verification_status}</span>
                  <span className="tiny muted">{timeAgo(latest.published_at)}</span>
                </div>
                <h3>{latest.title}</h3>
                <p>{truncateText(latest.content, 260)}</p>
              </div>
            </div>
          ) : (
            <div className="empty-state">No verified news records have been stored yet.</div>
          )}
          <div className="form-actions">
            <button className="btn secondary" onClick={loadNews} disabled={loading}>
              Refresh feed
            </button>
            {getRole(user) === "admin" ? (
              <button className="btn primary" onClick={handleFetchNow} disabled={refreshing}>
                {refreshing ? "Fetching..." : "Fetch trusted news now"}
              </button>
            ) : null}
          </div>
          {error ? <div className="auth-error">{error}</div> : null}
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>What this page shows</h3>
              <p className="muted">A clearer newsroom view for clinicians and public-health teams.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Image-style visual card" copy="Each article is shown with a bold visual panel so the feed is easier to scan quickly." />
            <InfoRow title="Article date and source" copy="Every card includes the publication time, source name, and verification status." />
            <InfoRow title="Operational article preview" copy="The article excerpt lets teams understand the signal without opening Data Ops." />
          </div>
        </article>
      </section>

      <section className="story-grid">
        {newsRecords.map((item) => (
          <article className="story-card" key={`news-page-${item.id}`}>
            <div className={`story-media ${storyTone(item.location)}`}>
              <div className="story-media-badge">{item.source_name}</div>
              <strong>{item.location}</strong>
              <span>{item.disease}</span>
            </div>
            <div className="story-copy">
              <div className="story-meta">
                <span className={`status-chip ${item.verification_status === "Verified" ? "green" : "amber"}`}>{item.verification_status}</span>
                <span className="tiny muted">{formatDateTime(item.published_at)}</span>
              </div>
              <h3>{item.title}</h3>
              <p>{truncateText(item.content, 220)}</p>
            </div>
          </article>
        ))}
      </section>
    </>
  );
}

function WeatherPage({ initials, user, token }) {
  const [weatherRecords, setWeatherRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  async function loadWeather() {
    setLoading(true);
    setError("");
    try {
      const records = await fetchWeatherRecords(token, { disease: "Lassa fever", limit: 18 });
      setWeatherRecords(records);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWeather();
  }, [token]);

  async function handleFetchNow() {
    setRefreshing(true);
    setError("");
    try {
      await runLiveWeatherIngestion(token, {
        disease: "Lassa fever",
        locations: ["Ondo", "Edo", "Bauchi", "Taraba", "Plateau"]
      });
      await loadWeather();
    } catch (refreshError) {
      setError(refreshError.message);
    } finally {
      setRefreshing(false);
    }
  }

  const latest = weatherRecords[0] || null;

  return (
    <>
      <Topbar
        title="Live weather and environmental feed"
        subtitle="Weather page"
        chipTone="green"
        chipText={`${weatherRecords.length} weather snapshots`}
        user={user}
        initials={initials}
      />

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Weather risk overview</h3>
              <p className="muted">Real-time environmental conditions that can influence Lassa-fever risk patterns.</p>
            </div>
            <div className="status-chip green">{loading ? "Loading weather" : "Live weather"}</div>
          </div>
          {latest ? (
            <div className="hero-story">
              <div className={`weather-visual ${weatherTone(latest.dry_season_index)}`}>
                <div className="story-media-badge">{latest.source_name}</div>
                <strong>{latest.location}</strong>
                <span>{formatDateTime(latest.recorded_at)}</span>
              </div>
              <div className="story-copy">
                <div className="weather-chip-row">
                  <div className="weather-chip">{latest.temperature_c}C</div>
                  <div className="weather-chip">{latest.rainfall_mm} mm rain</div>
                  <div className="weather-chip">{latest.humidity_pct}% humidity</div>
                </div>
                <h3>{latest.location} environmental snapshot</h3>
                <p>
                  Dry season index at {latest.dry_season_index}. This record was captured {timeAgo(latest.recorded_at)} and is ready for
                  downstream surveillance analysis.
                </p>
              </div>
            </div>
          ) : (
            <div className="empty-state">No weather records have been stored yet.</div>
          )}
          <div className="form-actions">
            <button className="btn secondary" onClick={loadWeather} disabled={loading}>
              Refresh feed
            </button>
            {getRole(user) === "admin" ? (
              <button className="btn primary" onClick={handleFetchNow} disabled={refreshing}>
                {refreshing ? "Fetching..." : "Fetch live weather now"}
              </button>
            ) : null}
          </div>
          {error ? <div className="auth-error">{error}</div> : null}
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>What this page shows</h3>
              <p className="muted">A cleaner weather screen for teams that do not need backend operations details.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Timestamped weather cards" copy="Each location record shows the exact recorded time, not just a summary metric." />
            <InfoRow title="Readable environmental context" copy="Temperature, rainfall, humidity, and dry-season pressure are visible at a glance." />
            <InfoRow title="Prediction-ready feed" copy="These are the same weather records the backend uses for risk analysis and prediction runs." />
          </div>
        </article>
      </section>

      <section className="story-grid">
        {weatherRecords.map((item) => (
          <article className="story-card" key={`weather-page-${item.id}`}>
            <div className={`weather-visual ${weatherTone(item.dry_season_index)}`}>
              <div className="story-media-badge">{item.source_name}</div>
              <strong>{item.location}</strong>
              <span>{item.disease}</span>
            </div>
            <div className="story-copy">
              <div className="story-meta">
                <span className="status-chip amber">Recorded</span>
                <span className="tiny muted">{formatDateTime(item.recorded_at)}</span>
              </div>
              <h3>{item.location} weather record</h3>
              <div className="weather-chip-row">
                <div className="weather-chip">{item.temperature_c}C</div>
                <div className="weather-chip">{item.rainfall_mm} mm</div>
                <div className="weather-chip">{item.humidity_pct}%</div>
                <div className="weather-chip">Dry {item.dry_season_index}</div>
              </div>
              <p>{buildWeatherNarrative(item)}</p>
            </div>
          </article>
        ))}
      </section>
    </>
  );
}

function RecommendationsPage({ initials, user, token }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadRecommendations() {
      try {
        const result = await fetchRecommendations(token, { limit: 24 });
        if (cancelled) {
          return;
        }
        setRecommendations(result);
        setError("");
      } catch (fetchError) {
        if (!cancelled) {
          setError(readableError(fetchError));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadRecommendations();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <>
      <Topbar
        title="Operational recommendations for the current surveillance picture"
        subtitle="Recommendations"
        chipTone="green"
        chipText={loading ? "Loading" : `${recommendations.length} active items`}
        user={user}
        initials={initials}
      />

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>How to use this page</h3>
              <p className="muted">Every role can use the recommendation layer to understand the next best action quickly.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Clinic users" copy="Use these items as the immediate action list after symptom screening or when an alert is raised." />
            <InfoRow title="Public health officers" copy="Use the items to coordinate escalation, screening guidance, and regional communication." />
            <InfoRow title="Admin / Data Ops" copy="Use the page to confirm that the action layer being generated by the system is practical and clear." />
          </div>
          <div className="footer-note">
            ClinicAI Sentinel should not stop at a risk label. This page keeps the response actions visible to every user role.
          </div>
        </article>

        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Priority actions</h3>
              <p className="muted">The highest-signal recommendations currently generated by the backend.</p>
            </div>
          </div>
          {error ? <p className="auth-error">{error}</p> : null}
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Location</th>
                <th>Priority</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recommendations.map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td>{item.location}</td>
                  <td><span className={`tag ${item.priority === "High" ? "red" : item.priority === "Medium" ? "amber" : "green"}`}>{item.priority}</span></td>
                  <td>{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="grid-2">
        <article className="list-card">
          <div className="card-header">
            <div>
              <h3>Recommendation details</h3>
              <p className="muted">Use this list when teams need the full wording rather than a compact table.</p>
            </div>
          </div>
          <div className="feed">
            {recommendations.map((item) => (
              <div className="insight-item" key={`recommendation-copy-${item.id}`}>
                <div>
                  <div className="signal-title">{item.title}</div>
                  <div className="muted">{item.description}</div>
                  <div className="tiny muted">{item.location} | {item.category}</div>
                </div>
                <span className={`tag ${item.priority === "High" ? "red" : item.priority === "Medium" ? "amber" : "green"}`}>{item.priority}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Recommended workflow</h3>
              <p className="muted">This is the cleanest path for clinic users to contribute useful frontline data.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="1. Submit symptoms" copy="Open Clinic Intake and record fever, headache, vomiting, weakness, bleeding, and contact history." />
            <InfoRow title="2. Let the system learn" copy="Those symptom entries land in the structured symptom-report dataset for surveillance analysis." />
            <InfoRow title="3. Review response actions" copy="Return here to see the current action layer the system recommends for healthcare teams." />
          </div>
        </article>
      </section>
    </>
  );
}

function ClinicIntakePage({ initials, user, token }) {
  const [form, setForm] = useState({
    facility_name: user?.name ? `${user.name} facility` : "ClinicAI Sentinel Clinic",
    location: "Ondo",
    disease: "Lassa fever",
    report_date: new Date().toISOString().slice(0, 16),
    fever_cases: "0",
    headache_cases: "0",
    vomiting_cases: "0",
    weakness_cases: "0",
    bleeding_cases: "0",
    contact_history_cases: "0",
    suspected_cases: "0",
    notes: "",
    reported_by: user?.name || "Clinic user"
  });
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [pipelineResult, setPipelineResult] = useState(null);
  const [editingReportId, setEditingReportId] = useState(null);
  const [trendFrom, setTrendFrom] = useState("");
  const [trendTo, setTrendTo] = useState("");
  const myRecords = records.filter((item) => (item.reported_by || "").toLowerCase() === (user?.name || "").toLowerCase());
  const mySummary = myRecords.reduce(
    (summary, item) => ({
      reports: summary.reports + 1,
      fever: summary.fever + item.fever_cases,
      bleeding: summary.bleeding + item.bleeding_cases,
      suspected: summary.suspected + item.suspected_cases
    }),
    { reports: 0, fever: 0, bleeding: 0, suspected: 0 }
  );
  const trendPoints = [...myRecords]
    .sort((left, right) => new Date(left.report_date).getTime() - new Date(right.report_date).getTime())
    .slice(-6);
  const filteredTrendPoints = trendPoints.filter((item) => {
    const itemDate = new Date(item.report_date).getTime();
    const fromDate = trendFrom ? new Date(trendFrom).getTime() : null;
    const toDate = trendTo ? new Date(trendTo).getTime() : null;
    if (fromDate && itemDate < fromDate) {
      return false;
    }
    if (toDate && itemDate > toDate) {
      return false;
    }
    return true;
  });
  const maxTrendValue = Math.max(
    1,
    ...filteredTrendPoints.flatMap((item) => [item.fever_cases, item.bleeding_cases, item.suspected_cases])
  );
  const chartWidth = 420;
  const chartHeight = 180;
  const chartPadding = 20;

  function buildTrendPolyline(metric) {
    if (!filteredTrendPoints.length) {
      return "";
    }
    return filteredTrendPoints
      .map((item, index) => {
        const x = chartPadding + (filteredTrendPoints.length === 1 ? 0 : (index * (chartWidth - chartPadding * 2)) / (filteredTrendPoints.length - 1));
        const y =
          chartHeight -
          chartPadding -
          ((item[metric] || 0) / maxTrendValue) * (chartHeight - chartPadding * 2);
        return `${x},${y}`;
      })
      .join(" ");
  }

  async function loadRecords() {
    try {
      const result = await fetchSymptomReports(token, { disease: "Lassa fever", limit: 10 });
      setRecords(result);
      setError("");
    } catch (fetchError) {
      setError(readableError(fetchError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRecords();
  }, [token]);

  function loadRecordIntoForm(record) {
    setEditingReportId(record.id);
    setForm({
      facility_name: record.facility_name,
      location: record.location,
      disease: record.disease,
      report_date: new Date(record.report_date).toISOString().slice(0, 16),
      fever_cases: String(record.fever_cases),
      headache_cases: String(record.headache_cases),
      vomiting_cases: String(record.vomiting_cases),
      weakness_cases: String(record.weakness_cases),
      bleeding_cases: String(record.bleeding_cases),
      contact_history_cases: String(record.contact_history_cases),
      suspected_cases: String(record.suspected_cases),
      notes: record.notes || "",
      reported_by: record.reported_by
    });
    setStatus("Editing existing symptom report.");
    setError("");
  }

  function resetFormForNewEntry() {
    setEditingReportId(null);
    setForm((current) => ({
      ...current,
      report_date: new Date().toISOString().slice(0, 16),
      fever_cases: "0",
      headache_cases: "0",
      vomiting_cases: "0",
      weakness_cases: "0",
      bleeding_cases: "0",
      contact_history_cases: "0",
      suspected_cases: "0",
      notes: "",
      reported_by: user?.name || "Clinic user"
    }));
  }

  async function removeReport(report) {
    const shouldDelete = window.confirm(`Delete the symptom report from ${formatDateTime(report.report_date)} for ${report.location}?`);
    if (!shouldDelete) {
      return;
    }

    setSaving(true);
    setStatus("");
    setError("");
    try {
      await deleteSymptomReport(token, report.id);
      if (editingReportId === report.id) {
        resetFormForNewEntry();
      }
      setPipelineResult(null);
      setStatus("Symptom report deleted successfully.");
      await loadRecords();
    } catch (deleteError) {
      setError(readableError(deleteError));
    } finally {
      setSaving(false);
    }
  }

  async function submitIntake() {
    setSaving(true);
    setStatus("");
    setError("");
    try {
      const payload = {
        ...form,
        fever_cases: Number(form.fever_cases),
        headache_cases: Number(form.headache_cases),
        vomiting_cases: Number(form.vomiting_cases),
        weakness_cases: Number(form.weakness_cases),
        bleeding_cases: Number(form.bleeding_cases),
        contact_history_cases: Number(form.contact_history_cases),
        suspected_cases: Number(form.suspected_cases)
      };
      if (editingReportId) {
        await updateSymptomReport(token, editingReportId, payload);
      } else {
        await createSymptomReport(token, payload);
      }
      const analysisResult = await runPipelineAnalysis(token, {
        disease: form.disease,
        location: form.location,
        analyst: user?.name || "Clinic user"
      });
      setPipelineResult(analysisResult);
      setStatus(
        `${editingReportId ? "Symptom report updated successfully." : "Symptom report submitted successfully."} ${analysisResult.prediction.risk_level} risk detected for ${analysisResult.prediction.location}.`
      );
      resetFormForNewEntry();
      await loadRecords();
    } catch (submitError) {
      setError(readableError(submitError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Topbar
        title="Capture symptom data from clinics and communities"
        subtitle="Clinic intake"
        chipTone="red"
        chipText={saving ? "Submitting" : "Data collection"}
        user={user}
        initials={initials}
      />

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>{editingReportId ? "Edit symptom report" : "Symptom intake form"}</h3>
              <p className="muted">This is the clinic workflow for turning frontline symptoms into data the system can use.</p>
            </div>
          </div>
          <div className="form-grid form-grid-2">
            <FilterInput label="Facility / clinic" value={form.facility_name} onChange={(value) => setForm((current) => ({ ...current, facility_name: value }))} placeholder="Clinic name" />
            <FilterInput label="Location" value={form.location} onChange={(value) => setForm((current) => ({ ...current, location: value }))} placeholder="State or LGA" />
            <FilterInput label="Disease" value={form.disease} onChange={(value) => setForm((current) => ({ ...current, disease: value }))} placeholder="Lassa fever" />
            <FilterInput label="Report date" type="datetime-local" value={form.report_date} onChange={(value) => setForm((current) => ({ ...current, report_date: value }))} placeholder="" />
            <FilterInput label="Fever cases" type="number" value={form.fever_cases} onChange={(value) => setForm((current) => ({ ...current, fever_cases: value }))} placeholder="0" />
            <FilterInput label="Headache cases" type="number" value={form.headache_cases} onChange={(value) => setForm((current) => ({ ...current, headache_cases: value }))} placeholder="0" />
            <FilterInput label="Vomiting cases" type="number" value={form.vomiting_cases} onChange={(value) => setForm((current) => ({ ...current, vomiting_cases: value }))} placeholder="0" />
            <FilterInput label="Weakness cases" type="number" value={form.weakness_cases} onChange={(value) => setForm((current) => ({ ...current, weakness_cases: value }))} placeholder="0" />
            <FilterInput label="Bleeding cases" type="number" value={form.bleeding_cases} onChange={(value) => setForm((current) => ({ ...current, bleeding_cases: value }))} placeholder="0" />
            <FilterInput label="Contact history cases" type="number" value={form.contact_history_cases} onChange={(value) => setForm((current) => ({ ...current, contact_history_cases: value }))} placeholder="0" />
            <FilterInput label="Suspected cases" type="number" value={form.suspected_cases} onChange={(value) => setForm((current) => ({ ...current, suspected_cases: value }))} placeholder="0" />
            <FilterInput label="Reported by" value={form.reported_by} onChange={(value) => setForm((current) => ({ ...current, reported_by: value }))} placeholder="Reporter name" />
          </div>
          <label className="filter-field">
            <span className="tiny muted">Notes</span>
            <textarea
              value={form.notes}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
              placeholder="Record anything important about rodent exposure, unusual clustering, or community context."
            />
          </label>
          <div className="form-actions">
            <button className="btn primary" type="button" disabled={saving} onClick={submitIntake}>
              {saving ? "Submitting..." : editingReportId ? "Update symptom report" : "Submit symptom report"}
            </button>
            {editingReportId ? (
              <button className="btn secondary" type="button" disabled={saving} onClick={resetFormForNewEntry}>
                Cancel edit
              </button>
            ) : null}
          </div>
          {status ? <p className="success-copy">{status}</p> : null}
          {error ? <p className="auth-error">{error}</p> : null}
          <div className="footer-note">
            These symptom entries become structured surveillance records for later analysis, historical backfill, and model improvement.
          </div>
          {pipelineResult ? (
            <div className="footer-note">
              <strong>Latest clinic analysis</strong>
              <div>{pipelineResult.summary}</div>
              <div className="tiny">
                Prediction: {pipelineResult.prediction.risk_level} ({Math.round(pipelineResult.prediction.risk_score * 100)}%) | Alert: {pipelineResult.alert.level}
              </div>
              <div className="tiny">
                Next actions: {pipelineResult.recommendations.map((item) => item.title).join(" | ")}
              </div>
            </div>
          ) : null}
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Why this matters</h3>
              <p className="muted">The clinic role should contribute data, not just view dashboards.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Frontline data capture" copy="This page records the symptom pressure healthcare workers are actually seeing on the ground." />
            <InfoRow title="Model input" copy="Fever, vomiting, weakness, bleeding, contact history, and suspected case counts feed the surveillance evidence base." />
            <InfoRow title="Better recommendations" copy="As more symptom reports come in, the action layer becomes more grounded in clinical reality." />
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Clinic reporting summary</h3>
              <p className="muted">A fast snapshot of what this clinic user has contributed so far.</p>
            </div>
          </div>
          <div className="disease-stats">
            <StatBox value={mySummary.reports} label="Reports submitted" />
            <StatBox value={mySummary.fever} label="Fever cases logged" />
            <StatBox value={mySummary.bleeding} label="Bleeding cases logged" />
            <StatBox value={mySummary.suspected} label="Suspected cases logged" />
          </div>
          <div className="feed">
            <InfoRow title="Clinic value" copy="This summary helps healthcare workers confirm that the system is learning from their repeated submissions over time." />
            <InfoRow title="Operational reading" copy="Watch the fever, bleeding, and suspected-case totals closely because they are the strongest frontline signals in this intake flow." />
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Latest clinic impact</h3>
              <p className="muted">Shows the most recent model and alert output generated from clinic-side reporting.</p>
            </div>
          </div>
          {pipelineResult ? (
            <>
              <div className="disease-stats">
                <StatBox value={pipelineResult.prediction.risk_level} label="Predicted risk" />
                <StatBox value={`${Math.round(pipelineResult.prediction.risk_score * 100)}%`} label="Risk score" />
                <StatBox value={pipelineResult.alert.level} label="Alert level" />
                <StatBox value={pipelineResult.recommendations.length} label="Actions generated" />
              </div>
              <div className="footer-note">
                {pipelineResult.summary}
              </div>
            </>
          ) : (
            <div className="footer-note">
              Submit a clinic symptom report to generate a fresh risk assessment, alert level, and action set from the current data.
            </div>
          )}
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Recent clinic symptom submissions</h3>
              <p className="muted">The latest structured symptom reports currently saved to the backend.</p>
            </div>
            <div className="status-chip green">{loading ? "Loading" : `${records.length} records`}</div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Facility</th>
                <th>Location</th>
                <th>Fever</th>
                <th>Bleeding</th>
                <th>Suspected</th>
              </tr>
            </thead>
            <tbody>
              {records.map((item) => (
                <tr key={item.id}>
                  <td>{item.facility_name}</td>
                  <td>{item.location}</td>
                  <td>{item.fever_cases}</td>
                  <td>{item.bleeding_cases}</td>
                  <td>{item.suspected_cases}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="list-card">
          <div className="card-header">
            <div>
              <h3>What happens after submission</h3>
              <p className="muted">The ClinicAI Sentinel flow after a symptom report is saved.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Stored in backend" copy="The symptom report becomes part of the structured surveillance dataset immediately." />
            <InfoRow title="Combined with weather and news" copy="The system can combine clinic symptoms with weather risk and verified news signals." />
            <InfoRow title="Used for prediction and action" copy="Those combined signals can feed prediction, alert generation, and the recommendation layer." />
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>My submitted reports</h3>
              <p className="muted">A clinic-focused history of the reports submitted by your current signed-in role.</p>
            </div>
            <div className="status-chip amber">{myRecords.length} mine</div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Location</th>
                <th>Fever</th>
                <th>Bleeding</th>
                <th>Reported by</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {myRecords.map((item) => (
                <tr key={`my-report-${item.id}`}>
                  <td>{formatDateTime(item.report_date)}</td>
                  <td>{item.location}</td>
                  <td>{item.fever_cases}</td>
                  <td>{item.bleeding_cases}</td>
                  <td>{item.reported_by}</td>
                  <td>
                    <div className="form-actions">
                      <button className="btn secondary" type="button" onClick={() => loadRecordIntoForm(item)}>
                        Edit
                      </button>
                      <button className="btn secondary" type="button" onClick={() => removeReport(item)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Your intake summary</h3>
              <p className="muted">A quick readout of how this clinic user is contributing data into the system.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Reports submitted" copy={`${myRecords.length} recent symptom report${myRecords.length === 1 ? "" : "s"} are currently linked to ${user?.name || "this clinic user"}.`} />
            <InfoRow title="Why this matters" copy="This gives clinic users feedback that their data is not disappearing after submission and is part of the surveillance evidence chain." />
            <InfoRow title="Best next habit" copy="Keep submitting new symptom counts as cases change so the model and recommendations reflect what the clinic is actually seeing." />
          </div>
          <div className="footer-note">
            A strong clinic workflow should always answer two questions clearly: did my data save, and can I see my reporting history?
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Clinic symptom trend</h3>
              <p className="muted">A simple over-time view of what this clinic user has been reporting.</p>
            </div>
          </div>
          <div className="form-grid form-grid-2">
            <FilterInput label="Trend from" type="datetime-local" value={trendFrom} onChange={setTrendFrom} placeholder="" />
            <FilterInput label="Trend to" type="datetime-local" value={trendTo} onChange={setTrendTo} placeholder="" />
          </div>
          {filteredTrendPoints.length ? (
            <div className="footer-note">
              <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="trend-chart" role="img" aria-label="Clinic symptom trend chart">
                <line x1={chartPadding} y1={chartHeight - chartPadding} x2={chartWidth - chartPadding} y2={chartHeight - chartPadding} stroke="rgba(92,74,39,0.25)" strokeWidth="2" />
                <line x1={chartPadding} y1={chartPadding} x2={chartPadding} y2={chartHeight - chartPadding} stroke="rgba(92,74,39,0.2)" strokeWidth="2" />
                <polyline fill="none" stroke="#c95b2f" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={buildTrendPolyline("fever_cases")} />
                <polyline fill="none" stroke="#b21f3a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={buildTrendPolyline("bleeding_cases")} />
                <polyline fill="none" stroke="#0d7a5f" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={buildTrendPolyline("suspected_cases")} />
              </svg>
              <div className="trend-legend">
                <span><span className="trend-dot fever"></span> Fever</span>
                <span><span className="trend-dot bleeding"></span> Bleeding</span>
                <span><span className="trend-dot suspected"></span> Suspected</span>
              </div>
            </div>
          ) : (
            <div className="empty-state">No clinic reports match the current date filter yet.</div>
          )}
          <div className="feed">
            {filteredTrendPoints.length ? filteredTrendPoints.map((item) => (
              <div className="insight-item" key={`trend-${item.id}`}>
                <div>
                  <div className="signal-title">{formatDateTime(item.report_date)}</div>
                  <div className="muted">
                    Fever {item.fever_cases} | Bleeding {item.bleeding_cases} | Suspected {item.suspected_cases}
                  </div>
                </div>
                <span className={`tag ${item.bleeding_cases > 0 || item.suspected_cases > 0 ? "red" : item.fever_cases > 0 ? "amber" : "green"}`}>
                  {item.bleeding_cases > 0 || item.suspected_cases > 0 ? "Escalate" : item.fever_cases > 0 ? "Watch" : "Stable"}
                </span>
              </div>
            )) : null}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Trend interpretation</h3>
              <p className="muted">How clinic teams should read the submission pattern they are building.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Rising fever counts" copy="Repeated increases in fever counts should trigger stronger screening and a closer look at contact history." />
            <InfoRow title="Bleeding or suspected-case jumps" copy="These are the strongest clinic-side signs that the response posture should shift from routine review to escalation." />
            <InfoRow title="Keep reporting consistently" copy="Trend value comes from continuity. Even small daily updates help the platform see change earlier." />
          </div>
        </article>
      </section>
    </>
  );
}

function DataOpsPage({ initials, user, token }) {
  const [filters, setFilters] = useState({
    disease: "Lassa fever",
    location: "",
    classification: "",
    riskLevel: "",
    priority: "",
    severity: ""
  });
  const [opsData, setOpsData] = useState({
    signals: [],
    predictions: [],
    alerts: [],
    recommendations: [],
    clinicReports: [],
    symptomReports: [],
    weatherRecords: [],
    newsRecords: [],
    notifications: [],
    modelStatus: null,
    datasetStatus: null,
    historicalReports: [],
    trainingHistory: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pipelineResult, setPipelineResult] = useState(null);
  const [newsAnalysis, setNewsAnalysis] = useState(null);
  const [ingestionResult, setIngestionResult] = useState(null);
  const [reportResult, setReportResult] = useState(null);
  const [emailDispatchResult, setEmailDispatchResult] = useState(null);
  const [smsDispatchResult, setSmsDispatchResult] = useState(null);
  const [whatsAppDispatchResult, setWhatsAppDispatchResult] = useState(null);
  const [submitting, setSubmitting] = useState("");
  const [forms, setForms] = useState({
    signal: {
      title: "",
      disease: "Lassa fever",
      location: "Ondo",
      source_type: "News crawl",
      source_name: "Manual analyst entry",
      classification: "Amber",
      confidence: "0.74",
      risk_factor: "MEDIUM",
      summary: ""
    },
    symptom: {
      facility_name: "ClinicAI Demo Facility",
      location: "Ondo",
      disease: "Lassa fever",
      report_date: new Date().toISOString().slice(0, 16),
      fever_cases: "6",
      headache_cases: "4",
      vomiting_cases: "2",
      weakness_cases: "3",
      bleeding_cases: "1",
      contact_history_cases: "2",
      suspected_cases: "3",
      notes: "",
      reported_by: user?.name || "Demo Analyst"
    },
    weather: {
      location: "Ondo",
      disease: "Lassa fever",
      source_name: "Manual weather entry",
      temperature_c: "33",
      rainfall_mm: "14",
      humidity_pct: "52",
      dry_season_index: "0.78",
      recorded_at: new Date().toISOString().slice(0, 16)
    },
    news: {
      title: "",
      location: "Ondo",
      disease: "Lassa fever",
      source_name: "Verified news desk",
      verification_status: "Verified",
      content: "",
      published_at: new Date().toISOString().slice(0, 16)
    },
    ingestion: {
      disease: "Lassa fever",
      max_items_per_source: "2",
      weather_locations: "Ondo,Edo,Bauchi,Taraba,Plateau"
    },
    pipeline: {
      disease: "Lassa fever",
      location: "Ondo",
      analyst: user?.name || "Demo Analyst"
    },
    report: {
      disease: "Lassa fever",
      analyst: user?.name || "Demo Analyst"
    },
    notification: {
      disease: "Lassa fever",
      audience: "Public health",
      recipient_email: "",
      recipient_sms: "",
      recipient_whatsapp: "",
      channel: "Dashboard",
      location: "Ondo",
      priority: "High",
      status: "Queued",
      title: "Red alert review for Ondo",
      message: "ClinicAI Sentinel recommends rapid review of high-risk Lassa fever signals in Ondo.",
      recipient: ""
    }
  });

  async function loadOps() {
    setLoading(true);
    try {
      const [
        signals,
        predictions,
        alerts,
        recommendations,
        clinicReports,
        symptomReports,
        weatherRecords,
        newsRecords,
        notifications,
        modelStatus,
        datasetStatus,
        historicalReports,
        trainingHistory
      ] = await Promise.all([
        fetchSignals(token, {
          disease: filters.disease,
          location: filters.location,
          classification: filters.classification,
          min_confidence: 0.6
        }),
        fetchPredictions(token, {
          disease: filters.disease,
          location: filters.location,
          risk_level: filters.riskLevel
        }),
        fetchAlertsList(token, {
          disease: filters.disease,
          location: filters.location
        }),
        fetchRecommendations(token, {
          priority: filters.priority,
          location: filters.location
        }),
        fetchClinicReports(token, {
          disease: filters.disease,
          location: filters.location,
          severity: filters.severity
        }),
        fetchSymptomReports(token, {
          disease: filters.disease,
          location: filters.location
        }),
        fetchWeatherRecords(token, {
          disease: filters.disease,
          location: filters.location
        }),
        fetchNewsRecords(token, {
          disease: filters.disease,
          location: filters.location
        }),
        fetchNotifications(token, {
          disease: filters.disease,
          location: filters.location
        }),
        fetchModelStatus(token),
        fetchDatasetStatus(token, filters.disease || "Lassa fever"),
        fetchHistoricalReports(token, filters.disease || "Lassa fever"),
        fetchModelHistory(token, filters.disease || "Lassa fever")
      ]);

      setOpsData({
        signals,
        predictions,
        alerts,
        recommendations,
        clinicReports,
        symptomReports,
        weatherRecords,
        newsRecords,
        notifications,
        modelStatus,
        datasetStatus,
        historicalReports,
        trainingHistory
      });
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOps();
  }, [filters, token]);

  async function submitForm(kind, runner) {
    setSubmitting(kind);
    setSuccess("");
    setError("");
    try {
      await runner();
      setSuccess(`${kind} submitted successfully.`);
      await loadOps();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function analyzeNewsArticle() {
    setSubmitting("News analysis");
    setSuccess("");
    setError("");
    try {
      const result = await analyzeNewsRecord(token, {
        ...forms.news
      });
      setNewsAnalysis(result);
      setForms((current) => ({
        ...current,
        signal: {
          ...current.signal,
          title: result.signal_title,
          disease: result.disease,
          location: result.location,
          source_type: "NLP extraction",
          source_name: current.news.source_name,
          classification: result.classification,
          confidence: result.confidence.toFixed(2),
          risk_factor: result.risk_factor,
          summary: result.summary
        },
        pipeline: {
          ...current.pipeline,
          disease: result.disease,
          location: result.location
        }
      }));
      setSuccess("News analysis completed. Signal form was updated from the NLP result.");
    } catch (analysisError) {
      setError(analysisError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runNewsIngestion() {
    setSubmitting("Trusted news ingestion");
    setSuccess("");
    setError("");
    try {
      const result = await runTrustedNewsIngestion(token, {
        disease: forms.ingestion.disease,
        max_items_per_source: Number(forms.ingestion.max_items_per_source),
        auto_create_signals: true
      });
      setIngestionResult(result);
      setSuccess(`Trusted news ingestion completed. ${result.records_created} records and ${result.signals_created || 0} signals created.`);
      await loadOps();
    } catch (ingestionError) {
      setError(ingestionError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runWeatherIngestion() {
    setSubmitting("Weather ingestion");
    setSuccess("");
    setError("");
    try {
      const result = await runLiveWeatherIngestion(token, {
        disease: forms.ingestion.disease,
        locations: forms.ingestion.weather_locations
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      });
      setIngestionResult(result);
      setSuccess(`Live weather ingestion completed. ${result.records_created} weather records created.`);
      await loadOps();
    } catch (ingestionError) {
      setError(ingestionError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runDailyReportExport() {
    setSubmitting("Daily report");
    setSuccess("");
    setError("");
    try {
      const result = await generateDailyReport(token, forms.report);
      setReportResult(result);
      setSuccess(`Daily report generated for ${result.disease}.`);
    } catch (reportError) {
      setError(reportError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runNotificationGeneration() {
    setSubmitting("Notification generation");
    setSuccess("");
    setError("");
    try {
      const result = await generateNotifications(token, {
        disease: forms.notification.disease,
        audience: forms.notification.audience,
        recipient_email: forms.notification.recipient_email || null,
        recipient_sms: forms.notification.recipient_sms || null,
        recipient_whatsapp: forms.notification.recipient_whatsapp || null
      });
      setSuccess(`Generated ${result.length} notification records across the selected channels.`);
      await loadOps();
    } catch (notificationError) {
      setError(notificationError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runQueuedEmailDispatch() {
    setSubmitting("Email dispatch");
    setSuccess("");
    setError("");
    try {
      const result = await sendQueuedEmailNotifications(token);
      setEmailDispatchResult(result);
      setSuccess(`Email dispatch completed. ${result.sent} of ${result.processed} queued email notifications processed via ${result.mode}.`);
      await loadOps();
    } catch (dispatchError) {
      setError(dispatchError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runQueuedSmsDispatch() {
    setSubmitting("SMS dispatch");
    setSuccess("");
    setError("");
    try {
      const result = await sendQueuedSmsNotifications(token);
      setSmsDispatchResult(result);
      setSuccess(`SMS dispatch completed. ${result.sent} of ${result.processed} queued SMS notifications processed via ${result.mode}.`);
      await loadOps();
    } catch (dispatchError) {
      setError(dispatchError.message);
    } finally {
      setSubmitting("");
    }
  }

  async function runQueuedWhatsAppDispatch() {
    setSubmitting("WhatsApp dispatch");
    setSuccess("");
    setError("");
    try {
      const result = await sendQueuedWhatsAppNotifications(token);
      setWhatsAppDispatchResult(result);
      setSuccess(`WhatsApp dispatch completed. ${result.sent} of ${result.processed} queued WhatsApp notifications processed via ${result.mode}.`);
      await loadOps();
    } catch (dispatchError) {
      setError(dispatchError.message);
    } finally {
      setSubmitting("");
    }
  }

  return (
    <>
      <Topbar
        title="Operations console for live ingestion and analyst review"
        subtitle="Data Ops"
        chipTone="green"
        chipText={`${opsData.signals.length} filtered signals`}
        user={user}
        initials={initials}
      />

      <section className="ops-toolbar">
        <div className="ops-filter-card">
          <div className="card-header">
            <div>
              <h3>Live filters</h3>
              <p className="muted">Query the backend resources the same way operations teams will.</p>
            </div>
          </div>
          <div className="filter-grid">
            <FilterField label="Disease" value={filters.disease} onChange={(value) => setFilters((current) => ({ ...current, disease: value }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis", ""]} />
            <FilterInput label="Location" value={filters.location} onChange={(value) => setFilters((current) => ({ ...current, location: value }))} placeholder="Ondo, Edo, FCT..." />
            <FilterField label="Signal class" value={filters.classification} onChange={(value) => setFilters((current) => ({ ...current, classification: value }))} options={["", "Red", "Amber", "Green"]} />
            <FilterField label="Risk level" value={filters.riskLevel} onChange={(value) => setFilters((current) => ({ ...current, riskLevel: value }))} options={["", "High", "Medium", "Low"]} />
            <FilterField label="Recommendation priority" value={filters.priority} onChange={(value) => setFilters((current) => ({ ...current, priority: value }))} options={["", "High", "Medium", "Low"]} />
            <FilterField label="Clinic severity" value={filters.severity} onChange={(value) => setFilters((current) => ({ ...current, severity: value }))} options={["", "High", "Medium", "Low"]} />
          </div>
          {error ? <p className="auth-error">{error}</p> : null}
        </div>
      </section>

      <section className="grid-3">
        <article className="card">
          <div className="metric">
            <strong>{opsData.signals.length}</strong>
            <span className="muted">Signals matching current filters</span>
          </div>
        </article>
        <article className="card">
          <div className="metric">
            <strong>{opsData.clinicReports.length}</strong>
            <span className="muted">Clinic reports returned by the live backend</span>
          </div>
        </article>
        <article className="card">
          <div className="metric">
            <strong>{opsData.recommendations.length}</strong>
            <span className="muted">Active recommendations for analyst review</span>
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Historical training coverage</h3>
              <p className="muted">This is the dataset admin layer for the auto-discovery pipeline.</p>
            </div>
            <div className="status-chip green">{opsData.datasetStatus?.covered_weeks?.length || 0} weeks loaded</div>
          </div>
          <div className="grid-3 compact-metrics">
            <article className="mini-panel">
              <div className="metric">
                <strong>{opsData.datasetStatus?.historical_reports || 0}</strong>
                <span className="muted">Historical SITREPs</span>
              </div>
            </article>
            <article className="mini-panel">
              <div className="metric">
                <strong>{opsData.datasetStatus?.training_rows || 0}</strong>
                <span className="muted">Training rows built</span>
              </div>
            </article>
            <article className="mini-panel">
              <div className="metric">
                <strong>{opsData.modelStatus?.sample_count || 0}</strong>
                <span className="muted">Rows used by model</span>
              </div>
            </article>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Week</th>
                <th>Confirmed</th>
                <th>Cumulative</th>
                <th>Deaths</th>
                <th>CFR</th>
              </tr>
            </thead>
            <tbody>
              {opsData.historicalReports.map((item) => (
                <tr key={`${item.year}-${item.epi_week}`}>
                  <td>{item.year}-W{String(item.epi_week).padStart(2, "0")}</td>
                  <td>{item.confirmed_current}</td>
                  <td>{item.confirmed_cumulative}</td>
                  <td>{item.deaths_cumulative}</td>
                  <td>{item.cfr_cumulative}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Drop-in historical workflow</h3>
              <p className="muted">Use these folders to grow the training corpus without editing code.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Reports folder" copy="Place extracted SITREP JSON files in backend/data/historical/reports." />
            <InfoRow title="Weather folder" copy="Place state-and-week weather CSVs in backend/data/historical/weather." />
            <InfoRow title="Symptoms folder" copy="Place historical symptom aggregate CSVs in backend/data/historical/symptoms." />
            <InfoRow title="News folder" copy="Place historical NLP/news aggregate CSVs in backend/data/historical/news." />
          </div>
          <div className="footer-note">
            After adding files, use <code>Run auto historical refresh</code>. The backend will discover the files, rebuild the dataset, and retrain the baseline model automatically.
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Training history</h3>
              <p className="muted">Each refresh and retrain is now logged so you can see model progress over time.</p>
            </div>
            <div className="status-chip amber">{opsData.trainingHistory.length} recorded runs</div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Trigger</th>
                <th>Samples</th>
                <th>Accuracy</th>
                <th>MAE</th>
                <th>Reports</th>
              </tr>
            </thead>
            <tbody>
              {opsData.trainingHistory.map((item) => (
                <tr key={item.id}>
                  <td>{item.trigger_source}</td>
                  <td>{item.sample_count}</td>
                  <td>{item.accuracy ?? "n/a"}</td>
                  <td>{item.mae ?? "n/a"}</td>
                  <td>{item.historical_reports}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Training trend readout</h3>
              <p className="muted">This gives you a judge-friendly story as the model improves with more weeks.</p>
            </div>
          </div>
          <div className="feed">
            {opsData.trainingHistory.slice(0, 3).map((item) => (
              <InfoRow
                key={`trend-${item.id}`}
                title={`${item.trigger_source} run`}
                copy={`Samples ${item.sample_count}, accuracy ${item.accuracy ?? "n/a"}, MAE ${item.mae ?? "n/a"}, historical reports ${item.historical_reports}.`}
              />
            ))}
            {!opsData.trainingHistory.length ? (
              <InfoRow title="No training runs yet" copy="Use manual train or auto historical refresh to start collecting model history." />
            ) : null}
          </div>
          <div className="footer-note">
            As you add more weeks, this panel becomes the clearest proof that ClinicAI Sentinel is learning from richer surveillance history rather than staying static.
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Structured symptom intake</h3>
              <p className="muted">Healthcare workers can now submit the exact symptom mix needed for surveillance scoring.</p>
            </div>
          </div>
          <div className="form-grid form-grid-2">
            <FilterInput label="Facility" value={forms.symptom.facility_name} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, facility_name: value } }))} placeholder="Akure General Hospital" />
            <FilterInput label="Location" value={forms.symptom.location} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, location: value }, pipeline: { ...current.pipeline, location: value } }))} placeholder="Ondo" />
            <FilterField label="Disease" value={forms.symptom.disease} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, disease: value }, pipeline: { ...current.pipeline, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterInput label="Report date" value={forms.symptom.report_date} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, report_date: value } }))} placeholder="2026-04-27T10:00" type="datetime-local" />
            <FilterInput label="Fever cases" value={forms.symptom.fever_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, fever_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Headache cases" value={forms.symptom.headache_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, headache_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Vomiting cases" value={forms.symptom.vomiting_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, vomiting_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Weakness cases" value={forms.symptom.weakness_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, weakness_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Bleeding cases" value={forms.symptom.bleeding_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, bleeding_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Contact history cases" value={forms.symptom.contact_history_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, contact_history_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Suspected cases" value={forms.symptom.suspected_cases} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, suspected_cases: value } }))} placeholder="0" type="number" />
            <FilterInput label="Reported by" value={forms.symptom.reported_by} onChange={(value) => setForms((current) => ({ ...current, symptom: { ...current.symptom, reported_by: value }, pipeline: { ...current.pipeline, analyst: value } }))} placeholder="Surveillance nurse" />
          </div>
          <label className="filter-field stacked-field">
            <span className="tiny muted">Clinical notes</span>
            <textarea value={forms.symptom.notes} onChange={(event) => setForms((current) => ({ ...current, symptom: { ...current.symptom, notes: event.target.value } }))} placeholder="Add suspected exposure, community notes, or lab context." />
          </label>
          <div className="form-actions">
            <button
              className="btn primary"
              type="button"
              disabled={submitting === "Symptom report"}
              onClick={() =>
                submitForm("Symptom report", () =>
                  createSymptomReport(token, {
                    ...forms.symptom,
                    report_date: new Date(forms.symptom.report_date).toISOString(),
                    fever_cases: Number(forms.symptom.fever_cases),
                    headache_cases: Number(forms.symptom.headache_cases),
                    vomiting_cases: Number(forms.symptom.vomiting_cases),
                    weakness_cases: Number(forms.symptom.weakness_cases),
                    bleeding_cases: Number(forms.symptom.bleeding_cases),
                    contact_history_cases: Number(forms.symptom.contact_history_cases),
                    suspected_cases: Number(forms.symptom.suspected_cases)
                  })
                )
              }
            >
              Save symptom report
            </button>
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Weather and verified news ingestion</h3>
              <p className="muted">These forms drive the environmental layer and the NLP source layer of the platform.</p>
            </div>
          </div>
          <div className="form-grid form-grid-2">
            <FilterField label="Ingestion disease" value={forms.ingestion.disease} onChange={(value) => setForms((current) => ({ ...current, ingestion: { ...current.ingestion, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterInput label="News items per source" value={forms.ingestion.max_items_per_source} onChange={(value) => setForms((current) => ({ ...current, ingestion: { ...current.ingestion, max_items_per_source: value } }))} placeholder="2" type="number" />
            <FilterInput label="Weather target states" value={forms.ingestion.weather_locations} onChange={(value) => setForms((current) => ({ ...current, ingestion: { ...current.ingestion, weather_locations: value } }))} placeholder="Ondo,Edo,Bauchi" />
            <FilterInput label="Weather location" value={forms.weather.location} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, location: value } }))} placeholder="Ondo" />
            <FilterField label="Weather disease" value={forms.weather.disease} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterInput label="Temperature C" value={forms.weather.temperature_c} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, temperature_c: value } }))} placeholder="33" type="number" />
            <FilterInput label="Rainfall mm" value={forms.weather.rainfall_mm} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, rainfall_mm: value } }))} placeholder="14" type="number" />
            <FilterInput label="Humidity %" value={forms.weather.humidity_pct} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, humidity_pct: value } }))} placeholder="52" type="number" />
            <FilterInput label="Dry season index" value={forms.weather.dry_season_index} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, dry_season_index: value } }))} placeholder="0.78" type="number" />
            <FilterInput label="Weather source" value={forms.weather.source_name} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, source_name: value } }))} placeholder="NiMet feed" />
            <FilterInput label="Recorded at" value={forms.weather.recorded_at} onChange={(value) => setForms((current) => ({ ...current, weather: { ...current.weather, recorded_at: value } }))} placeholder="2026-04-27T10:00" type="datetime-local" />
          </div>
          <div className="form-actions">
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Trusted news ingestion"}
              onClick={runNewsIngestion}
            >
              Fetch trusted news
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Weather ingestion"}
              onClick={runWeatherIngestion}
            >
              Fetch live weather
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Weather record"}
              onClick={() =>
                submitForm("Weather record", () =>
                  createWeatherRecord(token, {
                    ...forms.weather,
                    temperature_c: Number(forms.weather.temperature_c),
                    rainfall_mm: Number(forms.weather.rainfall_mm),
                    humidity_pct: Number(forms.weather.humidity_pct),
                    dry_season_index: Number(forms.weather.dry_season_index),
                    recorded_at: new Date(forms.weather.recorded_at).toISOString()
                  })
                )
              }
            >
              Save weather record
            </button>
          </div>
          <div className="divider"></div>
          <div className="form-grid form-grid-2">
            <FilterInput label="News title" value={forms.news.title} onChange={(value) => setForms((current) => ({ ...current, news: { ...current.news, title: value } }))} placeholder="Rodent infestation rises in Ondo communities" />
            <FilterInput label="News location" value={forms.news.location} onChange={(value) => setForms((current) => ({ ...current, news: { ...current.news, location: value } }))} placeholder="Ondo" />
            <FilterField label="News disease" value={forms.news.disease} onChange={(value) => setForms((current) => ({ ...current, news: { ...current.news, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterField label="Verification" value={forms.news.verification_status} onChange={(value) => setForms((current) => ({ ...current, news: { ...current.news, verification_status: value } }))} options={["Verified", "Review", "Unverified"]} />
            <FilterInput label="News source" value={forms.news.source_name} onChange={(value) => setForms((current) => ({ ...current, news: { ...current.news, source_name: value } }))} placeholder="Trusted Health Desk" />
            <FilterInput label="Published at" value={forms.news.published_at} onChange={(value) => setForms((current) => ({ ...current, news: { ...current.news, published_at: value } }))} placeholder="2026-04-27T09:00" type="datetime-local" />
          </div>
          <label className="filter-field stacked-field">
            <span className="tiny muted">News content</span>
            <textarea value={forms.news.content} onChange={(event) => setForms((current) => ({ ...current, news: { ...current.news, content: event.target.value } }))} placeholder="Paste the verified report text so the NLP layer can extract outbreak signals." />
          </label>
          <div className="form-actions">
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "News analysis"}
              onClick={analyzeNewsArticle}
            >
              Analyze news text
            </button>
            <button
              className="btn primary"
              type="button"
              disabled={submitting === "News record"}
              onClick={() =>
                submitForm("News record", () =>
                  createNewsRecord(token, {
                    ...forms.news,
                    published_at: new Date(forms.news.published_at).toISOString()
                  })
                )
              }
            >
              Save news record
            </button>
          </div>
          {newsAnalysis ? (
            <div className="analysis-preview">
              <div className="card-header">
                <div>
                  <h3>NLP preview</h3>
                  <p className="muted">This is the structured signal the article currently produces.</p>
                </div>
                <div className={`status-chip ${newsAnalysis.classification.toLowerCase()}`}>{newsAnalysis.classification}</div>
              </div>
              <div className="grid-3 compact-metrics">
                <article className="mini-panel">
                  <div className="metric">
                    <strong>{newsAnalysis.location}</strong>
                    <span className="muted">Detected location</span>
                  </div>
                </article>
                <article className="mini-panel">
                  <div className="metric">
                    <strong>{Math.round(newsAnalysis.confidence * 100)}%</strong>
                    <span className="muted">Confidence score</span>
                  </div>
                </article>
                <article className="mini-panel">
                  <div className="metric">
                    <strong>{newsAnalysis.source_trust}</strong>
                    <span className="muted">Source trust</span>
                  </div>
                </article>
              </div>
              <div className="feed">
                <InfoRow title="Signal type" copy={newsAnalysis.signal_type} />
                <InfoRow title="Matched locations" copy={newsAnalysis.matched_locations.join(", ") || "No location extracted"} />
                <InfoRow title="Matched terms" copy={newsAnalysis.matched_terms.join(", ") || "No outbreak terms matched"} />
              </div>
              <div className="footer-note">
                <strong>Preview summary</strong>
                <div>{newsAnalysis.summary}</div>
              </div>
            </div>
          ) : null}
          {ingestionResult ? (
            <div className="footer-note">
              <strong>Latest ingestion run</strong>
              <div>
                {ingestionResult.mode} created {ingestionResult.records_created} records
                {typeof ingestionResult.signals_created === "number" ? ` and ${ingestionResult.signals_created} signals` : ""}.
              </div>
              {ingestionResult.errors?.length ? (
                <div className="tiny">Warnings: {ingestionResult.errors.join(" | ")}</div>
              ) : null}
            </div>
          ) : null}
        </article>
      </section>

      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Signal intake and pipeline runner</h3>
              <p className="muted">This is the end-to-end control surface for the new AI surveillance flow.</p>
            </div>
          </div>
          <div className="form-grid form-grid-2">
            <FilterInput label="Signal title" value={forms.signal.title} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, title: value } }))} placeholder="Possible rodent-linked community concern" />
            <FilterInput label="Signal location" value={forms.signal.location} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, location: value } }))} placeholder="Ondo" />
            <FilterField label="Signal disease" value={forms.signal.disease} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterField label="Classification" value={forms.signal.classification} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, classification: value } }))} options={["Red", "Amber", "Green"]} />
            <FilterField label="Risk factor" value={forms.signal.risk_factor} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, risk_factor: value } }))} options={["HIGH", "MEDIUM", "LOW"]} />
            <FilterInput label="Confidence" value={forms.signal.confidence} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, confidence: value } }))} placeholder="0.74" type="number" />
            <FilterInput label="Source type" value={forms.signal.source_type} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, source_type: value } }))} placeholder="News crawl" />
            <FilterInput label="Source name" value={forms.signal.source_name} onChange={(value) => setForms((current) => ({ ...current, signal: { ...current.signal, source_name: value } }))} placeholder="Verified national news" />
          </div>
          <label className="filter-field stacked-field">
            <span className="tiny muted">Signal summary</span>
            <textarea value={forms.signal.summary} onChange={(event) => setForms((current) => ({ ...current, signal: { ...current.signal, summary: event.target.value } }))} placeholder="Summarize why this source should influence the model." />
          </label>
          <div className="form-actions">
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Signal"}
              onClick={() =>
                submitForm("Signal", () =>
                  createSignal(token, {
                    ...forms.signal,
                    confidence: Number(forms.signal.confidence)
                  })
                )
              }
            >
              Save signal
            </button>
          </div>
          <div className="divider"></div>
          <div className="form-grid form-grid-3">
            <FilterField label="Analysis disease" value={forms.pipeline.disease} onChange={(value) => setForms((current) => ({ ...current, pipeline: { ...current.pipeline, disease: value }, report: { ...current.report, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterInput label="Analysis location" value={forms.pipeline.location} onChange={(value) => setForms((current) => ({ ...current, pipeline: { ...current.pipeline, location: value } }))} placeholder="Ondo" />
            <FilterInput label="Analyst name" value={forms.pipeline.analyst} onChange={(value) => setForms((current) => ({ ...current, pipeline: { ...current.pipeline, analyst: value }, report: { ...current.report, analyst: value } }))} placeholder="Demo Analyst" />
          </div>
          <div className="form-grid form-grid-2">
            <FilterField label="Report disease" value={forms.report.disease} onChange={(value) => setForms((current) => ({ ...current, report: { ...current.report, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterInput label="Report analyst" value={forms.report.analyst} onChange={(value) => setForms((current) => ({ ...current, report: { ...current.report, analyst: value } }))} placeholder="Demo Analyst" />
          </div>
          <div className="divider"></div>
          <div className="card-header">
            <div>
              <h3>Notification dispatch</h3>
              <p className="muted">Queue dashboard, email, SMS, and WhatsApp notifications from active alerts. If recipient fields are empty, saved role contact details will be used.</p>
            </div>
          </div>
          <div className="form-grid form-grid-3">
            <FilterField label="Notification disease" value={forms.notification.disease} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, disease: value } }))} options={["Lassa fever", "Cholera", "Mpox", "Meningitis"]} />
            <FilterInput label="Audience" value={forms.notification.audience} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, audience: value } }))} placeholder="Public health" />
            <FilterInput label="Email recipient" value={forms.notification.recipient_email} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, recipient_email: value, recipient: value } }))} placeholder="surveillance@clinicai-sentinel.local" />
            <FilterInput label="SMS recipient" value={forms.notification.recipient_sms} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, recipient_sms: value } }))} placeholder="+2348000000000" />
            <FilterInput label="WhatsApp recipient" value={forms.notification.recipient_whatsapp} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, recipient_whatsapp: value } }))} placeholder="+2348000000000" />
            <FilterField label="Manual channel" value={forms.notification.channel} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, channel: value } }))} options={["Dashboard", "Email", "SMS", "WhatsApp"]} />
            <FilterInput label="Manual location" value={forms.notification.location} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, location: value } }))} placeholder="Ondo" />
            <FilterField label="Manual priority" value={forms.notification.priority} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, priority: value } }))} options={["High", "Medium", "Low"]} />
            <FilterInput label="Manual title" value={forms.notification.title} onChange={(value) => setForms((current) => ({ ...current, notification: { ...current.notification, title: value } }))} placeholder="Red alert review for Ondo" />
          </div>
          <label className="filter-field stacked-field">
            <span className="tiny muted">Manual notification message</span>
            <textarea value={forms.notification.message} onChange={(event) => setForms((current) => ({ ...current, notification: { ...current.notification, message: event.target.value } }))} placeholder="Summarize the alert and the action clinics or officers should take." />
          </label>
          <div className="form-actions">
            <button
              className="btn primary"
              type="button"
              disabled={submitting === "Pipeline analysis"}
              onClick={() =>
                submitForm("Pipeline analysis", async () => {
                  const result = await runPipelineAnalysis(token, forms.pipeline);
                  setPipelineResult(result);
                })
              }
            >
              Run end-to-end analysis
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Model training"}
              onClick={() =>
                submitForm("Model training", async () => {
                  const status = await trainModel(token);
                  setOpsData((current) => ({ ...current, modelStatus: status }));
                })
              }
            >
              Train baseline model
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Historical refresh"}
              onClick={() =>
                submitForm("Historical refresh", async () => {
                  const result = await runAutoDatasetRefresh(token);
                  setSuccess(
                    `Historical refresh completed. Reports ${result.reports_loaded}, weather ${result.weather_rows_loaded}, symptoms ${result.symptom_rows_loaded}, news ${result.news_rows_loaded}.`
                  );
                })
              }
            >
              Run auto historical refresh
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Daily report"}
              onClick={runDailyReportExport}
            >
              Generate daily report
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Notification generation"}
              onClick={runNotificationGeneration}
            >
              Generate notifications
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Notification"}
              onClick={() =>
                submitForm("Notification", () =>
                  createNotification(token, {
                    disease: forms.notification.disease,
                    location: forms.notification.location,
                    channel: forms.notification.channel,
                    audience: forms.notification.audience,
                    priority: forms.notification.priority,
                    status: forms.notification.status,
                    title: forms.notification.title,
                    message: forms.notification.message,
                    recipient: forms.notification.channel === "Dashboard" ? null : forms.notification.recipient
                  })
                )
              }
            >
              Save manual notification
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "Email dispatch"}
              onClick={runQueuedEmailDispatch}
            >
              Send queued emails
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "SMS dispatch"}
              onClick={runQueuedSmsDispatch}
            >
              Send queued SMS
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={submitting === "WhatsApp dispatch"}
              onClick={runQueuedWhatsAppDispatch}
            >
              Send queued WhatsApp
            </button>
          </div>
          {success ? <p className="success-copy">{success}</p> : null}
          {pipelineResult ? (
            <div className="footer-note">
              <strong>Latest pipeline result</strong>
              <div>{pipelineResult.summary}</div>
              <div className="tiny">
                Prediction: {pipelineResult.prediction.risk_level} ({Math.round(pipelineResult.prediction.risk_score * 100)}%)
              </div>
            </div>
          ) : null}
          {opsData.modelStatus ? (
            <div className="footer-note">
              <strong>Model status</strong>
              <div>{opsData.modelStatus.ready ? opsData.modelStatus.model_name : "No trained artifact yet"}</div>
              <div className="tiny">
                Samples: {opsData.modelStatus.sample_count} | Accuracy: {opsData.modelStatus.accuracy ?? "n/a"} | MAE: {opsData.modelStatus.mae ?? "n/a"}
              </div>
            </div>
          ) : null}
          {opsData.datasetStatus ? (
            <div className="footer-note">
              <strong>Dataset status</strong>
              <div>
                Reports: {opsData.datasetStatus.historical_reports} | Training rows: {opsData.datasetStatus.training_rows}
              </div>
              <div className="tiny">
                Weeks: {opsData.datasetStatus.covered_weeks.length ? opsData.datasetStatus.covered_weeks.join(", ") : "No historical weeks loaded yet"}
              </div>
            </div>
          ) : null}
          {reportResult ? (
            <div className="footer-note">
              <strong>Latest report export</strong>
              <div>{reportResult.report_title}</div>
              <div className="tiny">Markdown: {reportResult.markdown_report_path || reportResult.report_path}</div>
              <div className="tiny">HTML: {reportResult.html_report_path}</div>
              <div className="tiny">PDF: {reportResult.pdf_report_path}</div>
              <div className="tiny">High-risk locations: {reportResult.high_risk_locations.length ? reportResult.high_risk_locations.join(", ") : "None"}</div>
            </div>
          ) : null}
          {opsData.notifications.length ? (
            <div className="footer-note">
              <strong>Latest notification queue</strong>
              <div>{opsData.notifications[0].title}</div>
              <div className="tiny">
                {opsData.notifications[0].channel} | {opsData.notifications[0].location} | {opsData.notifications[0].priority}
              </div>
            </div>
          ) : null}
          {emailDispatchResult ? (
            <div className="footer-note">
              <strong>Email dispatch status</strong>
              <div>
                Processed {emailDispatchResult.processed}, sent {emailDispatchResult.sent}, failed {emailDispatchResult.failed} via {emailDispatchResult.mode}.
              </div>
              {emailDispatchResult.outbox_paths?.length ? (
                <div className="tiny">Outbox files: {emailDispatchResult.outbox_paths.join(" | ")}</div>
              ) : null}
            </div>
          ) : null}
          {smsDispatchResult ? (
            <div className="footer-note">
              <strong>SMS dispatch status</strong>
              <div>
                Processed {smsDispatchResult.processed}, sent {smsDispatchResult.sent}, failed {smsDispatchResult.failed} via {smsDispatchResult.mode}.
              </div>
              {smsDispatchResult.outbox_paths?.length ? (
                <div className="tiny">SMS outbox files: {smsDispatchResult.outbox_paths.join(" | ")}</div>
              ) : null}
            </div>
          ) : null}
          {whatsAppDispatchResult ? (
            <div className="footer-note">
              <strong>WhatsApp dispatch status</strong>
              <div>
                Processed {whatsAppDispatchResult.processed}, sent {whatsAppDispatchResult.sent}, failed {whatsAppDispatchResult.failed} via {whatsAppDispatchResult.mode}.
              </div>
              {whatsAppDispatchResult.outbox_paths?.length ? (
                <div className="tiny">WhatsApp outbox files: {whatsAppDispatchResult.outbox_paths.join(" | ")}</div>
              ) : null}
            </div>
          ) : null}
        </article>

        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>New intake layers</h3>
              <p className="muted">These raw sources now feed the generated prediction and alert workflow.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Symptom reports</th>
                <th>Weather records</th>
                <th>News records</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{opsData.symptomReports.length}</td>
                <td>{opsData.weatherRecords.length}</td>
                <td>{opsData.newsRecords.length}</td>
              </tr>
            </tbody>
          </table>
          <div className="feed">
            {opsData.symptomReports.slice(0, 3).map((item) => (
              <InfoRow
                key={`symptom-${item.id}`}
                title={`${item.location} symptom report`}
                copy={`${item.facility_name}: fever ${item.fever_cases}, bleeding ${item.bleeding_cases}, suspected ${item.suspected_cases}.`}
              />
            ))}
            {opsData.weatherRecords.slice(0, 2).map((item) => (
              <InfoRow
                key={`weather-${item.id}`}
                title={`${item.location} weather snapshot`}
                copy={`Temp ${item.temperature_c}C, rainfall ${item.rainfall_mm}mm, dry index ${item.dry_season_index}.`}
              />
            ))}
            {opsData.newsRecords.slice(0, 2).map((item) => (
              <InfoRow
                key={`news-${item.id}`}
                title={item.title}
                copy={`${item.location} | ${item.verification_status} | ${item.source_name}`}
              />
            ))}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Signals</h3>
              <p className="muted">Crawler and NLP outputs ordered by confidence.</p>
            </div>
            <div className="status-chip amber">{loading ? "Refreshing" : "Live query"}</div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Location</th>
                <th>Class</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {opsData.signals.map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td>{item.location}</td>
                  <td><span className={`tag ${item.classification.toLowerCase()}`}>{item.classification}</span></td>
                  <td>{item.confidence.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Clinic reports</h3>
              <p className="muted">Operational intake from facilities and surveillance teams.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Facility</th>
                <th>Location</th>
                <th>Severity</th>
                <th>Patients</th>
              </tr>
            </thead>
            <tbody>
              {opsData.clinicReports.map((item) => (
                <tr key={item.id}>
                  <td>{item.facility_name}</td>
                  <td>{item.location}</td>
                  <td><span className={`tag ${item.severity === "High" ? "red" : item.severity === "Medium" ? "amber" : "green"}`}>{item.severity}</span></td>
                  <td>{item.patient_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Predictions</h3>
              <p className="muted">Model outputs exposed directly from the backend domain layer.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Disease</th>
                <th>Location</th>
                <th>Risk</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {opsData.predictions.map((item) => (
                <tr key={item.id}>
                  <td>{item.disease}</td>
                  <td>{item.location}</td>
                  <td><span className={`tag ${item.risk_level === "High" ? "red" : item.risk_level === "Medium" ? "amber" : "green"}`}>{item.risk_level}</span></td>
                  <td>{item.risk_score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Alerts and actions</h3>
              <p className="muted">Decision-support output prepared for clinic response.</p>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Disease</th>
                <th>Level</th>
                <th>State</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {opsData.alerts.map((item) => (
                <tr key={item.id}>
                  <td>{item.disease}</td>
                  <td><span className={`tag ${item.level.toLowerCase()}`}>{item.level}</span></td>
                  <td>{item.location}</td>
                  <td>{item.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="grid-2">
        <article className="table-card">
          <div className="card-header">
            <div>
              <h3>Notifications</h3>
              <p className="muted">Queued outbound messages generated from active surveillance alerts.</p>
            </div>
            <div className="status-chip green">{opsData.notifications.length} queued items</div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Channel</th>
                <th>Audience</th>
                <th>Location</th>
                <th>Priority</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {opsData.notifications.map((item) => (
                <tr key={item.id}>
                  <td>{item.channel}</td>
                  <td>{item.audience}</td>
                  <td>{item.location}</td>
                  <td><span className={`tag ${item.priority === "High" ? "red" : item.priority === "Medium" ? "amber" : "green"}`}>{item.priority}</span></td>
                  <td>{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="list-card">
          <div className="card-header">
            <div>
              <h3>Recommendations</h3>
              <p className="muted">Priority-sorted outputs from the action layer.</p>
            </div>
          </div>
          <div className="feed">
            {opsData.recommendations.map((item) => (
              <div className="insight-item" key={item.id}>
                <div>
                  <div className="signal-title">{item.title}</div>
                  <div className="muted">{item.description}</div>
                </div>
                <span className={`tag ${item.priority === "High" ? "red" : item.priority === "Medium" ? "amber" : "green"}`}>{item.priority}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <div className="card-header">
            <div>
              <h3>Why this page matters</h3>
              <p className="muted">It bridges your new ingestion APIs with operational visibility.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Analyst workflow" copy="Use filters to inspect only the highest-risk records from live backend tables." />
            <InfoRow title="Pipeline verification" copy="Confirms that symptom intake, weather, news, generated signals, predictions, and recommendations are landing correctly." />
            <InfoRow title="Next expansion point" copy="This page can later add exports, approval actions, and audit views without changing the core surveillance workflow." />
          </div>
          <div className="footer-note">
            The operations page now demonstrates the central promise of ClinicAI Sentinel: collect multi-source evidence, generate risk intelligence, and surface response-ready actions from one workspace.
          </div>
        </article>
      </section>
    </>
  );
}

function RestrictedPage({ initials, user, area }) {
  const role = getRole(user);
  return (
    <>
      <Topbar
        title={`${area} is restricted for this role`}
        subtitle="Access control"
        chipTone="amber"
        chipText={`Role: ${role.replace("_", " ")}`}
        user={user}
        initials={initials}
      />
      <section className="grid-2">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>Access guidance</h3>
              <p className="muted">ClinicAI Sentinel now separates clinical, public-health, and admin workflows.</p>
            </div>
          </div>
          <div className="feed">
            <InfoRow title="Clinic users" copy="Can focus on reporting symptoms, reviewing alerts, and following recommendations." />
            <InfoRow title="Public health officers" copy="Can review analytics, location risk trends, and generated summaries." />
            <InfoRow title="Admin / Data Ops" copy="Can manage ingestion, retraining, historical refresh, and system-level exports." />
          </div>
          <div className="footer-note">
            Your current role does not include access to <strong>{area}</strong>. Switch to an allowed role in demo mode or use an account mapped to the right responsibility.
          </div>
        </article>
      </section>
    </>
  );
}

function FilterField({ label, value, onChange, options }) {
  return (
    <label className="filter-field">
      <span className="tiny muted">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option || "all"} value={option}>
            {option || "All"}
          </option>
        ))}
      </select>
    </label>
  );
}

function FilterInput({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="filter-field">
      <span className="tiny muted">{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  );
}

function MetricPanel({ value, label, tone, status }) {
  return (
    <div className="mini-panel">
      <div className="metric-row">
        <div className="metric">
          <strong>{value}</strong>
          <span className="muted">{label}</span>
        </div>
        <div className={`status-chip ${tone}`}>{status}</div>
      </div>
    </div>
  );
}

function InfoRow({ title, copy }) {
  return (
    <div className="insight-item">
      <div>
        <div className="signal-title">{title}</div>
        <div className="muted">{copy}</div>
      </div>
    </div>
  );
}

function ActionRow({ title, tone, status }) {
  return (
    <div className="feed-item">
      <div className="signal-title">{title}</div>
      <div className={`status-chip ${tone}`}>{status}</div>
    </div>
  );
}

function StatBox({ value, label }) {
  return (
    <div className="stat-box">
      <strong>{value}</strong>
      <div className="tiny muted">{label}</div>
    </div>
  );
}

function formatDateTime(value) {
  if (!value) {
    return "Unknown time";
  }

  return new Date(value).toLocaleString("en-NG", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function timeAgo(value) {
  if (!value) {
    return "just now";
  }

  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours} hr ago`;
  }
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function truncateText(value, limit) {
  if (!value || value.length <= limit) {
    return value;
  }
  return `${value.slice(0, limit).trim()}...`;
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function storyTone(location = "") {
  const key = location.toLowerCase();
  if (key.includes("ondo") || key.includes("edo")) {
    return "story-red";
  }
  if (key.includes("bauchi") || key.includes("plateau")) {
    return "story-amber";
  }
  return "story-green";
}

function weatherTone(drySeasonIndex = 0) {
  if (drySeasonIndex >= 0.75) {
    return "weather-dry";
  }
  if (drySeasonIndex >= 0.45) {
    return "weather-mixed";
  }
  return "weather-wet";
}

function buildWeatherNarrative(item) {
  return `${item.location} recorded ${item.temperature_c}C with ${item.rainfall_mm} mm rainfall, ${item.humidity_pct}% humidity, and a dry-season index of ${item.dry_season_index}.`;
}

function stateMapPosition(state, index = 0) {
  const positions = {
    Ondo: { top: "38%", left: "39%" },
    Edo: { top: "54%", left: "34%" },
    Ebonyi: { top: "50%", left: "51%" },
    Bauchi: { top: "21%", left: "58%" },
    Taraba: { top: "38%", left: "67%" },
    Benue: { top: "47%", left: "57%" },
    Plateau: { top: "34%", left: "51%" },
    Nasarawa: { top: "42%", left: "53%" },
    Kogi: { top: "49%", left: "45%" },
    Ogun: { top: "58%", left: "27%" },
    Lagos: { top: "68%", left: "24%" },
    Oyo: { top: "49%", left: "24%" },
    Gombe: { top: "26%", left: "66%" },
    Kaduna: { top: "26%", left: "47%" },
    FCT: { top: "41%", left: "47%" },
    "Cross River": { top: "58%", left: "62%" }
  };
  return positions[state] || { top: `${26 + (index % 5) * 10}%`, left: `${24 + (index % 4) * 11}%` };
}

export default App;
