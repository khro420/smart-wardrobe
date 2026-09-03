"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, CloudSun, Home, Shirt, PlusCircle, LogOut, User } from "lucide-react";
import Image from "next/image";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/wardrobe", label: "My wardrobe", icon: Shirt },
  { href: "/extract", label: "Add an outfit", icon: PlusCircle },
  { href: "/profile", label: "Profile", icon: User },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="min-h-screen bg-[#f8f7f4] text-slate-900">
      <header className="fixed inset-x-0 top-0 z-40 flex h-[72px] items-center justify-between border-b border-slate-200/90 bg-[#f8f7f4]/90 px-4 backdrop-blur-md sm:px-6 lg:left-[272px] lg:px-10">
        <button onClick={() => setIsSidebarOpen(true)} className="rounded-xl p-2 text-slate-700 transition-colors hover:bg-white hover:text-[#6d335b] lg:hidden" aria-label="Open navigation menu">
          <Menu className="h-5 w-5" />
        </button>
        <Link href="/" className="flex items-center lg:hidden">
          <Image src="/logo.png" alt="AURA" width={112} height={28} className="h-7 w-auto object-contain" priority />
        </Link>
        <div className="ml-auto flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm">
          <CloudSun className="h-4 w-4 text-amber-500" />
          <span>22°C</span>
        </div>
      </header>

      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col border-r border-slate-200 bg-white transition-transform duration-200 ease-out lg:translate-x-0 ${isSidebarOpen ? "translate-x-0 shadow-xl" : "-translate-x-full"}`}>
        <div className="flex h-[88px] items-center justify-between px-6">
          <Link href="/" onClick={closeSidebar} className="flex items-center">
            <Image src="/logo.png" alt="AURA" width={122} height={30} className="h-8 w-auto object-contain" priority />
          </Link>
          <button onClick={closeSidebar} className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 lg:hidden" aria-label="Close navigation menu">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-4 py-5">
          <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Your space</p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} onClick={closeSidebar} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors ${isActive ? "bg-[#f5eaf1] text-[#6d335b]" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}`}>
                <Icon className="h-[18px] w-[18px]" strokeWidth={isActive ? 2.4 : 2} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="m-4 flex items-center justify-between rounded-2xl bg-slate-50 p-3">
          <Link href="/profile" onClick={closeSidebar} className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#6d335b] text-xs font-semibold text-white">AU</div>
            <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">Demo user</p><p className="text-xs text-slate-500">Premium plan</p></div>
          </Link>
          <button onClick={() => alert("Logging out...")} className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white hover:text-rose-600" title="Log out" aria-label="Log out"><LogOut className="h-4 w-4" /></button>
        </div>
      </aside>

      {isSidebarOpen && <button onClick={closeSidebar} className="fixed inset-0 z-40 bg-slate-900/30 lg:hidden" aria-label="Close navigation menu" />}
      <main className="min-h-screen px-4 pb-10 pt-[96px] sm:px-6 lg:ml-[272px] lg:px-10 lg:pt-[112px]"><div className="w-full">{children}</div></main>
    </div>
  );
}
