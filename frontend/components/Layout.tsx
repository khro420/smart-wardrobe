"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, CloudSun, Home, Shirt, PlusCircle, LogOut, User } from "lucide-react";
import Image from "next/image";

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const navItems = [
    { href: "/", label: "HOME // SUGGESTIONS", icon: Home },
    { href: "/wardrobe", label: "MY WARDROBE // ARCHIVE", icon: Shirt },
    { href: "/extract", label: "EXTRACT OUTFIT // GEN", icon: PlusCircle },
    { href: "/profile", label: "AI PROFILE // IDENTITY", icon: User },
  ];

  return (
    <div className="min-h-screen bg-zinc-50 text-black flex flex-col w-full relative overflow-x-hidden antialiased">

      {/* Brutalist Top Navbar */}
      <header className="w-full bg-white border-b-4 border-black px-6 py-4 flex items-center justify-between fixed top-0 left-0 right-0 z-40">

        {/* Left Side: Raw Square Menu Trigger */}
        <div className="flex items-center z-10">
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 border-2 border-black bg-white hover:bg-black hover:text-white text-black transition-colors"
            aria-label="Open Navigation Menu"
          >
            <Menu className="w-6 h-6 stroke-[3]" />
          </button>
        </div>

        {/* Center Zone: Logo Position */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <Link href="/" className="flex items-center pointer-events-auto">
            <Image
              src="/logo.png"
              alt="AURA Logo"
              width={130}
              height={32}
              className="object-contain h-8 w-auto mix-blend-multiply"
              priority
            />
          </Link>
        </div>

        {/* Right Side: Industrial Weather Badge */}
        <div className="flex items-center gap-2 text-black bg-white border-2 border-black px-3 py-1.5 text-xs font-mono font-black uppercase shadow-[2px_2px_0px_0px_#000000] z-10">
          <CloudSun className="w-4 h-4 stroke-[2.5]" />
          <span>22°C // SYS</span>
        </div>
      </header>

      {/* Drawer Sidebar (Neo-Brutalist Block) */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-72 bg-white border-r-4 border-black flex flex-col justify-between h-screen transition-transform duration-200 ease-in-out
        ${isSidebarOpen ? "translate-x-0 shadow-[8px_0px_0px_0px_rgba(0,0,0,1)]" : "-translate-x-full"}
      `}>
        <div>
          {/* Sidebar Header with Raw Close Interaction */}
          <div className="flex items-center justify-between p-5 border-b-4 border-black bg-black text-white">
            <Link href="/" onClick={() => setIsSidebarOpen(false)} className="flex items-center invert">
              <Image
                src="/logo.png"
                alt="AURA Logo"
                width={130}
                height={36}
                className="object-contain h-9 w-auto"
              />
            </Link>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-1.5 border-2 border-white hover:bg-white hover:text-black text-white transition-colors"
              aria-label="Close menu"
            >
              <X className="w-5 h-5 stroke-[3]" />
            </button>
          </div>

          {/* Zine/Streetwear Navigation Stack */}
          <nav className="p-4 space-y-3">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsSidebarOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3.5 border-2 border-black text-xs font-mono font-black uppercase transition-all tracking-wider ${isActive
                      ? "bg-black text-white shadow-[4px_4px_0px_0px_#27272a] translate-x-0.5 translate-y-0.5"
                      : "bg-white text-black hover:bg-zinc-100 hover:shadow-[3px_3px_0px_0px_#000000]"
                    }`}
                >
                  <Icon className="w-4 h-4 shrink-0 stroke-[3]" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Industrial Account Module at Base linking to Profile */}
        <div className="p-4 border-t-4 border-black flex items-center justify-between bg-zinc-50">
          <Link 
            href="/profile"
            onClick={() => setIsSidebarOpen(false)}
            className="flex items-center gap-3 group focus:outline-hidden"
          >
            <div className="w-10 h-10 bg-black text-white border-2 border-black flex items-center justify-center text-sm font-mono font-black shrink-0 shadow-[2px_2px_0px_0px_rgba(0,0,0,0.2)] group-hover:bg-zinc-800 transition-colors">
              U_1
            </div>
            <div>
              <p className="text-xs font-mono font-black text-black uppercase group-hover:underline decoration-2">// DEMO_USER</p>
              <p className="text-[9px] font-mono font-bold text-zinc-500 uppercase tracking-wider">ROOT_ACCESS_PREMIUM</p>
            </div>
          </Link>
          <button
            onClick={() => alert("Logging out...")}
            className="text-zinc-400 hover:text-white hover:bg-rose-600 border-2 border-transparent hover:border-black p-2 transition-colors"
            title="Log Out"
          >
            <LogOut className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>
      </aside>

      {/* Heavy Screen-Wash Backdrop */}
      {isSidebarOpen && (
        <div
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 z-40 transition-opacity animate-in fade-in duration-150"
        />
      )}

      {/* Layout Grid Mainframe Container */}
      <main className="flex-1 w-full p-6 md:p-10 pt-[100px] md:pt-[120px]">
        <div className="max-w-5xl mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}