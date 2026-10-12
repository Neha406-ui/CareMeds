import React, { useEffect, useState } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

function App() {
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [details, setDetails] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setStatus('loading');
        const res = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
        });
        if (res.ok) {
          const data = await res.json();
          setStatus('ok');
          setMessage('Backend connected successfully');
          setDetails(data);
        } else {
          setStatus('error');
          setMessage(`Backend returned ${res.status}`);
          setDetails(null);
        }
      } catch (err) {
        setStatus('error');
        setMessage(err?.message || 'Unable to connect to backend');
        setDetails(null);
      }
    };
    checkHealth();
  }, []);

  return (
    <div className="container">
      <header className="header">
        <h1>CareMeds</h1>
        <p className="subtitle">Intelligent Medication Management for Senior Citizens in Old-Age Homes</p>
      </header>
      <main className="main">
        <section className="card" aria-live="polite" aria-label="Service connection status">
          <h2>Service API Connection Status</h2>
          {status === 'loading' && <p>Checking backend health...</p>}
          {status === 'ok' && (
            <div>
              <p className="success">{message}</p>
              {details && (
                <pre className="details" data-testid="health-details">{JSON.stringify(details, null, 2)}</pre>
              )}
            </div>
          )}
          {status === 'error' && <p className="error">{message}</p>}
        </section>
      </main>
      <footer className="footer">
        <small>Phase 1 Foundation</small>
      </footer>
    </div>
  );
}

export default App;






