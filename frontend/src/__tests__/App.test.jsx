import { render, screen, waitFor } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders CareMeds title', () => {
    render(<App />);
    expect(screen.getByText('CareMeds')).toBeInTheDocument();
  });

  it('shows loading initially then success state', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok', service: 'caremeds-backend', database_configured: false }),
    });
    render(<App />);
    expect(screen.getByText(/Checking backend health/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Backend connected successfully/i)).toBeInTheDocument();
    });
  });

  it('shows error state on network failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    });
  });
});
