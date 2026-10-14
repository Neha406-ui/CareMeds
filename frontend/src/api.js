// Strip stray chars, trailing slashes, then guarantee /api suffix
const _raw = (import.meta.env.VITE_API_URL || '').trim().replace(/[\]>]+$/, '');
const _clean = _raw.replace(/\/+$/, '') || 'http://localhost:8000';
const BASE = _clean.endsWith('/api') ? _clean : _clean + '/api';

export function getToken() { return localStorage.getItem('cm_token'); }
export function setToken(token) { localStorage.setItem('cm_token', token); }
export function clearToken() { localStorage.removeItem('cm_token'); }

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const body = options.body;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  if (body && typeof body === 'object' && !isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
    body: body && typeof body === 'object' && !isFormData ? JSON.stringify(body) : body,
  });
  if (response.status === 401) {
    clearToken();
    window.location.hash = '#/login';
    throw new Error('Session expired');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function login(username, password) {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);
  const response = await fetch(`${BASE}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Login failed');
  }
  const data = await response.json();
  setToken(data.access_token);
  return data;
}

export async function logout() {
  try {
    if (getToken()) await request('/auth/logout', { method: 'POST' });
  } finally {
    clearToken();
  }
}

export function getMe() { return request('/auth/me'); }
export async function register(username, password, fullName, phone) {
  return request('/auth/register', {
    method: 'POST',
    body: { username, password, full_name: fullName || null, phone: phone || null, role: 'family_member' },
  });
}
export function getHealth() { return request('/health'); }
export function getDbHealth() { return request('/health/db'); }
export function createUser(body) { return request('/auth/users', { method: 'POST', body }); }
export function getUsers() { return request('/auth/users'); }
export function setUserActive(id, isActive) {
  return request(`/auth/users/${id}`, { method: 'PATCH', body: { is_active: isActive } });
}

export function getResidents() { return request('/residents'); }
export function getResident(id) { return request(`/residents/${id}`); }
export function createResident(body) { return request('/residents', { method: 'POST', body }); }
export function updateResident(id, body) { return request(`/residents/${id}`, { method: 'PUT', body }); }
export function deactivateResident(id) { return request(`/residents/${id}`, { method: 'DELETE' }); }

export function getAssignmentUsers() { return request('/users'); }
export function getAssignments() { return request('/assignments'); }
export function assignCaretaker(residentId, userId) {
  return request(`/residents/${residentId}/assignments/caretakers`, { method: 'POST', body: { user_id: userId } });
}
export function assignDoctor(residentId, userId) {
  return request(`/residents/${residentId}/assignments/doctors`, { method: 'POST', body: { user_id: userId } });
}
export function unassignCaretaker(residentId, userId) {
  return request(`/residents/${residentId}/assignments/caretakers/${userId}`, { method: 'DELETE' });
}
export function unassignDoctor(residentId, userId) {
  return request(`/residents/${residentId}/assignments/doctors/${userId}`, { method: 'DELETE' });
}

export function getFamilyLinks() { return request('/family-links'); }
export function requestFamilyLink(residentId) { return request(`/family-links/${residentId}`, { method: 'POST' }); }
export function cancelFamilyLinkRequest(residentId) { return request(`/family-links/${residentId}`, { method: 'DELETE' }); }
export function getFamilyConsentRequests(residentId) { return request(`/residents/${residentId}/family-consents`); }
export function grantFamilyConsent(residentId, familyMemberId, permissions, relationshipType = 'family') {
  return request(`/residents/${residentId}/family-consent`, {
    method: 'POST',
    body: {
      family_member_id: familyMemberId,
      relationship_type: relationshipType,
      can_view_profile: permissions.can_view_profile,
      can_view_prescriptions: permissions.can_view_prescriptions,
    },
  });
}
export function updateFamilyConsent(residentId, familyMemberId, permissions) {
  return request(`/residents/${residentId}/family-consent/${familyMemberId}`, { method: 'PATCH', body: permissions });
}
export function revokeFamilyConsent(residentId, familyMemberId) {
  return request(`/residents/${residentId}/family-consent/${familyMemberId}`, { method: 'DELETE' });
}

export function getMedicines() { return request('/medicines'); }
export function createMedicine(body) { return request('/medicines', { method: 'POST', body }); }
export function getPrescriptions() { return request('/prescriptions'); }
export function createPrescription(body) { return request('/prescriptions', { method: 'POST', body }); }
export function updatePrescription(id, body) { return request(`/prescriptions/${id}`, { method: 'PUT', body }); }
export function getDoses(date) { return request(`/doses?start_date=${encodeURIComponent(date)}`); }
export function recordDoseOutcome(id, body) { return request(`/doses/${id}/outcome`, { method: 'POST', body }); }
export function acknowledgeDose(id) { return request(`/doses/${id}/acknowledge`, { method: 'POST' }); }
export function getDoseHistory(id) { return request(`/doses/${id}/history`); }
export function discontinuePrescription(id, reason) {
  return request(`/prescriptions/${id}/discontinue`, { method: 'POST', body: { reason } });
}

export function getInventory(expiringWithinDays = 30) {
  return request(`/inventory?expiring_within_days=${encodeURIComponent(expiringWithinDays)}`);
}
export function stockIn(body) { return request('/inventory/stock-in', { method: 'POST', body }); }
export function stockOut(batchId, body) {
  return request(`/inventory/batches/${batchId}/stock-out`, { method: 'POST', body });
}
export function getInventoryTransactions(limit = 100) {
  return request(`/inventory/transactions?limit=${encodeURIComponent(limit)}`);
}
export function getAuditLogs(limit = 100) {
  return request(`/audit-logs?limit=${encodeURIComponent(limit)}`);
}
export function getNotifications(unreadOnly = false) {
  return request(`/notifications?unread_only=${encodeURIComponent(unreadOnly)}`);
}
export function acknowledgeNotification(id) {
  return request(`/notifications/${id}/acknowledge`, { method: 'POST' });
}
export function getEscalations(openOnly = true) {
  return request(`/escalations?open_only=${encodeURIComponent(openOnly)}`);
}
export function resolveEscalation(id, notes) {
  return request(`/escalations/${id}/resolve`, { method: 'POST', body: { notes } });
}
export function getFamilyContactRequests() { return request('/family-contact-requests'); }
export function createFamilyContactRequest(body) {
  return request('/family-contact-requests', { method: 'POST', body });
}
export function respondToFamilyContactRequest(id, body) {
  return request(`/family-contact-requests/${id}`, { method: 'PATCH', body });
}
export function getHandovers(residentId = '') {
  const suffix = residentId ? `?resident_id=${encodeURIComponent(residentId)}` : '';
  return request(`/handovers${suffix}`);
}
export function getEligibleHandoverCaretakers(residentId) {
  return request(`/handovers/eligible-caretakers?resident_id=${encodeURIComponent(residentId)}`);
}
export function createHandover(body) { return request('/handovers', { method: 'POST', body }); }
export function acknowledgeHandover(id) {
  return request(`/handovers/${id}/acknowledge`, { method: 'POST' });
}
export function getAdherence(startDate = '', endDate = '') {
  const params = new URLSearchParams();
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  const query = params.toString();
  return request(`/analytics/adherence${query ? `?${query}` : ''}`);
}
