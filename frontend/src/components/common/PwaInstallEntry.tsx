import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
}

function isInstalled(): boolean {
  if (typeof window === 'undefined') return false;
  const standaloneNavigator = navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    standaloneNavigator.standalone === true
  );
}

export function PwaInstallEntry() {
  const { t } = useApp();
  const [installed, setInstalled] = useState(isInstalled);
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [installing, setInstalling] = useState(false);
  const canOfferInstructions =
    window.isSecureContext && 'serviceWorker' in navigator;

  useEffect(() => {
    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    };
    const handleAppInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
      setShowInstructions(false);
    };
    const displayMode = window.matchMedia('(display-mode: standalone)');
    const handleDisplayModeChange = () => setInstalled(isInstalled());

    window.addEventListener(
      'beforeinstallprompt',
      handleBeforeInstallPrompt,
    );
    window.addEventListener('appinstalled', handleAppInstalled);
    displayMode.addEventListener('change', handleDisplayModeChange);

    return () => {
      window.removeEventListener(
        'beforeinstallprompt',
        handleBeforeInstallPrompt,
      );
      window.removeEventListener('appinstalled', handleAppInstalled);
      displayMode.removeEventListener('change', handleDisplayModeChange);
    };
  }, []);

  const handleInstall = async () => {
    if (!installPrompt) {
      setShowInstructions((visible) => !visible);
      return;
    }

    setInstalling(true);
    try {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;
      setInstallPrompt(null);
      if (choice.outcome === 'accepted') {
        setInstalled(true);
      } else {
        setShowInstructions(true);
      }
    } catch (error) {
      console.error('The MaizeCare AI installation prompt failed:', error);
      setInstallPrompt(null);
      setShowInstructions(true);
    } finally {
      setInstalling(false);
    }
  };

  if (installed || !canOfferInstructions) return null;

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => void handleInstall()}
        disabled={installing}
        aria-expanded={showInstructions}
        aria-controls="maizecare-install-instructions"
        className="inline-flex items-center gap-2 rounded-lg px-1 py-1 text-sm font-medium text-emerald-900 transition-colors hover:text-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 disabled:opacity-60 dark:text-emerald-300 dark:hover:text-emerald-200"
      >
        <Download className="h-4 w-4" aria-hidden="true" />
        <span>{t('pwaInstallAction')}</span>
      </button>
      {showInstructions && (
        <p
          id="maizecare-install-instructions"
          className="mt-2 max-w-xl rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs leading-relaxed text-emerald-950 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100"
          role="status"
        >
          {t('pwaInstallInstructions')}
        </p>
      )}
    </div>
  );
}
