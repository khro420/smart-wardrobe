'use client';

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { useState } from "react";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <div className="flex">
          {/* Collapsible Sidebar */}
          <aside
            className={`hidden md:flex flex-col h-screen fixed left-0 top-0 bg-surface z-50 py-8 px-6 space-y-8 transition-all duration-300 ease-in-out ${
              sidebarOpen ? 'w-72' : 'w-20'
            }`}
          >
            <div className="mb-4 flex items-center justify-between">
              {sidebarOpen && (
                <div>
                  <h1 className="font-display text-3xl font-black text-on-surface tracking-tighter">
                    AURA
                  </h1>
                  <p className="font-label text-[10px] tracking-widest text-on-surface-variant uppercase mt-1 opacity-60">
                    The Digital Atelier
                  </p>
                </div>
              )}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-surface-container-high rounded-lg transition-colors flex-shrink-0"
              >
                <span className="material-symbols-outlined text-on-surface">
                  {sidebarOpen ? 'menu_open' : 'menu'}
                </span>
              </button>
            </div>
            <nav className="flex flex-col space-y-2 flex-grow">
              <a
                className="flex items-center space-x-3 text-on-secondary-container bg-secondary-container rounded-lg font-bold px-4 py-3 scale-105 duration-200 ease-in-out hover:no-underline justify-center md:justify-start"
                href="/"
                title="Home"
              >
                <span
                  className="material-symbols-outlined flex-shrink-0"
                  style={{ fontVariationSettings: '"FILL" 1' }}
                >
                  home
                </span>
                {sidebarOpen && <span className="font-label tracking-wider">Home</span>}
              </a>
              <a
                className="flex items-center space-x-3 text-on-surface-variant hover:text-on-surface px-4 py-3 hover:bg-surface-container-high transition-colors duration-200 rounded-lg justify-center md:justify-start"
                href="/wardrobe"
                title="Wardrobe"
              >
                <span className="material-symbols-outlined flex-shrink-0">dry_cleaning</span>
                {sidebarOpen && <span className="font-label tracking-wider">Wardrobe</span>}
              </a>
              <a
                className="flex items-center space-x-3 text-on-surface-variant hover:text-on-surface px-4 py-3 hover:bg-surface-container-high transition-colors duration-200 rounded-lg justify-center md:justify-start"
                href="/studio"
                title="Studio"
              >
                <span className="material-symbols-outlined flex-shrink-0">checkroom</span>
                {sidebarOpen && <span className="font-label tracking-wider">Studio</span>}
              </a>
              <a
                className="flex items-center space-x-3 text-on-surface-variant hover:text-on-surface px-4 py-3 hover:bg-surface-container-high transition-colors duration-200 rounded-lg justify-center md:justify-start"
                href="/curations"
                title="Curations"
              >
                <span className="material-symbols-outlined flex-shrink-0">auto_stories</span>
                {sidebarOpen && <span className="font-label tracking-wider">Curations</span>}
              </a>
              <a
                className="flex items-center space-x-3 text-on-surface-variant hover:text-on-surface px-4 py-3 hover:bg-surface-container-high transition-colors duration-200 rounded-lg justify-center md:justify-start"
                href="/settings"
                title="Settings"
              >
                <span className="material-symbols-outlined flex-shrink-0">settings</span>
                {sidebarOpen && <span className="font-label tracking-wider">Settings</span>}
              </a>
            </nav>
            <div className="flex flex-col space-y-4 pt-8">
              <button
                className="satin-gradient text-on-primary py-4 px-6 rounded-xl font-bold flex items-center justify-center space-x-2 shadow-lg shadow-primary/20 hover:opacity-90 transition-all active:scale-95"
                title="New Collection"
              >
                <span className="material-symbols-outlined flex-shrink-0">add_circle</span>
                {sidebarOpen && <span>New Collection</span>}
              </button>
              {sidebarOpen && (
                <div className="flex flex-col space-y-1">
                  <a
                    className="flex items-center space-x-3 text-on-surface-variant hover:text-on-surface px-4 py-2 text-sm transition-colors"
                    href="#"
                  >
                    <span className="material-symbols-outlined text-sm">help</span>
                    <span className="font-label">Support</span>
                  </a>
                  <a
                    className="flex items-center space-x-3 text-on-surface-variant hover:text-on-surface px-4 py-2 text-sm transition-colors"
                    href="#"
                  >
                    <span className="material-symbols-outlined text-sm">person</span>
                    <span className="font-label">Account</span>
                  </a>
                </div>
              )}
            </div>
          </aside>
          {/* Main Content */}
          <main
            className={`flex-1 transition-all duration-300 ease-in-out ${
              sidebarOpen ? 'md:ml-72' : 'md:ml-20'
            }`}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
