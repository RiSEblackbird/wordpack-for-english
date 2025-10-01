import React, { useEffect, useMemo, useState } from 'react';

interface GoogleLoginButtonProps {
  className?: string;
}

type GoogleCredentialResponse = {
  clientId: string;
  credential: string;
  select_by: string;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: { client_id: string; callback: (res: GoogleCredentialResponse) => void }) => void;
          prompt: (cb?: (notification: { isNotDisplayed: () => boolean; isSkippedMoment: () => boolean }) => void) => void;
          renderButton: (element: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

async function postLogin(credential: string): Promise<void> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ credential }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body?.detail === 'string' ? body.detail : res.statusText;
    throw new Error(detail || 'login failed');
  }
}

export const GoogleLoginButton: React.FC<GoogleLoginButtonProps> = ({ className }) => {
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch('/api/auth/meta');
        if (!res.ok) throw new Error(`failed to load auth meta: ${res.status}`);
        const meta = await res.json();
        if (!mounted) return;
        if (typeof meta?.client_id !== 'string' || !meta.client_id) {
          throw new Error('Google client id missing');
        }
        setClientId(meta.client_id);
        setMetaLoading(false);
      } catch (err) {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
        setMetaLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!clientId) return;
    let script: HTMLScriptElement | null = document.querySelector(`script[src="${GOOGLE_SCRIPT_SRC}"]`);
    if (script && script.dataset.loaded === 'true') {
      setReady(true);
      return;
    }
    if (!script) {
      script = document.createElement('script');
      script.src = GOOGLE_SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => {
        script!.dataset.loaded = 'true';
        setReady(true);
      };
      script.onerror = () => {
        setError('Google ログインスクリプトの読み込みに失敗しました');
      };
      document.head.appendChild(script);
    } else {
      script.addEventListener('load', () => {
        script!.dataset.loaded = 'true';
        setReady(true);
      });
      script.addEventListener('error', () => {
        setError('Google ログインスクリプトの読み込みに失敗しました');
      });
    }
  }, [clientId]);

  useEffect(() => {
    if (!ready || !clientId || !window.google?.accounts?.id) return;

    const handleResponse = async (response: GoogleCredentialResponse) => {
      try {
        setLoading(true);
        await postLogin(response.credential);
        window.location.reload();
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(`ログインに失敗しました: ${message}`);
      } finally {
        setLoading(false);
      }
    };

    window.google.accounts.id.initialize({ client_id: clientId, callback: handleResponse });
    const btnContainer = document.getElementById('google-login-button');
    if (btnContainer) {
      window.google.accounts.id.renderButton(btnContainer, {
        theme: 'outline',
        size: 'large',
        width: 340,
        logo_alignment: 'left',
        shape: 'pill',
      });
    }
    window.google.accounts.id.prompt();
  }, [ready, clientId]);

  const disabled = !!error || loading || !clientId;

  const fallbackButton = useMemo(() => (
    <button
      type="button"
      disabled={disabled}
      onClick={() => window.google?.accounts?.id?.prompt?.()}
      style={{
        width: '100%',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.6rem',
        padding: '0.75rem 1.5rem',
        borderRadius: '9999px',
        border: '1px solid rgba(148, 163, 184, 0.5)',
        background: disabled ? 'rgba(15, 23, 42, 0.4)' : '#1d4ed8',
        color: '#f8fafc',
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'transform 0.15s ease, box-shadow 0.2s ease',
        boxShadow: disabled ? undefined : '0 10px 30px rgba(29, 78, 216, 0.45)',
      }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M17.64 9.2045C17.64 8.56636 17.5827 7.95273 17.4764 7.36364H9V10.8455H13.8436C13.635 11.9727 13.0009 12.9232 12.0505 13.56V15.8195H14.9564C16.6582 14.2527 17.64 11.9455 17.64 9.2045Z"
          fill="#4285F4"
        />
        <path
          d="M9 18C11.43 18 13.4409 17.1941 14.9564 15.8196L12.0505 13.56C11.2323 14.1014 10.1964 14.4181 9 14.4181C6.65591 14.4181 4.67182 12.8373 3.96409 10.71H0.957306V13.0418C2.46318 15.9832 5.48182 18 9 18Z"
          fill="#34A853"
        />
        <path
          d="M3.96409 10.71C3.78545 10.1686 3.68182 9.59318 3.68182 9C3.68182 8.40682 3.78545 7.83136 3.96409 7.29V4.95818H0.957273C0.347727 6.15545 0 7.54364 0 9C0 10.4564 0.347727 11.8445 0.957273 13.0418L3.96409 10.71Z"
          fill="#FBBC05"
        />
        <path
          d="M9 3.58182C10.3077 3.58182 11.47 4.03636 12.37 4.90182L15.02 2.25182C13.4409 0.788182 11.43 0 9 0C5.48182 0 2.46318 2.01682 0.957306 4.95818L3.96409 7.29C4.67182 5.16273 6.65591 3.58182 9 3.58182Z"
          fill="#EA4335"
        />
      </svg>
      {loading ? 'サインイン中…' : 'Googleでログイン'}
    </button>
  ), [disabled, loading]);

  return (
    <div className={className} style={{ width: '100%' }}>
      <div id="google-login-button" style={{ width: '100%', minHeight: '48px' }} />
      {!ready ? fallbackButton : null}
      {error ? (
        <p
          role="alert"
          style={{
            marginTop: '1rem',
            color: '#f87171',
            fontSize: '0.9rem',
            lineHeight: 1.5,
          }}
        >
          {error}
        </p>
      ) : null}
    </div>
  );
};
