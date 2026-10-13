import React, { useEffect, useState, useCallback, useMemo } from 'react';
import * as api from './api.js';

/* ══════════════════════════════════════════════════════════════
   SVG Icons (inline, tree-shakeable)
   ══════════════════════════════════════════════════════════════ */
const Icon = ({ d, size = 18, ...p }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>{typeof d === 'string' ? <path d={d} /> : d}</svg>
);
const icons = {
  home: <Icon d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />,
  users: <Icon d={<><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 00-3-3.87" /><path d="M16 3.13a4 4 0 010 7.75" /></>} />,
  pill: <Icon d={<><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18M3 9h18" /></>} />,
  clipboard: <Icon d={<><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" ry="1" /></>} />,
  settings: <Icon d={<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></>} />,
  logout: <Icon d={<><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></>} />,
  plus: <Icon d={<><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>} />,
  search: <Icon d={<><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>} size={16} />,
  x: <Icon d={<><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></>} />,
  heart: <Icon d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />,
  activity: <Icon d={<><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></>} />,
  eye: <Icon d={<><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></>} />,
  edit: <Icon d={<><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" /></>} />,
  trash: <Icon d={<><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></>} />,
  check: <Icon d={<><polyline points="20 6 9 17 4 12" /></>} />,
};


/* ══════════════════════════════════════════════════════════════
   App Root
   ══════════════════════════════════════════════════════════════ */
export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [page, setPage] = useState('dashboard');
  const [logoutError, setLogoutError] = useState('');
  const [authError, setAuthError] = useState('');
  const [familyAccess, setFamilyAccess] = useState({ profile: false, prescriptions: false });
  const [familyAccessError, setFamilyAccessError] = useState('');

  /* ── Restore session ── */
  useEffect(() => {
    if (api.getToken()) {
      api.getMe()
        .then(u => { setUser(u); setAuthChecked(true); })
        .catch(error => {
          api.clearToken();
          setAuthError(`Could not restore your session: ${error.message}`);
          setAuthChecked(true);
        });
    } else setAuthChecked(true);
  }, []);

  useEffect(() => {
    if (user?.role !== 'family_member') {
      setFamilyAccess({ profile: false, prescriptions: false });
      setFamilyAccessError('');
      return;
    }
    let cancelled = false;
    setFamilyAccess({ profile: false, prescriptions: false });
    setFamilyAccessError('');
    api.getFamilyLinks()
      .then(links => {
        if (cancelled) return;
        setFamilyAccess({
          profile: links.some(link => link.is_active && link.consent_granted && link.can_view_profile),
          prescriptions: links.some(link => link.is_active && link.consent_granted && link.can_view_prescriptions),
        });
      })
      .catch(error => {
        if (!cancelled) setFamilyAccessError(`Could not load your current access permissions: ${error.message}`);
      });
    return () => { cancelled = true; };
  }, [user]);

  const handleLogin = useCallback((u) => {
    setUser(u);
    setPage('dashboard');
    setLogoutError('');
    setAuthError('');
  }, []);
  const handleLogout = useCallback(async () => {
    try {
      await api.logout();
      setLogoutError('');
    } catch (error) {
      setLogoutError(`Signed out locally, but the server could not revoke this session: ${error.message}`);
    } finally {
      setUser(null);
      setPage('dashboard');
    }
  }, []);

  if (!authChecked) return <div className="loading-spinner" style={{ minHeight: '100vh' }}><div className="spinner" /></div>;
  if (!user) return <LoginPage onLogin={handleLogin} message={logoutError || authError} />;

  const navigation = roleNavigation(user.role, familyAccess);
  const permittedPages = new Set([
    ...navigation.map(item => item.key),
    'settings',
  ]);
  const currentPage = permittedPages.has(page) ? page : 'dashboard';
  const changePage = nextPage => {
    if (permittedPages.has(nextPage)) setPage(nextPage);
  };

  return (
    <div className="app-shell">
      <Sidebar user={user} page={currentPage} setPage={changePage} onLogout={handleLogout} navigation={navigation} />
      <div className="main-content">
        <TopBar page={currentPage} />
        {familyAccessError && <div className="alert alert-error">{familyAccessError}</div>}
        <main className="page" key={currentPage}>
          {currentPage === 'dashboard' && <DashboardPage user={user} setPage={changePage} />}
          {currentPage === 'residents' && <ResidentsPage user={user} />}
          {currentPage === 'medicines' && <MedicinesPage user={user} />}
          {currentPage === 'prescriptions' && <PrescriptionsPage user={user} />}
          {currentPage === 'schedule' && <DoseSchedulePage user={user} />}
          {currentPage === 'operations' && <OperationsPage user={user} />}
          {currentPage === 'access' && <AccessPage user={user} />}
          {currentPage === 'settings' && <SettingsPage user={user} />}
        </main>
      </div>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════
   Login Page
   ══════════════════════════════════════════════════════════════ */
function LoginPage({ onLogin, message = '' }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(username, password);
      const me = await api.getMe();
      onLogin(me);
    } catch (err) {
      api.clearToken();
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">C</div>
          <div>
            <h1>CareMeds</h1>
            <p>Medication Management</p>
          </div>
        </div>
        <h2 className="login-title">Welcome back</h2>
        <p className="login-subtitle">Sign in to continue managing care</p>
        {message && <div className="alert alert-error">{message}</div>}
        {error && <div className="login-alert">{error}</div>}
        <form onSubmit={submit}>
          <div className="form-group">
            <label className="form-label" htmlFor="login-user">Username</label>
            <input id="login-user" className="form-input" value={username} onChange={e => setUsername(e.target.value)} placeholder="Enter your username" required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="login-pass">Password</label>
            <input id="login-pass" className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password" required />
          </div>
          <button id="login-submit" className="btn btn-primary" style={{ width: '100%', marginTop: 8 }} disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════
   Sidebar
   ══════════════════════════════════════════════════════════════ */
const commonNav = [
  { key: 'dashboard', label: 'Dashboard', icon: icons.home },
  { key: 'residents', label: 'Residents', icon: icons.users },
  { key: 'medicines', label: 'Medicines', icon: icons.pill },
  { key: 'prescriptions', label: 'Prescriptions', icon: icons.clipboard },
  { key: 'schedule', label: 'Medication Schedule', icon: icons.activity },
];
const ROLE_NAV = {
  admin: [
    ...commonNav,
    { key: 'operations', label: 'Care Operations', icon: icons.activity },
    { key: 'access', label: 'Access Management', icon: icons.settings },
  ],
  doctor: [
    ...commonNav,
    { key: 'operations', label: 'Care Operations', icon: icons.activity },
  ],
  caretaker: [
    ...commonNav.map(item => item.key === 'residents' ? { ...item, label: 'Assigned Residents' } : item),
    { key: 'operations', label: 'Care Operations', icon: icons.activity },
  ],
  resident: [
    ...commonNav.map(item => item.key === 'residents' ? { ...item, label: 'My Records' } : item),
    { key: 'operations', label: 'Reminders', icon: icons.activity },
    { key: 'access', label: 'Family Consent', icon: icons.heart },
  ],
};

function roleNavigation(role, familyAccess) {
  if (role !== 'family_member') return ROLE_NAV[role] || [];
  return [
    { key: 'dashboard', label: 'Dashboard', icon: icons.home },
    ...(familyAccess.profile ? [{ key: 'residents', label: 'Linked Residents', icon: icons.users }] : []),
    { key: 'medicines', label: 'Medicines', icon: icons.pill },
    ...(familyAccess.prescriptions ? [
      { key: 'prescriptions', label: 'Prescriptions', icon: icons.clipboard },
      { key: 'schedule', label: 'Medication Schedule', icon: icons.activity },
    ] : []),
    { key: 'operations', label: 'Care Updates', icon: icons.activity },
    { key: 'access', label: 'Request Resident Access', icon: icons.heart },
  ];
}

function Sidebar({ user, page, setPage, onLogout, navigation }) {
  const initials = (user.full_name || user.username || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  const navItems = navigation;
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">C</div>
        <div>
          <h1>CareMeds</h1>
          <p>Care Platform</p>
        </div>
      </div>
      <nav className="sidebar-nav">
        <div className="sidebar-section">
          <div className="sidebar-section-title">Menu</div>
          {navItems.map(n => (
            <button key={n.key} id={`nav-${n.key}`} className={`sidebar-link${page === n.key ? ' active' : ''}`} onClick={() => setPage(n.key)}>
              {n.icon}<span>{n.label}</span>
            </button>
          ))}
        </div>
        <div className="sidebar-section">
          <div className="sidebar-section-title">System</div>
          <button id="nav-settings" className={`sidebar-link${page === 'settings' ? ' active' : ''}`} onClick={() => setPage('settings')}>
            {icons.settings}<span>Settings</span>
          </button>
        </div>
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">{initials}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user.full_name || user.username}</div>
            <div className="sidebar-user-role">{user.role?.replace('_', ' ')}</div>
          </div>
          <button id="btn-logout" className="sidebar-logout" onClick={onLogout} title="Sign out">{icons.logout}</button>
        </div>
      </div>
    </aside>
  );
}


/* ══════════════════════════════════════════════════════════════
   Top Bar
   ══════════════════════════════════════════════════════════════ */
const PAGE_TITLES = {
  dashboard: 'Dashboard',
  residents: 'Residents',
  medicines: 'Medicines',
  prescriptions: 'Prescriptions',
  schedule: 'Medication Schedule',
  operations: 'Care Operations',
  access: 'Access',
  settings: 'Settings',
};

function TopBar({ page }) {
  const now = new Date();
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening';
  return (
    <div className="topbar">
      <div>
        <span className="topbar-title">{PAGE_TITLES[page] || page}</span>
        {page === 'dashboard' && <span className="topbar-breadcrumb">— {greeting}</span>}
      </div>
      <div className="topbar-actions">
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          {now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
        </span>
      </div>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════
   Reusable: Modal
   ══════════════════════════════════════════════════════════════ */
function Modal({ title, onClose, children, footer }) {
  useEffect(() => {
    const h = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════
   Dashboard Page
   ══════════════════════════════════════════════════════════════ */
function DashboardPage({ user, setPage }) {
  const [stats, setStats] = useState({ residents: null, medicines: null, prescriptions: null, health: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [residents, medicines, prescriptions, health] = await Promise.all([
        api.getResidents(),
        api.getMedicines(),
        api.getPrescriptions(),
        api.getHealth(),
      ]);
        if (!cancelled) {
          setStats({ residents, medicines, prescriptions, health });
          setError('');
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const activePrescriptions = useMemo(() =>
    (stats.prescriptions || []).filter(p => p.status === 'active'),
    [stats.prescriptions]
  );

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;

  const dashboardCopy = {
    admin: ['Overview', 'Facility operations and resident care at a glance'],
    doctor: ['Clinical Dashboard', 'Your assigned residents and active prescriptions'],
    caretaker: ['Care Dashboard', 'Residents assigned to your care'],
    resident: ['My Medication Dashboard', 'Your resident records and medication plan'],
    family_member: ['Shared Care Dashboard', 'Residents who have granted you access'],
  }[user.role] || ['Dashboard', 'CareMeds overview'];
  const residentCountLabel = {
    admin: 'Active Residents',
    doctor: 'Assigned Residents',
    caretaker: 'Assigned Residents',
    resident: 'Your Resident Profile',
    family_member: 'Linked Residents',
  }[user.role] || 'Residents';

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">{dashboardCopy[0]}</h1>
          <p className="page-subtitle">{dashboardCopy[1]}</p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      <div className="stats-grid stagger-children">
        <div className="stat-card" onClick={() => setPage('residents')} style={{ cursor: 'pointer' }}>
          <div className="stat-icon green">👥</div>
          <div>
            <div className="stat-value">{stats.residents?.length ?? '—'}</div>
            <div className="stat-label">{residentCountLabel}</div>
          </div>
        </div>
        <div className="stat-card" onClick={() => setPage('medicines')} style={{ cursor: 'pointer' }}>
          <div className="stat-icon blue">💊</div>
          <div>
            <div className="stat-value">{stats.medicines?.length ?? '—'}</div>
            <div className="stat-label">Medicines</div>
          </div>
        </div>
        <div className="stat-card" onClick={() => setPage('prescriptions')} style={{ cursor: 'pointer' }}>
          <div className="stat-icon orange">📋</div>
          <div>
            <div className="stat-value">{activePrescriptions.length}</div>
            <div className="stat-label">Active Prescriptions</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">❤️</div>
          <div>
            <div className="stat-value" style={{ color: stats.health?.status === 'ok' ? 'var(--color-success)' : 'var(--color-danger)' }}>
              {stats.health?.status === 'ok' ? 'Online' : 'Offline'}
            </div>
            <div className="stat-label">System Health</div>
          </div>
        </div>
      </div>

      {/* Recent Prescriptions */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Prescriptions</h3>
          <button className="btn btn-ghost btn-sm" onClick={() => setPage('prescriptions')}>View all →</button>
        </div>
        {stats.prescriptions && stats.prescriptions.length > 0 ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Medicine</th>
                  <th>Dosage</th>
                  <th>Frequency</th>
                  <th>Status</th>
                  <th>Start Date</th>
                </tr>
              </thead>
              <tbody>
                {stats.prescriptions.slice(0, 5).map(p => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 500 }}>{p.medicine_id?.slice(0, 8)}…</td>
                    <td>{p.dosage}</td>
                    <td>{p.frequency}</td>
                    <td><span className={`badge badge-${p.status}`}><span className="badge-dot" />{p.status}</span></td>
                    <td>{p.start_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3>No prescriptions yet</h3>
            <p>Prescriptions will appear here once created by a doctor</p>
          </div>
        )}
      </div>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════
   Residents Page
   ══════════════════════════════════════════════════════════════ */
function ResidentsPage({ user }) {
  const [residents, setResidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedResident, setSelectedResident] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setResidents(await api.getResidents()); setError(''); } catch (e) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return residents;
    const q = search.toLowerCase();
    return residents.filter(r => r.full_name?.toLowerCase().includes(q) || r.room_number?.toLowerCase().includes(q));
  }, [residents, search]);

  const isAdmin = user.role === 'admin';

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Residents</h1>
          <p className="page-subtitle">{residents.length} total residents</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
          <div className="search-bar">
            {icons.search}
            <input id="residents-search" placeholder="Search residents…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          {isAdmin && <button id="btn-add-resident" className="btn btn-primary" onClick={() => setShowCreate(true)}>{icons.plus} Add Resident</button>}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? <div className="loading-spinner"><div className="spinner" /></div> : (
        <div className="card">
          {filtered.length > 0 ? (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Room</th>
                    <th>Date of Birth</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(r => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.full_name}</td>
                      <td>{r.room_number || '—'}</td>
                      <td>{r.dob || '—'}</td>
                      <td><span className={`badge ${r.is_active ? 'badge-active' : 'badge-expired'}`}><span className="badge-dot" />{r.is_active ? 'Active' : 'Inactive'}</span></td>
                      <td>
                        <button className="btn btn-ghost btn-sm" onClick={() => setSelectedResident(r)}>View</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">👥</div>
              <h3>{search ? 'No results found' : 'No residents yet'}</h3>
              <p>{search ? 'Try a different search term' : 'Add your first resident to get started'}</p>
              {isAdmin && !search && <button className="btn btn-primary" onClick={() => setShowCreate(true)}>{icons.plus} Add Resident</button>}
            </div>
          )}
        </div>
      )}

      {showCreate && <ResidentCreateModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />}
      {selectedResident && <ResidentDetailModal resident={selectedResident} onClose={() => setSelectedResident(null)} />}
    </div>
  );
}

function ResidentCreateModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ full_name: '', dob: '', room_number: '', emergency_contact: '', allergies: '', care_notes: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const body = { ...form };
      if (!body.dob) delete body.dob;
      await api.createResident(body);
      onCreated();
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Modal title="Add New Resident" onClose={onClose} footer={
      <><button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="create-resident-form" disabled={loading}>{loading ? 'Saving…' : 'Save Resident'}</button></>
    }>
      {error && <div className="alert alert-error">{error}</div>}
      <form id="create-resident-form" onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Full Name *</label>
          <input className="form-input" value={form.full_name} onChange={e => upd('full_name', e.target.value)} required placeholder="e.g. John Smith" />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Date of Birth</label>
            <input className="form-input" type="date" value={form.dob} onChange={e => upd('dob', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Room Number</label>
            <input className="form-input" value={form.room_number} onChange={e => upd('room_number', e.target.value)} placeholder="e.g. A-101" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Emergency Contact</label>
          <input className="form-input" value={form.emergency_contact} onChange={e => upd('emergency_contact', e.target.value)} placeholder="Name, Phone" />
        </div>
        <div className="form-group">
          <label className="form-label">Known Allergies</label>
          <textarea className="form-textarea" value={form.allergies} onChange={e => upd('allergies', e.target.value)} placeholder="List any known allergies…" />
        </div>
        <div className="form-group">
          <label className="form-label">Care Notes</label>
          <textarea className="form-textarea" value={form.care_notes} onChange={e => upd('care_notes', e.target.value)} placeholder="Special care instructions…" />
        </div>
      </form>
    </Modal>
  );
}

function ResidentDetailModal({ resident, onClose }) {
  return (
    <Modal title="Resident Details" onClose={onClose}>
      <div className="detail-grid">
        <div className="detail-item"><label>Full Name</label><span>{resident.full_name}</span></div>
        <div className="detail-item"><label>Room Number</label><span>{resident.room_number || '—'}</span></div>
        <div className="detail-item"><label>Date of Birth</label><span>{resident.dob || '—'}</span></div>
        <div className="detail-item"><label>Status</label><span className={`badge ${resident.is_active ? 'badge-active' : 'badge-expired'}`}><span className="badge-dot" />{resident.is_active ? 'Active' : 'Inactive'}</span></div>
        <div className="detail-item" style={{ gridColumn: '1/-1' }}><label>Emergency Contact</label><p>{resident.emergency_contact || '—'}</p></div>
        <div className="detail-item" style={{ gridColumn: '1/-1' }}><label>Allergies</label><p>{resident.allergies || 'None listed'}</p></div>
        <div className="detail-item" style={{ gridColumn: '1/-1' }}><label>Care Notes</label><p>{resident.care_notes || 'None'}</p></div>
      </div>
    </Modal>
  );
}


/* ══════════════════════════════════════════════════════════════
   Medicines Page
   ══════════════════════════════════════════════════════════════ */
function MedicinesPage({ user }) {
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setMedicines(await api.getMedicines()); setError(''); } catch (e) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return medicines;
    const q = search.toLowerCase();
    return medicines.filter(m => m.name?.toLowerCase().includes(q) || m.manufacturer?.toLowerCase().includes(q));
  }, [medicines, search]);

  const canCreate = ['admin', 'doctor'].includes(user.role);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Medicines</h1>
          <p className="page-subtitle">{medicines.length} in catalog</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
          <div className="search-bar">
            {icons.search}
            <input id="medicines-search" placeholder="Search medicines…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          {canCreate && <button id="btn-add-medicine" className="btn btn-primary" onClick={() => setShowCreate(true)}>{icons.plus} Add Medicine</button>}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? <div className="loading-spinner"><div className="spinner" /></div> : (
        <div className="card">
          {filtered.length > 0 ? (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Strength</th>
                    <th>Form</th>
                    <th>Manufacturer</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(m => (
                    <tr key={m.id}>
                      <td style={{ fontWeight: 600 }}>{m.name}</td>
                      <td>{m.strength || '—'}</td>
                      <td>{m.form || '—'}</td>
                      <td>{m.manufacturer || '—'}</td>
                      <td><span className={`badge ${m.is_active ? 'badge-active' : 'badge-expired'}`}><span className="badge-dot" />{m.is_active ? 'Active' : 'Inactive'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">💊</div>
              <h3>{search ? 'No results found' : 'No medicines yet'}</h3>
              <p>{search ? 'Try a different search term' : 'Add medicines to the catalog to begin'}</p>
              {canCreate && !search && <button className="btn btn-primary" onClick={() => setShowCreate(true)}>{icons.plus} Add Medicine</button>}
            </div>
          )}
        </div>
      )}

      {showCreate && <MedicineCreateModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />}
    </div>
  );
}

function MedicineCreateModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', strength: '', form: '', manufacturer: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.createMedicine(form);
      onCreated();
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Modal title="Add New Medicine" onClose={onClose} footer={
      <><button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="create-medicine-form" disabled={loading}>{loading ? 'Saving…' : 'Save Medicine'}</button></>
    }>
      {error && <div className="alert alert-error">{error}</div>}
      <form id="create-medicine-form" onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Medicine Name *</label>
          <input className="form-input" value={form.name} onChange={e => upd('name', e.target.value)} required placeholder="e.g. Metformin" />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Strength</label>
            <input className="form-input" value={form.strength} onChange={e => upd('strength', e.target.value)} placeholder="e.g. 500mg" />
          </div>
          <div className="form-group">
            <label className="form-label">Form</label>
            <input className="form-input" value={form.form} onChange={e => upd('form', e.target.value)} placeholder="e.g. Tablet, Syrup" />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Manufacturer</label>
          <input className="form-input" value={form.manufacturer} onChange={e => upd('manufacturer', e.target.value)} placeholder="e.g. Sun Pharma" />
        </div>
      </form>
    </Modal>
  );
}


/* ══════════════════════════════════════════════════════════════
   Prescriptions Page
   ══════════════════════════════════════════════════════════════ */
function PrescriptionsPage({ user }) {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState('all');
  const [editingPrescription, setEditingPrescription] = useState(null);
  const [discontinuingPrescription, setDiscontinuingPrescription] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setPrescriptions(await api.getPrescriptions()); setError(''); } catch (e) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    let list = prescriptions;
    if (filter !== 'all') list = list.filter(p => p.status === filter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(p => p.dosage?.toLowerCase().includes(q) || p.frequency?.toLowerCase().includes(q));
    }
    return list;
  }, [prescriptions, search, filter]);

  const isDoctor = user.role === 'doctor';

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Prescriptions</h1>
          <p className="page-subtitle">{prescriptions.length} total prescriptions</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
          <div className="search-bar">
            {icons.search}
            <input id="prescriptions-search" placeholder="Search prescriptions…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          {isDoctor && <button id="btn-add-prescription" className="btn btn-primary" onClick={() => setShowCreate(true)}>{icons.plus} New Prescription</button>}
        </div>
      </div>

      {/* Status filter tabs */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-5)' }}>
        {['all', 'active', 'on_hold', 'discontinued', 'expired'].map(f => (
          <button key={f} className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter(f)} style={{ textTransform: 'capitalize' }}>
            {f === 'all' ? 'All' : f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? <div className="loading-spinner"><div className="spinner" /></div> : (
        <div className="card">
          {filtered.length > 0 ? (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Dosage</th>
                    <th>Route</th>
                    <th>Frequency</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Status</th>
                    {isDoctor && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(p => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600 }}>{p.dosage}</td>
                      <td>{p.route || '—'}</td>
                      <td>{p.frequency}</td>
                      <td>{p.start_date}</td>
                      <td>{p.end_date || '—'}</td>
                      <td><span className={`badge badge-${p.status}`}><span className="badge-dot" />{p.status?.replace('_', ' ')}</span></td>
                      {isDoctor && (
                        <td>
                          {p.doctor_id === user.id && p.status !== 'discontinued' ? (
                            <>
                              <button className="btn btn-ghost btn-sm" onClick={() => setEditingPrescription(p)}>Edit</button>
                              <button className="btn btn-ghost btn-sm" onClick={() => setDiscontinuingPrescription(p)}>Discontinue</button>
                            </>
                          ) : '—'}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <h3>{search || filter !== 'all' ? 'No matching prescriptions' : 'No prescriptions yet'}</h3>
              <p>{search || filter !== 'all' ? 'Try adjusting your filters' : 'Prescriptions will appear here once created'}</p>
            </div>
          )}
        </div>
      )}

      {showCreate && <PrescriptionCreateModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />}
      {editingPrescription && (
        <PrescriptionEditModal
          prescription={editingPrescription}
          onClose={() => setEditingPrescription(null)}
          onSaved={() => { setEditingPrescription(null); load(); }}
        />
      )}
      {discontinuingPrescription && (
        <PrescriptionDiscontinueModal
          prescription={discontinuingPrescription}
          onClose={() => setDiscontinuingPrescription(null)}
          onSaved={() => { setDiscontinuingPrescription(null); load(); }}
        />
      )}
    </div>
  );
}

function DoseSchedulePage({ user }) {
  const [doses, setDoses] = useState([]);
  const [selectedDate, setSelectedDate] = useState(() => new Date().toLocaleDateString('en-CA'));
  const [selectedDose, setSelectedDose] = useState(null);
  const [outcome, setOutcome] = useState('administered');
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDoses(await api.getDoses(selectedDate));
      setError('');
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => { load(); }, [load]);

  const saveOutcome = async event => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.recordDoseOutcome(selectedDose.id, {
        status: outcome,
        reason: reason.trim() || null,
        notes: notes.trim() || null,
      });
      setSelectedDose(null);
      setReason('');
      setNotes('');
      setMessage('Dose outcome recorded.');
      await load();
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  const acknowledge = async dose => {
    setError('');
    setMessage('');
    try {
      await api.acknowledgeDose(dose.id);
      setMessage('Reminder acknowledged. This does not record medication administration.');
      await load();
    } catch (ackError) {
      setError(ackError.message);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Medication Schedule</h1>
          <p className="page-subtitle">Scheduled doses and recorded outcomes</p>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="dose-date">Schedule date</label>
          <input id="dose-date" className="form-input" type="date" value={selectedDate} onChange={event => setSelectedDate(event.target.value)} />
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}
      {loading ? <div className="loading-spinner"><div className="spinner" /></div> : (
        <div className="card">
          {doses.length ? (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Time</th><th>Medicine</th><th>Dosage</th><th>State</th><th>Instructions</th><th>Action</th></tr></thead>
                <tbody>
                  {doses.map(dose => (
                    <tr key={dose.id}>
                      <td>{dose.scheduled_local_time} ({dose.timezone})</td>
                      <td>{dose.medicine_name}</td>
                      <td>{dose.dosage}{dose.route ? ` · ${dose.route}` : ''}</td>
                      <td><span className={`badge badge-${dose.timeliness}`}><span className="badge-dot" />{dose.timeliness.replaceAll('_', ' ')}</span>{dose.acknowledged_at && <div>Reminder acknowledged</div>}</td>
                      <td>{dose.instructions || '—'}{dose.outcome_reason && <div>Reason: {dose.outcome_reason}</div>}</td>
                      <td>
                        {user.role === 'caretaker' && dose.status === 'scheduled' && dose.timeliness !== 'scheduled' && (
                          <button className="btn btn-primary btn-sm" onClick={() => { setSelectedDose(dose); setOutcome('administered'); }}>
                            Record outcome
                          </button>
                        )}
                        {user.role === 'resident' && dose.status === 'scheduled' && !dose.acknowledged_at && (
                          <button className="btn btn-secondary btn-sm" onClick={() => acknowledge(dose)}>Acknowledge reminder</button>
                        )}
                        {user.role !== 'caretaker' && user.role !== 'resident' && '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="empty-state"><h3>No doses scheduled</h3><p>No active prescription schedules are configured for this date.</p></div>}
        </div>
      )}
      {selectedDose && (
        <Modal title={`Record ${selectedDose.medicine_name}`} onClose={() => setSelectedDose(null)} footer={
          <><button className="btn btn-secondary" onClick={() => setSelectedDose(null)}>Cancel</button>
            <button className="btn btn-primary" form="dose-outcome-form" disabled={saving || (outcome !== 'administered' && !reason.trim())}>{saving ? 'Saving…' : 'Save outcome'}</button></>
        }>
          {error && <div className="alert alert-error">{error}</div>}
          <form id="dose-outcome-form" onSubmit={saveOutcome}>
            <div className="form-group">
              <label className="form-label" htmlFor="dose-outcome">Outcome</label>
              <select id="dose-outcome" className="form-select" value={outcome} onChange={event => setOutcome(event.target.value)}>
                <option value="administered">Administered</option>
                <option value="refused">Refused</option>
                <option value="withheld">Withheld</option>
                <option value="not_administered">Not administered</option>
                <option value="unable_to_confirm">Unable to confirm</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="dose-reason">Reason {outcome !== 'administered' ? '*' : '(optional)'}</label>
              <textarea id="dose-reason" className="form-textarea" value={reason} onChange={event => setReason(event.target.value)} required={outcome !== 'administered'} />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="dose-notes">Notes</label>
              <textarea id="dose-notes" className="form-textarea" value={notes} onChange={event => setNotes(event.target.value)} />
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

function OperationsPage({ user }) {
  const staff = ['admin', 'doctor', 'caretaker'].includes(user.role);
  const canManageStock = ['admin', 'caretaker'].includes(user.role);
  const [data, setData] = useState({
    notifications: [], inventory: [], transactions: [], escalations: [],
    contacts: [], residents: [], handovers: [], audit: [], analytics: null,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [stockInForm, setStockInForm] = useState({ medicine_id: '', lot_code: '', expires_on: '', quantity: '', reason: '' });
  const [stockOutForm, setStockOutForm] = useState({ batch_id: '', quantity: '', reason: '' });
  const [contactForm, setContactForm] = useState({ resident_id: '', message: '' });
  const [contactReply, setContactReply] = useState({ id: '', status: 'received', response: '' });
  const [resolution, setResolution] = useState({ id: '', notes: '' });
  const [handoverForm, setHandoverForm] = useState({
    resident_id: '', incoming_caretaker_id: '',
    shift_started_at: localDateTimeInput(new Date()),
    shift_ended_at: localDateTimeInput(new Date(Date.now() + 8 * 60 * 60 * 1000)),
    notes: '',
  });
  const [eligibleCaretakers, setEligibleCaretakers] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const jobs = {
        notifications: api.getNotifications(),
        analytics: api.getAdherence(),
      };
      if (staff) {
        jobs.contacts = api.getFamilyContactRequests();
        jobs.inventory = api.getInventory();
        jobs.transactions = api.getInventoryTransactions();
        jobs.escalations = api.getEscalations();
        if (user.role === 'admin' || user.role === 'caretaker') jobs.handovers = api.getHandovers();
        if (user.role === 'admin') jobs.audit = api.getAuditLogs();
      }
      if (user.role === 'family_member') {
        jobs.contacts = api.getFamilyContactRequests();
        jobs.residents = api.getFamilyLinks();
      }
      if (user.role === 'caretaker') jobs.residents = api.getResidents();
      const entries = await Promise.all(Object.entries(jobs).map(async ([key, promise]) => [key, await promise]));
      setData(previous => ({ ...previous, ...Object.fromEntries(entries) }));
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [staff, user.id, user.role]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (user.role !== 'caretaker' || !handoverForm.resident_id) {
      setEligibleCaretakers([]);
      return;
    }
    let cancelled = false;
    api.getEligibleHandoverCaretakers(handoverForm.resident_id)
      .then(items => { if (!cancelled) setEligibleCaretakers(items.filter(item => item.id !== user.id)); })
      .catch(loadError => { if (!cancelled) setError(loadError.message); });
    return () => { cancelled = true; };
  }, [handoverForm.resident_id, user.id, user.role]);

  const perform = async (action, successText) => {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      await action();
      setMessage(successText);
      await load();
    } catch (actionError) {
      setError(actionError.message);
    } finally {
      setSaving(false);
    }
  };

  const saveStockIn = event => {
    event.preventDefault();
    perform(() => api.stockIn({
      ...stockInForm,
      quantity: Number(stockInForm.quantity),
      reason: stockInForm.reason.trim() || null,
    }), 'Stock receipt recorded.');
  };
  const saveStockOut = event => {
    event.preventDefault();
    perform(() => api.stockOut(stockOutForm.batch_id, {
      quantity: Number(stockOutForm.quantity),
      reason: stockOutForm.reason.trim(),
    }), 'Stock issue recorded.');
  };
  const saveContact = event => {
    event.preventDefault();
    perform(async () => {
      await api.createFamilyContactRequest({
        ...contactForm,
        message: contactForm.message.trim(),
      });
      setContactForm(form => ({ ...form, message: '' }));
    }, 'Your contact request was sent to the care team.');
  };
  const sendContactReply = event => {
    event.preventDefault();
    perform(async () => {
      await api.respondToFamilyContactRequest(contactReply.id, {
        status: contactReply.status,
        response: contactReply.response.trim(),
      });
      setContactReply({ id: '', status: 'received', response: '' });
    }, 'Contact request updated.');
  };
  const resolveEscalation = event => {
    event.preventDefault();
    perform(async () => {
      await api.resolveEscalation(resolution.id, resolution.notes.trim());
      setResolution({ id: '', notes: '' });
    }, 'Escalation resolved.');
  };
  const saveHandover = event => {
    event.preventDefault();
    perform(async () => {
      await api.createHandover({
        resident_id: handoverForm.resident_id,
        incoming_caretaker_id: handoverForm.incoming_caretaker_id,
        shift_started_at: new Date(handoverForm.shift_started_at).toISOString(),
        shift_ended_at: new Date(handoverForm.shift_ended_at).toISOString(),
        notes: handoverForm.notes.trim(),
      });
      setHandoverForm(form => ({ ...form, notes: '', incoming_caretaker_id: '' }));
    }, 'Shift handover created.');
  };

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;
  const familyResidentLinks = data.residents;
  const medicineOptions = data.inventory;
  const batches = data.inventory.flatMap(medicine => medicine.batches.map(batch => ({
    ...batch,
    medicine_id: medicine.medicine_id,
    medicine_name: medicine.medicine_name,
  })));

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div><h1 className="page-title">Care Operations</h1><p className="page-subtitle">Reminders, medication stock, family communication, and handovers</p></div>
        <button className="btn btn-secondary" onClick={load}>Refresh</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}

      <section className="card">
        <div className="card-header"><h2 className="card-title">Adherence summary</h2></div>
        {data.analytics && <>
          <p>Period: {data.analytics.start_date} to {data.analytics.end_date}</p>
          <p>Rate: {data.analytics.adherence_rate_percent === null ? 'Not available' : `${data.analytics.adherence_rate_percent}%`} ({data.analytics.counts.administered} administered of {data.analytics.total_doses} occurred doses)</p>
          <p>Unresolved: {data.analytics.counts.unresolved}; unable to confirm: {data.analytics.counts.unable_to_confirm}; cancelled: {data.analytics.cancelled_doses}</p>
          <small>{data.analytics.formula}</small>
        </>}
      </section>

      <section className="card">
        <div className="card-header"><h2 className="card-title">Notifications</h2></div>
        {data.notifications.length ? data.notifications.map(item => (
          <div className="operation-row" key={item.id}>
            <div><strong>{item.notification_type.replaceAll('_', ' ')}</strong><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString()}</small></div>
            {!item.read_at && <button className="btn btn-secondary btn-sm" disabled={saving} onClick={() => perform(() => api.acknowledgeNotification(item.id), 'Notification marked as read.')}>Mark read</button>}
          </div>
        )) : <p className="empty-state">No notifications.</p>}
      </section>

      {user.role === 'family_member' && (
        <section className="card">
          <div className="card-header"><h2 className="card-title">Contact the care team</h2></div>
          <form onSubmit={saveContact}>
            <div className="form-group">
              <label className="form-label" htmlFor="contact-resident">Linked resident</label>
              <select id="contact-resident" className="form-select" value={contactForm.resident_id} onChange={event => setContactForm(form => ({ ...form, resident_id: event.target.value }))} required>
                <option value="">Select resident…</option>
                {familyResidentLinks.map(link => <option key={link.resident_id} value={link.resident_id}>{link.resident_name || link.resident_id}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="contact-message">Message</label>
              <textarea id="contact-message" className="form-textarea" value={contactForm.message} onChange={event => setContactForm(form => ({ ...form, message: event.target.value }))} required maxLength={4000} />
            </div>
            <button className="btn btn-primary" disabled={saving || !contactForm.resident_id || !contactForm.message.trim()}>{saving ? 'Sending…' : 'Send request'}</button>
          </form>
        </section>
      )}

      {(staff || user.role === 'family_member') && (
        <section className="card">
          <div className="card-header"><h2 className="card-title">Family contact requests</h2></div>
          {data.contacts.length ? data.contacts.map(item => (
            <div className="operation-row" key={item.id}>
              <div><strong>{item.status.replaceAll('_', ' ')}</strong><p>{item.message}</p>{item.response && <p><strong>Care team:</strong> {item.response}</p>}<small>Resident: {item.resident_id}</small></div>
              {staff && item.status !== 'resolved' && (
                <button className="btn btn-secondary btn-sm" onClick={() => setContactReply({ id: item.id, status: item.status === 'pending' ? 'received' : 'resolved', response: item.response || '' })}>Respond</button>
              )}
            </div>
          )) : <p className="empty-state">No contact requests.</p>}
          {staff && contactReply.id && (
            <form onSubmit={sendContactReply}>
              <div className="form-group">
                <label className="form-label" htmlFor="contact-response">Care team response</label>
                <textarea id="contact-response" className="form-textarea" value={contactReply.response} onChange={event => setContactReply(form => ({ ...form, response: event.target.value }))} required maxLength={4000} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="contact-status">Status</label>
                <select id="contact-status" className="form-select" value={contactReply.status} onChange={event => setContactReply(form => ({ ...form, status: event.target.value }))}>
                  <option value="received">Received</option><option value="resolved">Resolved</option>
                </select>
              </div>
              <button className="btn btn-primary" disabled={saving || !contactReply.response.trim()}>Save response</button>
            </form>
          )}
        </section>
      )}

      {staff && (
        <section className="card">
          <div className="card-header"><h2 className="card-title">Medication inventory</h2></div>
          {data.inventory.length ? (
            <div className="table-wrapper"><table className="data-table">
              <thead><tr><th>Medicine</th><th>Available</th><th>Reorder level</th><th>Stock status</th><th>Lots / expiry</th></tr></thead>
              <tbody>{data.inventory.map(item => <tr key={item.medicine_id}>
                <td>{item.medicine_name}</td><td>{item.available_quantity} available ({item.total_quantity} total)</td><td>{item.reorder_level}</td>
                <td>{item.low_stock ? 'Reorder' : 'In stock'}</td>
                <td>{item.batches.map(batch => `${batch.lot_code}: ${batch.quantity_remaining} (${batch.expired ? 'expired' : batch.expires_on}${batch.expiring_soon ? ', expiring soon' : ''})`).join('; ') || 'No batches'}</td>
              </tr>)}</tbody>
            </table></div>
          ) : <p className="empty-state">No medicines in the active catalog.</p>}
          {canManageStock && (
            <div className="form-row">
              <form onSubmit={saveStockIn}>
                <h3>Receive stock</h3>
                <div className="form-group"><label className="form-label" htmlFor="stock-medicine">Medicine</label><select id="stock-medicine" className="form-select" value={stockInForm.medicine_id} onChange={event => setStockInForm(form => ({ ...form, medicine_id: event.target.value }))} required><option value="">Select medicine…</option>{medicineOptions.map(item => <option key={item.medicine_id} value={item.medicine_id}>{item.medicine_name}</option>)}</select></div>
                <div className="form-group"><label className="form-label" htmlFor="stock-lot">Lot code</label><input id="stock-lot" className="form-input" value={stockInForm.lot_code} onChange={event => setStockInForm(form => ({ ...form, lot_code: event.target.value }))} required /></div>
                <div className="form-row"><div className="form-group"><label className="form-label" htmlFor="stock-expiry">Expiry</label><input id="stock-expiry" className="form-input" type="date" value={stockInForm.expires_on} onChange={event => setStockInForm(form => ({ ...form, expires_on: event.target.value }))} required /></div><div className="form-group"><label className="form-label" htmlFor="stock-quantity">Quantity</label><input id="stock-quantity" className="form-input" type="number" min="1" value={stockInForm.quantity} onChange={event => setStockInForm(form => ({ ...form, quantity: event.target.value }))} required /></div></div>
                <div className="form-group"><label className="form-label" htmlFor="stock-reason">Reason</label><input id="stock-reason" className="form-input" value={stockInForm.reason} onChange={event => setStockInForm(form => ({ ...form, reason: event.target.value }))} /></div>
                <button className="btn btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Receive stock'}</button>
              </form>
              <form onSubmit={saveStockOut}>
                <h3>Issue stock</h3>
                <div className="form-group"><label className="form-label" htmlFor="stock-batch">Batch</label><select id="stock-batch" className="form-select" value={stockOutForm.batch_id} onChange={event => setStockOutForm(form => ({ ...form, batch_id: event.target.value }))} required><option value="">Select batch…</option>{batches.filter(batch => batch.quantity_remaining > 0 && !batch.expired).map(batch => <option key={batch.id} value={batch.id}>{batch.medicine_name} · {batch.lot_code} · {batch.quantity_remaining}</option>)}</select></div>
                <div className="form-group"><label className="form-label" htmlFor="issue-quantity">Quantity</label><input id="issue-quantity" className="form-input" type="number" min="1" value={stockOutForm.quantity} onChange={event => setStockOutForm(form => ({ ...form, quantity: event.target.value }))} required /></div>
                <div className="form-group"><label className="form-label" htmlFor="issue-reason">Reason</label><input id="issue-reason" className="form-input" value={stockOutForm.reason} onChange={event => setStockOutForm(form => ({ ...form, reason: event.target.value }))} required /></div>
                <button className="btn btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Issue stock'}</button>
              </form>
            </div>
          )}
          <h3>Recent stock transactions</h3>
          {data.transactions.length ? <ul>{data.transactions.map(item => <li key={item.id}>{item.transaction_type.replace('_', ' ')} {item.quantity}; balance {item.quantity_after}; {item.reason || 'no reason recorded'}</li>)}</ul> : <p>No stock transactions.</p>}
        </section>
      )}

      {staff && (
        <section className="card">
          <div className="card-header"><h2 className="card-title">Overdue dose escalations</h2></div>
          {data.escalations.length ? data.escalations.map(item => (
            <div className="operation-row" key={item.id}>
              <div><strong>{item.status}</strong><p>Dose occurrence: {item.dose_occurrence_id}</p><small>{new Date(item.created_at).toLocaleString()}</small></div>
              {item.status === 'open' && <button className="btn btn-secondary btn-sm" onClick={() => setResolution({ id: item.id, notes: '' })}>Resolve</button>}
            </div>
          )) : <p className="empty-state">No open escalations.</p>}
          {resolution.id && <form onSubmit={resolveEscalation}>
            <div className="form-group"><label className="form-label" htmlFor="escalation-notes">Resolution notes</label><textarea id="escalation-notes" className="form-textarea" value={resolution.notes} onChange={event => setResolution(form => ({ ...form, notes: event.target.value }))} required /></div>
            <button className="btn btn-primary" disabled={saving || !resolution.notes.trim()}>Resolve escalation</button>
          </form>}
        </section>
      )}

      {user.role === 'caretaker' && (
        <section className="card">
          <div className="card-header"><h2 className="card-title">Shift handover</h2></div>
          <form onSubmit={saveHandover}>
            <div className="form-row">
              <div className="form-group"><label className="form-label" htmlFor="handover-resident">Resident</label><select id="handover-resident" className="form-select" value={handoverForm.resident_id} onChange={event => setHandoverForm(form => ({ ...form, resident_id: event.target.value, incoming_caretaker_id: '' }))} required><option value="">Select assigned resident…</option>{data.residents.map(item => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></div>
              <div className="form-group"><label className="form-label" htmlFor="handover-incoming">Incoming caretaker</label><select id="handover-incoming" className="form-select" value={handoverForm.incoming_caretaker_id} onChange={event => setHandoverForm(form => ({ ...form, incoming_caretaker_id: event.target.value }))} required><option value="">Select caretaker…</option>{eligibleCaretakers.map(item => <option key={item.id} value={item.id}>{item.full_name || item.username}</option>)}</select></div>
            </div>
            <div className="form-row"><div className="form-group"><label className="form-label" htmlFor="shift-start">Shift starts</label><input id="shift-start" className="form-input" type="datetime-local" value={handoverForm.shift_started_at} onChange={event => setHandoverForm(form => ({ ...form, shift_started_at: event.target.value }))} required /></div><div className="form-group"><label className="form-label" htmlFor="shift-end">Shift ends</label><input id="shift-end" className="form-input" type="datetime-local" value={handoverForm.shift_ended_at} onChange={event => setHandoverForm(form => ({ ...form, shift_ended_at: event.target.value }))} required /></div></div>
            <div className="form-group"><label className="form-label" htmlFor="handover-notes">Handover notes</label><textarea id="handover-notes" className="form-textarea" value={handoverForm.notes} onChange={event => setHandoverForm(form => ({ ...form, notes: event.target.value }))} required maxLength={4000} /></div>
            <button className="btn btn-primary" disabled={saving || !eligibleCaretakers.length}>{saving ? 'Saving…' : 'Create handover'}</button>
          </form>
          <h3>Recent handovers</h3>
          {data.handovers.length ? data.handovers.map(item => <div className="operation-row" key={item.id}>
            <div><strong>{item.acknowledged_at ? 'Acknowledged' : 'Awaiting acknowledgement'}</strong><p>{item.notes}</p><small>{new Date(item.shift_started_at).toLocaleString()} – {new Date(item.shift_ended_at).toLocaleString()}</small></div>
            {item.incoming_caretaker_id === user.id && !item.acknowledged_at && <button className="btn btn-secondary btn-sm" disabled={saving} onClick={() => perform(() => api.acknowledgeHandover(item.id), 'Handover acknowledged.')}>Acknowledge</button>}
          </div>) : <p className="empty-state">No handovers for your assigned residents.</p>}
        </section>
      )}

      {user.role === 'admin' && (
        <section className="card">
          <div className="card-header"><h2 className="card-title">Audit log</h2></div>
          {data.audit.length ? <div className="table-wrapper"><table className="data-table"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Resource</th><th>Details</th></tr></thead><tbody>{data.audit.map(item => <tr key={item.id}><td>{new Date(item.occurred_at).toLocaleString()}</td><td>{item.actor_id || 'system'}</td><td>{item.action}</td><td>{item.resource_type} {item.resource_id || ''}</td><td>{item.details || '—'}</td></tr>)}</tbody></table></div> : <p className="empty-state">No audit events.</p>}
        </section>
      )}
    </div>
  );
}

function localDateTimeInput(date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function PrescriptionCreateModal({ onClose, onCreated }) {
  const [residents, setResidents] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [form, setForm] = useState({ resident_id: '', medicine_id: '', dosage: '', route: '', frequency: '', scheduled_times: '09:00', timezone: 'UTC', instructions: '', start_date: '', end_date: '' });
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [residentList, medicineList] = await Promise.all([api.getResidents(), api.getMedicines()]);
        if (!cancelled) {
          setResidents(residentList);
          setMedicines(medicineList);
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setDataLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const body = { ...form };
      body.scheduled_times = form.scheduled_times.split(',').map(value => value.trim()).filter(Boolean);
      if (!body.end_date) delete body.end_date;
      await api.createPrescription(body);
      onCreated();
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Modal title="New Prescription" onClose={onClose} footer={
      <><button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="create-pres-form" disabled={loading || dataLoading || !!error}>{loading ? 'Saving…' : 'Create Prescription'}</button></>
    }>
      {error && <div className="alert alert-error">{error}</div>}
      {dataLoading ? <div className="loading-spinner"><div className="spinner" /></div> : (
        <form id="create-pres-form" onSubmit={submit}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Resident *</label>
              <select className="form-select" value={form.resident_id} onChange={e => upd('resident_id', e.target.value)} required>
                <option value="">Select resident…</option>
                {residents.map(r => <option key={r.id} value={r.id}>{r.full_name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Medicine *</label>
              <select className="form-select" value={form.medicine_id} onChange={e => upd('medicine_id', e.target.value)} required>
                <option value="">Select medicine…</option>
                {medicines.map(m => <option key={m.id} value={m.id}>{m.name} {m.strength || ''}</option>)}
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Dosage *</label>
              <input className="form-input" value={form.dosage} onChange={e => upd('dosage', e.target.value)} required placeholder="e.g. 1 tablet" />
            </div>
            <div className="form-group">
              <label className="form-label">Route</label>
              <input className="form-input" value={form.route} onChange={e => upd('route', e.target.value)} placeholder="e.g. Oral" />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Frequency *</label>
            <input className="form-input" value={form.frequency} onChange={e => upd('frequency', e.target.value)} required placeholder="e.g. Twice daily" />
          </div>
          <div className="form-group">
            <label className="form-label">Scheduled times (24-hour, comma-separated) *</label>
            <input className="form-input" value={form.scheduled_times} onChange={e => upd('scheduled_times', e.target.value)} required placeholder="08:00, 20:00" />
          </div>
          <div className="form-group">
            <label className="form-label">Time zone *</label>
            <input className="form-input" value={form.timezone} onChange={e => upd('timezone', e.target.value)} required placeholder="Asia/Kolkata" />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Start Date *</label>
              <input className="form-input" type="date" value={form.start_date} onChange={e => upd('start_date', e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">End Date</label>
              <input className="form-input" type="date" value={form.end_date} onChange={e => upd('end_date', e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Special Instructions</label>
            <textarea className="form-textarea" value={form.instructions} onChange={e => upd('instructions', e.target.value)} placeholder="Take after meals, avoid dairy…" />
          </div>
        </form>
      )}
    </Modal>
  );
}

function PrescriptionEditModal({ prescription, onClose, onSaved }) {
  const [form, setForm] = useState({
    dosage: prescription.dosage,
    route: prescription.route || '',
    frequency: prescription.frequency,
    scheduled_times: prescription.scheduled_times.join(', '),
    timezone: prescription.timezone,
    instructions: prescription.instructions || '',
    start_date: prescription.start_date,
    end_date: prescription.end_date || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const update = (key, value) => setForm(current => ({ ...current, [key]: value }));

  const submit = async event => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const body = { ...form };
      body.scheduled_times = form.scheduled_times.split(',').map(value => value.trim()).filter(Boolean);
      if (!body.end_date) delete body.end_date;
      await api.updatePrescription(prescription.id, body);
      onSaved();
    } catch (updateError) {
      setError(updateError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Edit Prescription" onClose={onClose} footer={
      <><button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="edit-prescription-form" disabled={loading}>{loading ? 'Saving…' : 'Save Changes'}</button></>
    }>
      {error && <div className="alert alert-error">{error}</div>}
      <form id="edit-prescription-form" onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Dosage *</label>
          <input className="form-input" value={form.dosage} onChange={e => update('dosage', e.target.value)} required />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Route</label>
            <input className="form-input" value={form.route} onChange={e => update('route', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Frequency *</label>
            <input className="form-input" value={form.frequency} onChange={e => update('frequency', e.target.value)} required />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Scheduled times (24-hour, comma-separated) *</label>
            <input className="form-input" value={form.scheduled_times} onChange={e => update('scheduled_times', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Time zone *</label>
            <input className="form-input" value={form.timezone} onChange={e => update('timezone', e.target.value)} required />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Start Date *</label>
            <input className="form-input" type="date" value={form.start_date} onChange={e => update('start_date', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">End Date</label>
            <input className="form-input" type="date" value={form.end_date} onChange={e => update('end_date', e.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Special Instructions</label>
          <textarea className="form-textarea" value={form.instructions} onChange={e => update('instructions', e.target.value)} />
        </div>
      </form>
    </Modal>
  );
}

function PrescriptionDiscontinueModal({ prescription, onClose, onSaved }) {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async event => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.discontinuePrescription(prescription.id, reason);
      onSaved();
    } catch (discontinueError) {
      setError(discontinueError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Discontinue Prescription" onClose={onClose} footer={
      <><button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="discontinue-prescription-form" disabled={loading || !reason.trim()}>{loading ? 'Saving…' : 'Confirm Discontinuation'}</button></>
    }>
      {error && <div className="alert alert-error">{error}</div>}
      <form id="discontinue-prescription-form" onSubmit={submit}>
        <div className="form-group">
          <label className="form-label" htmlFor="discontinuation-reason">Reason *</label>
          <textarea id="discontinuation-reason" className="form-textarea" value={reason} onChange={e => setReason(e.target.value)} required />
        </div>
      </form>
    </Modal>
  );
}


function AccessPage({ user }) {
  if (user.role === 'admin') return <AdminAccessManagement user={user} />;
  if (user.role === 'resident') return <ResidentConsentManagement />;
  if (user.role === 'family_member') return <FamilyLinkManagement />;
  return <div className="alert alert-error">Access management is not available for this role.</div>;
}

function AdminAccessManagement({ user }) {
  const [residents, setResidents] = useState([]);
  const [users, setUsers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [familyLinks, setFamilyLinks] = useState([]);
  const [residentId, setResidentId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [caretakerId, setCaretakerId] = useState('');
  const [newAccount, setNewAccount] = useState({
    username: '',
    password: '',
    full_name: '',
    phone: '',
    role: 'doctor',
  });
  const [creatingAccount, setCreatingAccount] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const doctors = users.filter(u => u.role === 'doctor');
  const caretakers = users.filter(u => u.role === 'caretaker');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [residentList, userList, assignmentList, familyLinkList, accountList] = await Promise.all([
        api.getResidents(),
        api.getAssignmentUsers(),
        api.getAssignments(),
        api.getFamilyLinks(),
        api.getUsers(),
      ]);
      setResidents(residentList);
      setUsers(userList);
      setAssignments(assignmentList);
      setFamilyLinks(familyLinkList);
      setAccounts(accountList);
      setError('');
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const assign = async (role, userId) => {
    setMessage('');
    setError('');
    try {
      if (role === 'doctor') await api.assignDoctor(residentId, userId);
      else await api.assignCaretaker(residentId, userId);
      setMessage(`${role === 'doctor' ? 'Doctor' : 'Caretaker'} assigned.`);
      await load();
    } catch (assignError) {
      setError(assignError.message);
    }
  };

  const unassign = async assignment => {
    setMessage('');
    setError('');
    try {
      if (assignment.role === 'doctor') await api.unassignDoctor(assignment.resident_id, assignment.user_id);
      else await api.unassignCaretaker(assignment.resident_id, assignment.user_id);
      setMessage(`${assignment.role === 'doctor' ? 'Doctor' : 'Caretaker'} assignment removed.`);
      await load();
    } catch (unassignError) {
      setError(unassignError.message);
    }
  };

  const revokeFamilyAccess = async link => {
    setMessage('');
    setError('');
    try {
      await api.revokeFamilyConsent(link.resident_id, link.family_member_id);
      setMessage('Family consent revoked.');
      await load();
    } catch (revokeError) {
      setError(revokeError.message);
    }
  };

  const updateAccount = async account => {
    setMessage('');
    setError('');
    try {
      await api.setUserActive(account.id, !account.is_active);
      setMessage(`${account.full_name || account.username} ${account.is_active ? 'deactivated' : 'reactivated'}.`);
      await load();
    } catch (updateError) {
      setError(updateError.message);
    }
  };

  const createAccount = async event => {
    event.preventDefault();
    setMessage('');
    setError('');
    setCreatingAccount(true);
    try {
      await api.createUser({
        username: newAccount.username.trim(),
        password: newAccount.password,
        full_name: newAccount.full_name.trim() || null,
        phone: newAccount.phone.trim() || null,
        role: newAccount.role,
      });
      setNewAccount({ username: '', password: '', full_name: '', phone: '', role: 'doctor' });
      setMessage('Account created. Share its credentials with the user through your organization’s approved secure channel.');
      await load();
    } catch (createError) {
      setError(createError.message);
    } finally {
      setCreatingAccount(false);
    }
  };

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;
  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Access Management</h1>
          <p className="page-subtitle">Assign clinical and care teams to residents</p>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}
      <div className="card">
        <div className="form-group">
          <label className="form-label" htmlFor="assignment-resident">Resident</label>
          <select id="assignment-resident" className="form-select" value={residentId} onChange={e => setResidentId(e.target.value)}>
            <option value="">Select resident…</option>
            {residents.filter(r => r.is_active).map(r => <option key={r.id} value={r.id}>{r.full_name}</option>)}
          </select>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="assignment-doctor">Assigned Doctor</label>
            <select id="assignment-doctor" className="form-select" value={doctorId} onChange={e => setDoctorId(e.target.value)}>
              <option value="">Select doctor…</option>
              {doctors.map(u => <option key={u.id} value={u.id}>{u.full_name || u.username}</option>)}
            </select>
            <button className="btn btn-primary" disabled={!residentId || !doctorId} onClick={() => assign('doctor', doctorId)}>Assign Doctor</button>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="assignment-caretaker">Assigned Caretaker</label>
            <select id="assignment-caretaker" className="form-select" value={caretakerId} onChange={e => setCaretakerId(e.target.value)}>
              <option value="">Select caretaker…</option>
              {caretakers.map(u => <option key={u.id} value={u.id}>{u.full_name || u.username}</option>)}
            </select>
            <button className="btn btn-primary" disabled={!residentId || !caretakerId} onClick={() => assign('caretaker', caretakerId)}>Assign Caretaker</button>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-header"><h3 className="card-title">Current assignments</h3></div>
        {assignments.length ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Resident</th><th>Staff account</th><th>Role</th><th>Status</th><th /></tr></thead>
              <tbody>
                {assignments.map((assignment, index) => (
                  <tr key={`${assignment.role}-${assignment.resident_id}-${assignment.user_id}-${index}`}>
                    <td>{residents.find(r => r.id === assignment.resident_id)?.full_name || assignment.resident_id}</td>
                    <td>{users.find(u => u.id === assignment.user_id)?.full_name || assignment.user_id}</td>
                    <td>{assignment.role}</td>
                    <td>{assignment.is_active ? 'Active' : 'Inactive'}</td>
                    <td>{assignment.is_active && <button className="btn btn-secondary btn-sm" onClick={() => unassign(assignment)}>Remove</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p>No staff assignments are recorded.</p>}
      </div>
      <div className="card">
        <div className="card-header"><h3 className="card-title">Family access and consent</h3></div>
        {familyLinks.length ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Resident</th><th>Family account</th><th>Status</th><th /></tr></thead>
              <tbody>
                {familyLinks.map((link, index) => (
                  <tr key={`${link.resident_id}-${link.family_member_id}-${index}`}>
                    <td>{link.resident_name}</td>
                    <td>{link.family_member_name}</td>
                    <td>{link.is_active && link.consent_granted ? 'Consent active' : 'No active consent'}</td>
                    <td>{link.is_active && link.consent_granted && <button className="btn btn-secondary btn-sm" onClick={() => revokeFamilyAccess(link)}>Revoke</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p>No family access links are recorded.</p>}
      </div>
      <div className="card">
        <div className="card-header"><h3 className="card-title">Create user account</h3></div>
        <form onSubmit={createAccount}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="new-account-username">Username</label>
              <input id="new-account-username" className="form-input" value={newAccount.username} onChange={event => setNewAccount(form => ({ ...form, username: event.target.value }))} autoComplete="off" maxLength={150} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="new-account-role">Role</label>
              <select id="new-account-role" className="form-select" value={newAccount.role} onChange={event => setNewAccount(form => ({ ...form, role: event.target.value }))}>
                <option value="doctor">Doctor</option>
                <option value="caretaker">Caretaker</option>
                <option value="resident">Resident</option>
                <option value="family_member">Family Member</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="new-account-name">Full name (optional)</label>
              <input id="new-account-name" className="form-input" value={newAccount.full_name} onChange={event => setNewAccount(form => ({ ...form, full_name: event.target.value }))} maxLength={255} />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="new-account-phone">Phone (optional)</label>
              <input id="new-account-phone" className="form-input" type="tel" value={newAccount.phone} onChange={event => setNewAccount(form => ({ ...form, phone: event.target.value }))} maxLength={50} />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="new-account-password">Temporary password</label>
            <input id="new-account-password" className="form-input" type="password" value={newAccount.password} onChange={event => setNewAccount(form => ({ ...form, password: event.target.value }))} autoComplete="new-password" minLength={12} maxLength={72} required />
            <p className="form-hint">Use at least 12 characters. Passwords must fit within 72 UTF-8 bytes.</p>
          </div>
          <button className="btn btn-primary" disabled={creatingAccount || !newAccount.username.trim() || newAccount.password.length < 12}>
            {creatingAccount ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      </div>
      <div className="card">
        <div className="card-header"><h3 className="card-title">User accounts</h3></div>
        {accounts.length ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Status</th><th /></tr></thead>
              <tbody>
                {accounts.map(account => (
                  <tr key={account.id}>
                    <td>{account.full_name || '—'}</td>
                    <td>{account.username}</td>
                    <td>{account.role}</td>
                    <td>{account.is_active ? 'Active' : 'Inactive'}</td>
                    <td>{account.id !== user?.id && (
                      <button className="btn btn-secondary btn-sm" onClick={() => updateAccount(account)}>
                        {account.is_active ? 'Deactivate' : 'Reactivate'}
                      </button>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p>No user accounts are recorded.</p>}
      </div>
    </div>
  );
}

function ResidentConsentManagement() {
  const [resident, setResident] = useState(null);
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const residents = await api.getResidents();
      const ownResident = residents[0];
      setResident(ownResident || null);
      if (ownResident) setLinks(await api.getFamilyConsentRequests(ownResident.id));
      else setLinks([]);
      setError('');
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const updateConsent = async (link, grant) => {
    setMessage('');
    setError('');
    try {
      if (!grant) {
        await api.revokeFamilyConsent(resident.id, link.family_member_id);
        setMessage('Family access revoked.');
      } else {
        const permissions = {
          can_view_profile: link.can_view_profile,
          can_view_prescriptions: link.can_view_prescriptions,
        };
        if (link.consent_granted) {
          await api.updateFamilyConsent(resident.id, link.family_member_id, permissions);
          setMessage('Family permissions saved.');
        } else {
          await api.grantFamilyConsent(resident.id, link.family_member_id, permissions);
          setMessage('Family access approved.');
        }
      }
      await load();
    } catch (actionError) {
      setError(actionError.message);
    }
  };

  const changePermission = (familyMemberId, permission, checked) => {
    setLinks(current => current.map(link => link.family_member_id === familyMemberId
      ? { ...link, [permission]: checked }
      : link));
  };

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;
  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Family Consent</h1>
          <p className="page-subtitle">You control which family accounts may view your records</p>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}
      {!resident && <div className="alert alert-info">Your account is not linked to a resident profile. Contact an administrator.</div>}
      <div className="card">
        <div className="card-header"><h3 className="card-title">Family access requests and consent</h3></div>
        {links.length ? links.map(link => (
          <div className="detail-grid" key={link.family_member_id}>
            <div className="detail-item"><label>Family account</label><span>{link.full_name || link.username}</span></div>
            <div className="detail-item">
              <label>Permission</label>
              <span>{link.consent_granted ? 'Access permissions granted' : 'Awaiting your approval'}</span>
              <label>
                <input
                  type="checkbox"
                  checked={link.can_view_profile}
                  onChange={event => changePermission(link.family_member_id, 'can_view_profile', event.target.checked)}
                /> View resident profile
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={link.can_view_prescriptions}
                  onChange={event => changePermission(link.family_member_id, 'can_view_prescriptions', event.target.checked)}
                /> View prescriptions
              </label>
            </div>
            <div className="detail-item">
              <button
                className={link.consent_granted ? 'btn btn-secondary' : 'btn btn-primary'}
                onClick={() => updateConsent(link, true)}
                disabled={!link.can_view_profile && !link.can_view_prescriptions}
              >{link.consent_granted ? 'Save permissions' : 'Approve access'}</button>
              {link.consent_granted && <button className="btn btn-secondary" onClick={() => updateConsent(link, false)}>Revoke access</button>}
            </div>
          </div>
        )) : <p>No family access requests or active permissions.</p>}
      </div>
    </div>
  );
}

function FamilyLinkManagement() {
  const [residentId, setResidentId] = useState('');
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLinks(await api.getFamilyLinks());
      setError('');
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const requestAccess = async e => {
    e.preventDefault();
    setError('');
    setMessage('');
    try {
      await api.requestFamilyLink(residentId.trim());
      setMessage('Request sent. The resident must approve access before any records are shared.');
      setResidentId('');
      await load();
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const cancelRequest = async id => {
    setError('');
    setMessage('');
    try {
      await api.cancelFamilyLinkRequest(id);
      setMessage('Pending request cancelled.');
      await load();
    } catch (cancelError) {
      setError(cancelError.message);
    }
  };

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;
  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Request Resident Access</h1>
          <p className="page-subtitle">Access is shared only after the resident grants consent</p>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}
      <div className="card">
        <form onSubmit={requestAccess}>
          <div className="form-group">
            <label className="form-label" htmlFor="family-resident-id">Resident ID supplied by the care facility</label>
            <input id="family-resident-id" className="form-input" value={residentId} onChange={e => setResidentId(e.target.value)} required />
          </div>
          <button className="btn btn-primary">Request access</button>
        </form>
      </div>
      <div className="card">
        <div className="card-header"><h3 className="card-title">Your active requests and approved links</h3></div>
        {links.length ? links.map(link => (
          <div className="detail-grid" key={link.resident_id}>
            <div className="detail-item"><label>Resident</label><span>{link.resident_name || link.resident_id}</span></div>
            <div className="detail-item"><label>Status</label><span>{link.consent_granted ? 'Approved' : 'Awaiting resident consent'}</span></div>
            {!link.consent_granted && <div className="detail-item"><button className="btn btn-secondary" onClick={() => cancelRequest(link.resident_id)}>Cancel request</button></div>}
          </div>
        )) : <p>You have no active resident access requests.</p>}
      </div>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════
   Settings Page
   ══════════════════════════════════════════════════════════════ */
function SettingsPage({ user }) {
  const [health, setHealth] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getHealth(), api.getDbHealth()])
      .then(([healthStatus, databaseStatus]) => {
        if (!cancelled) {
          setHealth(healthStatus);
          setDbHealth(databaseStatus);
        }
      })
      .catch(loadError => { if (!cancelled) setError(loadError.message); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Account & system configuration</p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      <div style={{ display: 'grid', gap: 'var(--space-6)', maxWidth: 720 }}>
        {/* Profile Card */}
        <div className="card">
          <div className="card-header"><h3 className="card-title">Profile</h3></div>
          <div className="detail-grid">
            <div className="detail-item"><label>Username</label><span>{user.username}</span></div>
            <div className="detail-item"><label>Role</label><span className={`badge badge-${user.role}`}>{user.role?.replace('_', ' ')}</span></div>
            <div className="detail-item"><label>Full Name</label><span>{user.full_name || '—'}</span></div>
            <div className="detail-item"><label>Phone</label><span>{user.phone || '—'}</span></div>
            <div className="detail-item"><label>Member Since</label><span>{user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</span></div>
            <div className="detail-item"><label>Last Login</label><span>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '—'}</span></div>
          </div>
        </div>

        {/* System Health */}
        <div className="card">
          <div className="card-header"><h3 className="card-title">System Status</h3></div>
          <div className="detail-grid">
            <div className="detail-item">
              <label>API</label>
              <span style={{ color: health?.status === 'ok' ? 'var(--color-success)' : 'var(--color-danger)' }}>
                {health?.status === 'ok' ? '● Connected' : '● Disconnected'}
              </span>
            </div>
            <div className="detail-item">
              <label>Database</label>
              <span style={{ color: dbHealth?.status === 'connected' ? 'var(--color-success)' : dbHealth?.status === 'unconfigured' ? 'var(--color-warning)' : 'var(--color-danger)' }}>
                ● {dbHealth?.status || 'Checking…'}
              </span>
            </div>
            <div className="detail-item"><label>Service</label><span>{health?.service || '—'}</span></div>
            <div className="detail-item"><label>DB Configured</label><span>{health?.database_configured ? 'Yes' : 'No'}</span></div>
          </div>
          {dbHealth?.message && (
            <div className={`alert ${dbHealth.status === 'connected' ? 'alert-success' : dbHealth.status === 'unconfigured' ? 'alert-info' : 'alert-error'}`} style={{ marginTop: 'var(--space-4)' }}>
              {dbHealth.message}
            </div>
          )}
        </div>

        {/* About */}
        <div className="card">
          <div className="card-header"><h3 className="card-title">About CareMeds</h3></div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
            CareMeds is an intelligent medication management platform designed for senior citizens in old-age homes.
            It helps doctors, caretakers, and families manage prescriptions, track medication schedules, and ensure
            safe, coordinated care delivery.
          </p>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-4)' }}>
            Version 0.1.0 • Phase 1 Foundation
          </p>
        </div>
      </div>
    </div>
  );
}
