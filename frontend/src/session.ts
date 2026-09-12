import { useSyncExternalStore } from "react";
import { useNavigate } from "react-router-dom";
import { getToken, setToken } from "./api";
import { home } from "./routes";

/** The credential the application is holding, as one fact rather than two.
 *
 *  It used to be `RequireAuth`'s own `useState`, which was enough while every
 *  route sat inside that gate. Since the tournament list and a tournament's
 *  detail render without one (spec `public-browsing`), two shells read the
 *  same fact — the gate, to decide whether to show Login, and the public
 *  shell, to decide whether it has an account at all — and a copy in each
 *  would be two answers to one question.
 *
 *  `localStorage` stays the single store; this module only lets React
 *  subscribe to it, since a write notifies nothing in its own tab. The
 *  snapshot is read from storage on every call rather than mirrored in a
 *  module variable: a mirror initialised at import time is stale for anything
 *  that writes the token afterwards, and equal strings compare equal, which is
 *  all `useSyncExternalStore` asks of a snapshot.
 */
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The held credential, or null when there is none. Re-renders the caller
 *  when it changes. */
export function useCredential(): string | null {
  return useSyncExternalStore(subscribe, getToken);
}

/** Re-read the credential after something else has written it — what Login
 *  does on a successful sign-in or signup. */
export function credentialChanged(): void {
  emit();
}

/** Discard the credential. Navigation is the caller's: a screen behind the
 *  gate has to leave for `/`, while a public screen is already somewhere a
 *  signed-out visitor may be. */
export function signOut(): void {
  setToken(null);
  emit();
}

/** Sign out and go home, which is what every screen offering the action
 *  wants. `RequireAuth` hands the same callback to the screens inside the
 *  gate through its outlet context; a public screen has no such context and
 *  calls this itself. */
export function useSignOut(): () => void {
  const navigate = useNavigate();
  return () => {
    signOut();
    navigate(home(), { replace: true });
  };
}
