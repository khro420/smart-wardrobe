"use client";

import { FormEvent, useEffect, useState } from "react";
import { ShieldCheck, User } from "lucide-react";

import Layout from "@/components/Layout";
import { getPreferences, getProfile, savePreference, type Profile, updateProfile } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>();
  const [name, setName] = useState("");
  const [styleNote, setStyleNote] = useState("");
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingStyle, setSavingStyle] = useState(false);

  useEffect(() => {
    let active = true;
    void Promise.all([getProfile(), getPreferences()]).then(([nextProfile, preferences]) => {
      if (!active) return;
      setProfile(nextProfile);
      setName(nextProfile.display_name);
      const savedStyle = preferences.find((preference) => preference.preference_type === "style_note");
      setStyleNote(typeof savedStyle?.preference_value.value === "string" ? savedStyle.preference_value.value : "");
      setMessageIsError(false);
    }).catch((error: unknown) => {
      if (active) { setMessage(error instanceof Error ? error.message : "Could not load profile."); setMessageIsError(true); }
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setSavingProfile(true);
    setMessage("");
    try {
      const next = await updateProfile(name.trim());
      setProfile(next);
      setMessage("Profile updated.");
      setMessageIsError(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update profile.");
      setMessageIsError(true);
    } finally {
      setSavingProfile(false);
    }
  };

  const saveStylePreference = async (event: FormEvent) => {
    event.preventDefault();
    setSavingStyle(true);
    setMessage("");
    try {
      await savePreference("style_note", { value: styleNote.trim() }, 1);
      setMessage("Style preference saved for future recommendations.");
      setMessageIsError(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save the preference.");
      setMessageIsError(true);
    } finally {
      setSavingStyle(false);
    }
  };

  return <Layout><div className="mx-auto max-w-2xl space-y-6" aria-busy={loading}><div className="border-2 border-black bg-white p-6"><div className="flex items-center gap-3"><User className="h-8 w-8" aria-hidden="true" /><div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">ACCOUNT</p><h1 className="text-2xl font-black">Your profile</h1></div></div><p className="mt-4 text-sm text-zinc-600">Only the authenticated account can retrieve or update this profile and its wardrobe records.</p></div>{message && <p role={messageIsError ? "alert" : "status"} className={`border-2 p-3 text-sm ${messageIsError ? "border-rose-600 bg-rose-50 text-rose-700" : "border-emerald-600 bg-emerald-50 text-emerald-800"}`}>{message}</p>}{loading && <div className="ui-skeleton h-44 rounded-xl" role="status" aria-label="Loading profile" />}<form onSubmit={saveProfile} className={`space-y-4 border-2 border-black bg-white p-6 ${loading ? "hidden" : ""}`}><label className="block text-sm font-bold">Display name<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} disabled={savingProfile} className="mt-1 w-full border-2 border-black p-2" /></label><label className="block text-sm font-bold">Email<input value={profile?.email ?? ""} readOnly aria-describedby="email-help" className="mt-1 w-full border-2 border-zinc-300 bg-zinc-100 p-2 text-zinc-600" /><span id="email-help" className="mt-1 block text-xs font-normal text-zinc-500">Your sign-in email cannot be changed here.</span></label><button disabled={!profile || !name.trim() || savingProfile} aria-busy={savingProfile} className="min-h-11 bg-black px-4 py-3 text-sm font-bold text-white disabled:opacity-40">{savingProfile ? "Saving…" : "Save profile"}</button></form><form onSubmit={saveStylePreference} className={`space-y-4 border-2 border-black bg-zinc-50 p-6 ${loading ? "hidden" : ""}`}><div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">USER PREFERENCE</p><h2 className="text-xl font-black">Style note</h2><p className="mt-1 text-sm text-zinc-600">This private preference is attached to recommendation requests from your confirmed wardrobe.</p></div><label className="block text-sm font-bold">What should your recommendations prioritise?<textarea value={styleNote} onChange={(event) => setStyleNote(event.target.value)} maxLength={300} disabled={savingStyle} className="mt-1 min-h-24 w-full resize-y border-2 border-black bg-white p-3" placeholder="For example: relaxed neutral outfits for campus." /><span className="mt-1 block text-right text-xs font-normal text-zinc-500">{styleNote.length}/300</span></label><button disabled={!profile || !styleNote.trim() || savingStyle} aria-busy={savingStyle} className="min-h-11 bg-black px-4 py-3 text-sm font-bold text-white disabled:opacity-40">{savingStyle ? "Saving…" : "Save style note"}</button></form><aside className="border-2 border-black bg-zinc-50 p-5"><div className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" aria-hidden="true" /><h2 className="font-bold">Privacy and media</h2></div><p className="mt-2 text-sm text-zinc-600">Wardrobe uploads, personal images, preferences, and generated visualisations are private by default and served through owner-checked API routes.</p></aside></div></Layout>;
}
