import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker
      .register(`${import.meta.env.BASE_URL}service-worker.js`, { updateViaCache: 'none' })
      .then((registration) => {
        // Check for a changed worker immediately; install precaches the exact
        // hashed assets from this build before the new worker takes control.
        void registration.update().catch(() => {
          // A failed update check while offline does not affect the active worker.
        });
      })
      .catch((error) => console.error('Service worker registration failed:', error));
  });
}

createRoot(document.getElementById('root')!).render(<App />);
