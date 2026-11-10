"use client";
import { useEffect, useState } from "react";
import { getSelectedWardrobeProfileId, getWearerCategoryEligibility } from "./api";

export type WearerCategoryCapability = {
  version: "wearer-category-capabilities-1.0.0" | "wearer-category-capabilities-2.0.0"; item_decisions?: Record<string, "Permit" | "Deny" | "Unknown">; enabled: boolean; configured: boolean;
  profile_id: string; policy_version: string | null; policy_sha256: string | null;
  details_revision: string | null; gender_key: "male" | "female" | null;
  allowed_categories: string[]; reason: { code: string; message: string } | null;
};
export type WearerCategoryAvailability = { version: "wearer-category-availability-1.0.0"; profile_id: string; usable: boolean; reason: string | null };

export function useWearerCategoryEligibility(profileId?: string | null) {
  const [data, setData] = useState<WearerCategoryCapability>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true, request = 0;
    const load = () => {
      const id = profileId ?? getSelectedWardrobeProfileId(); const sequence = ++request;
      if (!id) { setData(undefined); setError("Choose the intended wearer in Active wearer."); setLoading(false); return; }
      setLoading(true);
      void getWearerCategoryEligibility(id).then(next => {
        if (!live || sequence !== request || (profileId == null && getSelectedWardrobeProfileId() !== id)) return;
        if (!["wearer-category-capabilities-1.0.0", "wearer-category-capabilities-2.0.0"].includes(next.version) || next.profile_id !== id || !Array.isArray(next.allowed_categories)) throw new Error("The selected wearer policy could not be confirmed.");
        setData(next); setError("");
      }).catch((cause: unknown) => { if (live && sequence === request) { setData(undefined); setError(cause instanceof Error ? cause.message : "Could not confirm wearer category policy."); } }).finally(() => { if (live && sequence === request) setLoading(false); });
    };
    load(); window.addEventListener("wearer-category-policy-changed", load);
    return () => { live = false; request++; window.removeEventListener("wearer-category-policy-changed", load); };
  }, [profileId]);
  const blocked = loading || !data || (data.enabled && !data.configured);
  const permits = (category: string | null) => !!data && (!data.enabled || data.configured && category !== null && data.allowed_categories.includes(category));
  const permitsItem = (id: string, category: string | null) => permits(category) && (data?.version !== "wearer-category-capabilities-2.0.0" || data.item_decisions?.[id] === "Permit");
  const text = loading ? "Checking selected wearer category policy…" : error || (data?.enabled ? data.configured ? `This application's ${data.gender_key} wearer policy permits ${data.allowed_categories.length} garment categories. Shared garments remain owned by the account.` : data.reason?.message ?? "Configure this wearer's category policy under Profile before starting new work." : "");
  return { data, blocked, loading, error, permits, permitsItem, text };
}
