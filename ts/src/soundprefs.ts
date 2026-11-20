/** A person's sounds and vibration (owner rule 2026-11-20; catalog/sounds.v1.json, services/notify_settings.py sounds).
 *  One choice in the account (Notifications, Sounds and vibration): tap and key sounds, vibration, volume and notification
 *  sounds. It is remembered and followed on every device and page the person signs in on; a shared device follows its manager,
 *  who may let the person's choice apply. Security and safety alerts always sound. A sound is never the only signal. */
export type Volume = "low" | "medium" | "high";
export interface SoundPrefs { tones: boolean; vibration: boolean; volume: Volume; notification_sounds: boolean }
export const DEFAULT_PREFS: Readonly<SoundPrefs> = Object.freeze({ tones: true, vibration: true, volume: "medium", notification_sounds: true });
/** Areas whose alerts always make a sound, whatever the person chose (the message register's locked areas). */
export const NEVER_SILENCED: readonly string[] = ["security", "safety"];
const KEY = "lynkomni.sounds.v1";
let memory: SoundPrefs | null = null;   // where the browser keeps nothing, the choice still holds for this visit

export function cleanPrefs(p: Partial<SoundPrefs> | null | undefined): SoundPrefs {
  const v = p?.volume;
  return { tones: p?.tones !== false, vibration: p?.vibration !== false, volume: v === "low" || v === "high" ? v : "medium", notification_sounds: p?.notification_sounds !== false };
}
/** The person's choice, as remembered on this device (the account's copy in the real app). */
export function loadPrefs(): SoundPrefs {
  try {
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(KEY) : null;
    if (raw) return cleanPrefs(JSON.parse(raw) as Partial<SoundPrefs>);
  } catch { /* storage blocked: fall back to this visit's choice */ }
  return memory ? { ...memory } : { ...DEFAULT_PREFS };
}
/** Change part of the choice and remember it. */
export function savePrefs(change: Partial<SoundPrefs>): SoundPrefs {
  const next = cleanPrefs({ ...loadPrefs(), ...change });
  memory = next;
  try { if (typeof localStorage !== "undefined") localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* kept for this visit */ }
  return next;
}
/** Whether an alert in this area may make a sound for this person (security and safety always do). */
export function alertSounds(p: SoundPrefs, area: string): boolean { return p.notification_sounds || NEVER_SILENCED.includes(area); }
