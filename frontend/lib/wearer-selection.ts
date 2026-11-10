import { getAccessToken, getWardrobeProfiles, type WardrobeProfile } from "./api";

const choicePrefix = "smart_wardrobe_wearer_selection:";
export const isWearerId = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(value);

// Local routing only. The server alone authenticates the bearer and wearer.
export function authenticationSession(token: string | null = getAccessToken()): string {
  if (!token) return "signed-out";
  const parts = token.split(".");
  if (parts.length === 5 && parts[0] === "v2" && /^[A-Za-z0-9_-]+$/.test(parts[1]) && /^\d+$/.test(parts[2]) && /^[0-9a-f]{32}$/.test(parts[3]) && /^[0-9a-f]{64}$/.test(parts[4])) return `v2:${parts[1]}:${parts[2]}:${parts[3]}`;
  if (parts.length === 3 && /^[A-Za-z0-9_-]+$/.test(parts[0]) && /^\d+$/.test(parts[1]) && /^[0-9a-f]{64}$/.test(parts[2])) return `legacy:${parts[0]}:${parts[1]}`;
  return "unrecognized-session";
}

export function rememberWearer(profileId: string, deliberate: boolean) {
  if (!isWearerId(profileId)) throw new Error("Choose an active wearer.");
  sessionStorage.setItem("smart_wardrobe_profile_id", profileId);
  sessionStorage.setItem(choicePrefix + authenticationSession(), JSON.stringify({ profileId, deliberate }));
}

export function selectedWearer(profiles: WardrobeProfile[]): WardrobeProfile | undefined {
  if (profiles.length === 1) return profiles[0];
  try {
    const choice = JSON.parse(sessionStorage.getItem(choicePrefix + authenticationSession()) ?? "null");
    if (choice?.deliberate === true && choice.profileId === sessionStorage.getItem("smart_wardrobe_profile_id")) return profiles.find(profile => profile.id === choice.profileId);
  } catch { /* Unscoped or corrupt selection never establishes deliberate intent. */ }
  return undefined;
}

export async function captureWearer(): Promise<WardrobeProfile> {
  const session = authenticationSession();
  const profiles = await getWardrobeProfiles();
  if (authenticationSession() !== session) throw new Error("Your sign-in session changed. Reload before requesting an outfit.");
  const wearer = selectedWearer(profiles);
  if (!wearer) throw new Error("Choose the intended wearer in Active wearer before requesting an outfit.");
  rememberWearer(wearer.id, profiles.length > 1);
  return wearer;
}

export function historySelection(): { view?: "historical" | "legacy_unrecorded"; wearer_profile_id?: string } {
  if (typeof window === "undefined") return {};
  const query = new URLSearchParams(window.location.search);
  if (query.get("view") === "legacy_unrecorded") return { view: "legacy_unrecorded" };
  const wearer = query.get("wearer_profile_id");
  if (query.get("view") === "historical" && isWearerId(wearer)) return { view: "historical", wearer_profile_id: wearer };
  return {};
}
