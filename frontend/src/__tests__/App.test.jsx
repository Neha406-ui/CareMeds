import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from '../App';

const userFor = role => ({
  id: 'user-1',
  username: 'care-user',
  full_name: 'Care User',
  role,
});

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function mockUserSession(role, prescriptions = [], familyLinks = []) {
  const user = userFor(role);
  localStorage.setItem('cm_token', 'test-access-token');
  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url);
    if (path.endsWith('/auth/me')) return response(user);
    if (path.endsWith('/residents')) return response([]);
    if (path.endsWith('/auth/users') && options.method === 'POST') {
      return response({ id: 'created-user', username: 'new-doctor', role: 'doctor' });
    }
    if (path.endsWith('/auth/users')) return response([]);
    if (path.endsWith('/assignments')) return response([]);
    if (path.endsWith('/family-links')) return response(familyLinks);
    if (path.endsWith('/users')) return response([]);
    if (path.endsWith('/medicines')) return response([]);
    if (path.endsWith('/prescriptions')) return response(prescriptions);
    if (path.includes('/notifications?')) return response([]);
    if (path.endsWith('/analytics/adherence')) return response({
      start_date: '2026-01-01',
      end_date: '2026-01-30',
      adherence_rate_percent: null,
      total_doses: 0,
      counts: { administered: 0, refused: 0, withheld: 0, not_administered: 0, unable_to_confirm: 0, unresolved: 0 },
      cancelled_doses: 0,
      formula: 'administered / all occurred, non-cancelled scheduled doses; unresolved outcomes remain in the denominator',
    });
    if (path.endsWith('/family-contact-requests')) return response([]);
    if (path.endsWith('/family-links')) return response([]);
    if (path.includes('/inventory?')) return response([]);
    if (path.includes('/inventory/transactions?')) return response([]);
    if (path.includes('/escalations?')) return response([]);
    if (path.endsWith('/handovers')) return response([]);
    if (path.includes('/audit-logs?')) return response([]);
    if (path.endsWith('/health')) return response({ status: 'ok', service: 'caremeds-backend' });
    if (path.endsWith('/auth/logout') && options.method === 'POST') return response(null, 204);
    return response({ detail: 'Not found' }, 404);
  });
}

describe('CareMeds role-based application surfaces', () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.hash = '';
  });

  it('requires login before rendering protected navigation', () => {
    render(<App />);
    expect(screen.getByText('CareMeds')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Residents' })).not.toBeInTheDocument();
  });

  it.each([
    ['admin', 'Overview', 'Access Management'],
    ['doctor', 'Clinical Dashboard', 'Prescriptions'],
    ['caretaker', 'Care Dashboard', 'Assigned Residents'],
    ['resident', 'My Medication Dashboard', 'Family Consent'],
    ['family_member', 'Shared Care Dashboard', 'Request Resident Access'],
  ])('shows role-specific dashboard and navigation for %s', async (role, dashboard, navLabel) => {
    mockUserSession(role);
    render(<App />);
    expect(await screen.findByRole('heading', { name: dashboard })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: navLabel })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Medicines' })).toBeInTheDocument();
    if (role === 'family_member') {
      expect(screen.queryByRole('button', { name: 'Linked Residents' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Prescriptions' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Medication Schedule' })).not.toBeInTheDocument();
    } else {
      expect(screen.getByRole('button', { name: 'Prescriptions' })).toBeInTheDocument();
    }
    if (role !== 'admin') {
      expect(screen.queryByRole('button', { name: 'Access Management' })).not.toBeInTheDocument();
    }
  });

  it('revokes the server session on logout and returns to sign-in', async () => {
    mockUserSession('admin');
    render(<App />);
    await screen.findByRole('heading', { name: 'Overview' });
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument());
    const logoutCall = global.fetch.mock.calls.find(([url]) => String(url).endsWith('/auth/logout'));
    expect(logoutCall).toBeTruthy();
    expect(logoutCall[1].headers.Authorization).toBe('Bearer test-access-token');
    expect(localStorage.getItem('cm_token')).toBeNull();
  });

  it('shows an explicit session-revocation failure after local sign-out', async () => {
    mockUserSession('admin');
    global.fetch.mockImplementation(async (url, options = {}) => {
      if (String(url).endsWith('/auth/logout')) throw new Error('Network unavailable');
      if (String(url).endsWith('/auth/me')) return response(userFor('admin'));
      if (String(url).endsWith('/residents')) return response([]);
      if (String(url).endsWith('/medicines')) return response([]);
      if (String(url).endsWith('/prescriptions')) return response([]);
      if (String(url).endsWith('/health')) return response({ status: 'ok' });
      return response({}, 404);
    });
    render(<App />);
    await screen.findByRole('heading', { name: 'Overview' });
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(await screen.findByText(/server could not revoke this session/i)).toBeInTheDocument();
  });

  it('shows prescription actions only for the prescribing doctor', async () => {
    const prescriptions = [
      {
        id: 'rx-own',
        doctor_id: 'user-1',
        dosage: '1 tablet',
        frequency: 'Daily',
        scheduled_times: ['09:00'],
        timezone: 'UTC',
        start_date: '2026-01-01',
        status: 'active',
      },
      {
        id: 'rx-other',
        doctor_id: 'user-2',
        dosage: '2 tablets',
        frequency: 'Twice daily',
        scheduled_times: ['09:00', '21:00'],
        timezone: 'UTC',
        start_date: '2026-01-01',
        status: 'active',
      },
    ];
    mockUserSession('doctor', prescriptions);
    render(<App />);
    await screen.findByRole('heading', { name: 'Clinical Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Prescriptions' }));
    await screen.findByRole('heading', { name: 'Prescriptions' });
    expect(screen.getAllByRole('button', { name: 'Edit' })).toHaveLength(1);
    expect(screen.getAllByRole('button', { name: 'Discontinue' })).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    expect(screen.getByRole('heading', { name: 'Edit Prescription' })).toBeInTheDocument();
  });

  it('does not offer prescription mutations to administrators', async () => {
    mockUserSession('admin', [{
      id: 'rx-own',
      doctor_id: 'doctor-id',
      dosage: '1 tablet',
      frequency: 'Daily',
      scheduled_times: ['09:00'],
      timezone: 'UTC',
      start_date: '2026-01-01',
      status: 'active',
    }]);
    render(<App />);
    await screen.findByRole('heading', { name: 'Overview' });
    fireEvent.click(screen.getByRole('button', { name: 'Prescriptions' }));
    await screen.findByRole('heading', { name: 'Prescriptions' });
    expect(screen.queryByRole('button', { name: 'New Prescription' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Discontinue' })).not.toBeInTheDocument();
  });

  it('gives administrators the account, consent, and assignment management surface', async () => {
    mockUserSession('admin');
    render(<App />);
    await screen.findByRole('heading', { name: 'Overview' });
    fireEvent.click(screen.getByRole('button', { name: 'Access Management' }));
    expect(await screen.findByRole('heading', { name: 'Access Management' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Current assignments' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Family access and consent' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'User accounts' })).toBeInTheDocument();
  });

  it('lets only administrators create accounts through the account management screen', async () => {
    mockUserSession('admin');
    render(<App />);
    await screen.findByRole('heading', { name: 'Overview' });
    fireEvent.click(screen.getByRole('button', { name: 'Access Management' }));
    await screen.findByRole('heading', { name: 'Create user account' });
    expect(screen.getByRole('option', { name: 'Admin' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Doctor' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Caretaker' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Resident' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Family Member' })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'new-doctor' } });
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'doctor' } });
    fireEvent.change(screen.getByLabelText('Full name (optional)'), { target: { value: 'New Doctor' } });
    fireEvent.change(screen.getByLabelText('Temporary password'), { target: { value: 'a-secure-initial-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByText(/account created/i)).toBeInTheDocument();
    const createCall = global.fetch.mock.calls.find(([url, options]) =>
      String(url).endsWith('/auth/users') && options.method === 'POST');
    expect(createCall).toBeTruthy();
    expect(JSON.parse(createCall[1].body)).toMatchObject({
      username: 'new-doctor',
      full_name: 'New Doctor',
      role: 'doctor',
      password: 'a-secure-initial-password',
    });
  });

  it('requires explicit family scopes before a resident can approve access', async () => {
    mockUserSession('resident');
    const resident = { id: 'resident-record-1', full_name: 'Resident One' };
    const pendingLink = {
      family_member_id: 'family-1',
      username: 'family-user',
      full_name: 'Family User',
      consent_granted: false,
      can_view_profile: false,
      can_view_prescriptions: false,
    };
    global.fetch = vi.fn(async (url, options = {}) => {
      const path = String(url);
      if (path.endsWith('/auth/me')) return response(userFor('resident'));
      if (path.endsWith('/residents')) return response([resident]);
      if (path.endsWith('/family-consents')) return response([pendingLink]);
      if (path.endsWith('/family-consent') && options.method === 'POST') return response({}, 201);
      if (path.endsWith('/medicines') || path.endsWith('/prescriptions')) return response([]);
      if (path.endsWith('/health')) return response({ status: 'ok' });
      return response({ detail: 'Not found' }, 404);
    });

    render(<App />);
    await screen.findByRole('heading', { name: 'My Medication Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Family Consent' }));
    await screen.findByText('Family User');
    const approveButton = screen.getByRole('button', { name: 'Approve access' });
    expect(approveButton).toBeDisabled();
    fireEvent.click(screen.getByLabelText('View prescriptions'));
    expect(approveButton).toBeEnabled();
    fireEvent.click(approveButton);

    await screen.findByText('Family access approved.');
    const grantCall = global.fetch.mock.calls.find(([url, options]) =>
      String(url).endsWith('/family-consent') && options.method === 'POST');
    expect(grantCall).toBeTruthy();
    expect(JSON.parse(grantCall[1].body)).toMatchObject({
      family_member_id: 'family-1',
      can_view_profile: false,
      can_view_prescriptions: true,
    });
  });

  it('lets an assigned caretaker record a reasoned dose outcome', async () => {
    localStorage.setItem('cm_token', 'test-access-token');
    const dose = {
      id: 'dose-1',
      resident_id: 'resident-1',
      medicine_name: 'Medication A',
      dosage: '1 tablet',
      scheduled_local_time: '09:00',
      timezone: 'UTC',
      status: 'scheduled',
      timeliness: 'due',
    };
    global.fetch = vi.fn(async (url, options = {}) => {
      const path = String(url);
      if (path.endsWith('/auth/me')) return response(userFor('caretaker'));
      if (path.endsWith('/residents')) return response([]);
      if (path.endsWith('/medicines') || path.endsWith('/prescriptions')) return response([]);
      if (path.includes('/doses?')) return response([dose]);
      if (path.endsWith('/doses/dose-1/outcome') && options.method === 'POST') return response({ ...dose, status: 'withheld' });
      if (path.endsWith('/health')) return response({ status: 'ok' });
      return response({ detail: 'Not found' }, 404);
    });

    render(<App />);
    await screen.findByRole('heading', { name: 'Care Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Medication Schedule' }));
    await screen.findByText('Medication A');
    fireEvent.click(screen.getByRole('button', { name: 'Record outcome' }));
    fireEvent.change(screen.getByLabelText('Outcome'), { target: { value: 'withheld' } });
    fireEvent.change(screen.getByLabelText('Reason *'), { target: { value: 'Clinical review required' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save outcome' }));
    await screen.findByText('Dose outcome recorded.');
    const outcomeCall = global.fetch.mock.calls.find(([url, options]) =>
      String(url).endsWith('/doses/dose-1/outcome') && options.method === 'POST');
    expect(JSON.parse(outcomeCall[1].body)).toMatchObject({
      status: 'withheld',
      reason: 'Clinical review required',
    });
  });

  it('keeps resident reminder acknowledgement separate from administration', async () => {
    localStorage.setItem('cm_token', 'test-access-token');
    const dose = {
      id: 'dose-2',
      resident_id: 'resident-record-1',
      medicine_name: 'Medication B',
      dosage: '1 capsule',
      scheduled_local_time: '08:00',
      timezone: 'UTC',
      status: 'scheduled',
      timeliness: 'due',
      acknowledged_at: null,
    };
    global.fetch = vi.fn(async (url, options = {}) => {
      const path = String(url);
      if (path.endsWith('/auth/me')) return response(userFor('resident'));
      if (path.endsWith('/residents')) return response([{ id: 'resident-record-1', full_name: 'Resident One' }]);
      if (path.endsWith('/medicines') || path.endsWith('/prescriptions')) return response([]);
      if (path.includes('/doses?')) return response([dose]);
      if (path.endsWith('/doses/dose-2/acknowledge') && options.method === 'POST') {
        return response({ ...dose, acknowledged_at: '2026-10-13T08:00:00' });
      }
      if (path.endsWith('/health')) return response({ status: 'ok' });
      return response({ detail: 'Not found' }, 404);
    });

    render(<App />);
    await screen.findByRole('heading', { name: 'My Medication Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Medication Schedule' }));
    await screen.findByText('Medication B');
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge reminder' }));
    expect(await screen.findByText(/does not record medication administration/i)).toBeInTheDocument();
    const acknowledgementCall = global.fetch.mock.calls.find(([url, options]) =>
      String(url).endsWith('/doses/dose-2/acknowledge') && options.method === 'POST');
    expect(acknowledgementCall).toBeTruthy();
  });

  it('shows stock management to caretakers but not to residents', async () => {
    mockUserSession('caretaker');
    const caretakerView = render(<App />);
    await screen.findByRole('heading', { name: 'Care Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Care Operations' }));
    expect(await screen.findByRole('heading', { name: 'Medication inventory' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Receive stock' })).toBeInTheDocument();
    caretakerView.unmount();

    localStorage.clear();
    mockUserSession('resident');
    render(<App />);
    await screen.findByRole('heading', { name: 'My Medication Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Reminders' }));
    expect(await screen.findByRole('heading', { name: 'Notifications' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Adherence summary' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Medication inventory' })).not.toBeInTheDocument();
  });

  it('shows the contact request form to family members without staff stock actions', async () => {
    mockUserSession('family_member');
    render(<App />);
    await screen.findByRole('heading', { name: 'Shared Care Dashboard' });
    fireEvent.click(screen.getByRole('button', { name: 'Care Updates' }));
    expect(await screen.findByRole('heading', { name: 'Contact the care team' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Medication inventory' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Receive stock' })).not.toBeInTheDocument();
  });

  it('shows family navigation only for currently consented scopes', async () => {
    mockUserSession('family_member', [], [{
      resident_id: 'resident-1',
      is_active: true,
      consent_granted: true,
      can_view_profile: true,
      can_view_prescriptions: false,
    }]);
    render(<App />);
    await screen.findByRole('heading', { name: 'Shared Care Dashboard' });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Linked Residents' })).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Prescriptions' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Medication Schedule' })).not.toBeInTheDocument();
  });
});
