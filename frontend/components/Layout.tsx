"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Home, Shirt, PlusCircle, User, ShieldCheck, LogOut, History } from "lucide-react";
import Image from "next/image";
import { ApiError, clearAccessToken, getAccessToken, getSelectedWardrobeProfileId, getWardrobeProfiles, logout, setSelectedWardrobeProfileId, type WardrobeProfile } from "@/lib/api";
import { leaveHomepageFlow } from "@/lib/recommendation-session";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/assistant", label: "Outfit Assistant", icon: Shirt },
  { href: "/wardrobe", label: "My wardrobe", icon: Shirt },
  { href: "/extract", label: "Add an outfit", icon: PlusCircle },
  { href: "/history", label: "Recommendation history", icon: History },
  { href: "/profile", label: "Profile", icon: User },
];

function SidebarContent({ pathname, onNavigate, profiles, selectedProfileId, onProfileChange, mobile = false }: { pathname: string; onNavigate: () => void; profiles: WardrobeProfile[]; selectedProfileId: string | null; onProfileChange: (profileId: string) => void; mobile?: boolean }) {
  return <>
    <div className="flex h-[88px] items-center justify-between px-6">
      <Link href="/" onClick={onNavigate} className="flex items-center">
        <Image src="/logo.png" alt="AURA" width={3420} height={1265} sizes="90px" style={{ height: 32, width: "auto" }} className="object-contain" priority />
      </Link>
      {mobile && <button type="button" onClick={onNavigate} className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900" aria-label="Close navigation menu"><X className="h-5 w-5" aria-hidden="true" /></button>}
    </div>
    <nav aria-label="Primary navigation" className="flex-1 space-y-1 px-4 py-5">
      <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Your space</p>
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return <Link key={item.href} href={item.href} onClick={onNavigate} aria-current={isActive ? "page" : undefined} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors ${isActive ? "bg-[#f5eaf1] text-[#6d335b]" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}`}><Icon className="h-[18px] w-[18px]" strokeWidth={isActive ? 2.4 : 2} aria-hidden="true" /><span>{item.label}</span></Link>;
      })}
    </nav>
    <div className="mx-4 rounded-2xl border border-[#ead7e2] bg-[#fdf8fb] p-3">
      <label className="block text-[11px] font-semibold uppercase tracking-[0.12em] text-[#6d335b]">Active wearer
        <select value={selectedProfileId ?? ""} onChange={(event) => onProfileChange(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-800" aria-label="Select active wardrobe profile">
          {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}{profile.is_default ? " (default)" : ""}</option>)}
        </select>
      </label>
      <Link href="/profile" onClick={onNavigate} className="mt-2 inline-block text-xs font-semibold text-[#6d335b] underline underline-offset-2">Manage wearers</Link>
    </div>
    <div className="m-4 flex items-center justify-between rounded-2xl bg-slate-50 p-3">
      <Link href="/profile" onClick={onNavigate} className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#6d335b] text-xs font-semibold text-white">AU</div>
        <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">Account</p><p className="text-xs text-slate-500">Private wardrobe</p></div>
      </Link>
      <span className="text-[10px] font-medium text-slate-400">Private</span>
    </div>
  </>;
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const closeSidebar = () => setIsSidebarOpen(false);
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState(false);
  const [wardrobeProfiles, setWardrobeProfiles] = useState<WardrobeProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const logoutPending = useRef(false);
  const signOut = async () => {
    if (logoutPending.current) return;
    logoutPending.current = true;
    setSigningOut(true);
    setLogoutError(false);
    const identity = getAccessToken();
    const finish = () => {
      if (getAccessToken() !== identity) return;
      clearAccessToken();
      window.location.assign("/auth");
    };
    try {
      if (identity) await logout(identity);
      finish();
    } catch (error) {
      if (getAccessToken() === identity) {
        if (error instanceof ApiError && error.status === 401) finish();
        else setLogoutError(true);
      }
    } finally {
      logoutPending.current = false;
      setSigningOut(false);
    }
  };

  useEffect(() => { if (pathname !== "/") leaveHomepageFlow(); }, [pathname]);

  useEffect(() => {
    if (pathname === "/auth" || !getAccessToken()) return;
    let active = true;
    const loadProfiles = () => { void getWardrobeProfiles().then((profiles) => {
        if (!active) return;
        const stored = getSelectedWardrobeProfileId();
        const selected = profiles.find((profile) => profile.id === stored) ?? profiles[0];
        setWardrobeProfiles(profiles);
        if (selected) { setSelectedProfileId(selected.id); setSelectedWardrobeProfileId(selected.id); }
      }).catch(() => { if (active) setWardrobeProfiles([]); }); };
    loadProfiles();
    window.addEventListener("smart-wardrobe-profiles-changed", loadProfiles);
    return () => { active = false; window.removeEventListener("smart-wardrobe-profiles-changed", loadProfiles); };
  }, [pathname]);

  const changeProfile = (profileId: string) => {
    setSelectedWardrobeProfileId(profileId);
    setSelectedProfileId(profileId);
    leaveHomepageFlow();
    window.location.reload();
  };

  useEffect(() => {
    if (!isSidebarOpen) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsSidebarOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [isSidebarOpen]);

  return (
    <div className="min-h-screen bg-[#f8f7f4] text-slate-900">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <header className="fixed inset-x-0 top-0 z-40 flex h-[72px] items-center justify-between border-b border-slate-200/90 bg-[#f8f7f4]/90 px-4 backdrop-blur-md sm:px-6 lg:left-[272px] lg:px-10">
        <button type="button" onClick={() => setIsSidebarOpen(true)} className="flex h-11 w-11 items-center justify-center rounded-xl text-slate-700 transition-colors hover:bg-white hover:text-[#6d335b] lg:hidden" aria-label="Open navigation menu" aria-expanded={isSidebarOpen} aria-controls="primary-navigation">
          <Menu className="h-5 w-5" />
        </button>
        <Link href="/" className="flex items-center lg:hidden">
          <Image src="/logo.png" alt="AURA" width={3420} height={1265} sizes="90px" style={{ height: 28, width: "auto" }} className="object-contain" priority />
        </Link>
        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          {pathname !== "/auth" && <button type="button" onClick={signOut} disabled={signingOut} aria-busy={signingOut} className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-white hover:text-[#6d335b] disabled:opacity-50 sm:px-3"><LogOut className="h-4 w-4" aria-hidden="true" /><span className="hidden sm:inline">{signingOut ? "Signing out…" : logoutError ? "Retry sign out" : "Sign out"}</span><span className="sr-only sm:hidden">{signingOut ? "Signing out…" : logoutError ? "Retry sign out" : "Sign out"}</span></button>}
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm sm:flex" aria-label="Private workspace">
            <ShieldCheck className="h-4 w-4 text-[#6d335b]" aria-hidden="true" />
            <span>Private workspace</span>
          </div>
        </div>
      </header>

      <aside className="fixed inset-y-0 left-0 z-50 hidden w-[272px] flex-col border-r border-slate-200 bg-white lg:flex"><SidebarContent pathname={pathname} onNavigate={closeSidebar} profiles={wardrobeProfiles} selectedProfileId={selectedProfileId} onProfileChange={changeProfile} /></aside>
      {isSidebarOpen && <aside id="primary-navigation" className="fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col border-r border-slate-200 bg-white shadow-xl lg:hidden"><SidebarContent pathname={pathname} onNavigate={closeSidebar} profiles={wardrobeProfiles} selectedProfileId={selectedProfileId} onProfileChange={changeProfile} mobile /></aside>}

      {isSidebarOpen && <button type="button" onClick={closeSidebar} className="fixed inset-0 z-40 bg-slate-900/30 lg:hidden" aria-label="Close navigation menu" />}
      <main id="main-content" tabIndex={-1} className="min-h-screen scroll-mt-24 px-4 pb-12 pt-[96px] sm:px-6 lg:ml-[272px] lg:px-10 lg:pt-[112px]"><div className="mx-auto w-full max-w-[1440px]">{logoutError && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">Could not sign out. Your session was kept. Use Retry sign out to try again.</p>}{children}</div></main>
    </div>
  );
}
