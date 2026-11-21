import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AppState } from "react-native";
import * as SecureStore from "expo-secure-store";
import { MobileApi, MobileApiError, webOrigin } from "./api";
import {
  account,
  storedSession,
  type Account,
  type StoredSession,
} from "./models";

const STORAGE_KEY = "hvacline.customer-session.v1";
const STORAGE_OPTIONS: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
};
type SessionContextValue = {
  ready: boolean;
  error: string;
  user?: Account;
  api?: MobileApi;
  origin?: string;
  retry: () => void;
  establish: (session: StoredSession, user: Account) => Promise<void>;
  signOut: () => Promise<boolean>;
};
const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession>();
  const [user, setUser] = useState<Account>();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const revision = useRef(0);
  const currentToken = useRef<string | undefined>(undefined);
  currentToken.current = session?.token;
  const storageQueue = useRef<Promise<unknown>>(Promise.resolve());
  const configuration = useMemo(() => {
    try {
      return { origin: webOrigin(), error: "" };
    } catch (failure) {
      return {
        origin: undefined,
        error:
          failure instanceof Error
            ? failure.message
            : "Mobile access is not configured.",
      };
    }
  }, []);
  const persist = useCallback((value?: StoredSession) => {
    const task = storageQueue.current
      .catch(() => undefined)
      .then(() =>
        value
          ? SecureStore.setItemAsync(
              STORAGE_KEY,
              JSON.stringify(value),
              STORAGE_OPTIONS,
            )
          : SecureStore.deleteItemAsync(STORAGE_KEY, STORAGE_OPTIONS),
      );
    storageQueue.current = task;
    return task;
  }, []);
  const clear = useCallback(async () => {
    revision.current += 1;
    setSession(undefined);
    setUser(undefined);
    try {
      await persist();
    } catch {
      setError(
        "The saved session could not be removed. Unlock your device and try signing out again.",
      );
    }
  }, [persist]);
  const api = useMemo(() => {
    const token = session?.token;
    return configuration.origin
      ? new MobileApi(configuration.origin, token, () => {
          if (token && currentToken.current === token) void clear();
        })
      : undefined;
  }, [configuration.origin, session?.token, clear]);

  useEffect(() => {
    const current = ++revision.current;
    setReady(false);
    setError("");
    if (!configuration.origin) {
      setReady(true);
      return;
    }
    const origin = configuration.origin;
    void (async () => {
      try {
        await storageQueue.current.catch(() => undefined);
        const raw = await SecureStore.getItemAsync(
          STORAGE_KEY,
          STORAGE_OPTIONS,
        );
        if (current !== revision.current) return;
        let saved: StoredSession | undefined;
        try {
          saved = raw ? storedSession(JSON.parse(raw), origin) : undefined;
        } catch {
          saved = undefined;
        }
        if (!saved) {
          if (raw) await persist();
          return;
        }
        const profile = account(
          await new MobileApi(origin, saved.token).request("auth/me"),
        );
        if (current !== revision.current) return;
        setSession(saved);
        setUser(profile);
      } catch (failure) {
        if (current !== revision.current) return;
        if (failure instanceof MobileApiError && failure.status === 401) {
          try {
            await persist();
          } catch {
            setError(
              "The expired session could not be removed. Unlock this device and try again.",
            );
          }
        } else
          setError(
            failure instanceof Error
              ? failure.message
              : "Your saved session could not be opened.",
          );
      } finally {
        if (current === revision.current) setReady(true);
      }
    })();
    return () => {
      if (revision.current === current) revision.current += 1;
    };
  }, [attempt, configuration.origin, persist]);

  useEffect(() => {
    if (!session || !api) return;
    const current = revision.current;
    const expire = () => {
      if (current === revision.current) void clear();
    };
    const timer = setTimeout(
      expire,
      Math.max(0, session.expiresAt - Date.now()),
    );
    const subscription = AppState.addEventListener("change", (state) => {
      if (state !== "active" || current !== revision.current) return;
      if (Date.now() >= session.expiresAt) {
        expire();
        return;
      }
      void api
        .request("auth/me")
        .then((value) => {
          if (current === revision.current) setUser(account(value));
        })
        .catch(() => undefined);
    });
    return () => {
      clearTimeout(timer);
      subscription.remove();
    };
  }, [session, api, clear]);

  const establish = async (value: StoredSession, profile: Account) => {
    if (!configuration.origin || !storedSession(value, configuration.origin))
      throw new Error("Your sign-in has expired. Please sign in again.");
    const current = ++revision.current;
    await persist(value);
    if (current !== revision.current) return;
    setSession(value);
    setUser(profile);
    setError("");
    setReady(true);
  };
  const signOut = async () => {
    const previous = session;
    await persist();
    revision.current += 1;
    setSession(undefined);
    setUser(undefined);
    setError("");
    setReady(true);
    if (!previous) return true;
    try {
      await new MobileApi(previous.origin, previous.token).request(
        "auth/logout",
        "POST",
      );
      return true;
    } catch {
      return false;
    }
  };
  return (
    <SessionContext.Provider
      value={{
        ready,
        error: configuration.error || error,
        user,
        api,
        origin: configuration.origin,
        retry: () => setAttempt((value) => value + 1),
        establish,
        signOut,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("Customer session is not available.");
  return value;
}
