"use client";
/* eslint-disable @next/next/no-img-element -- object URLs are created from authenticated protected-media responses. */

import { useEffect, useState } from "react";
import { getAccessToken, mediaUrl } from "@/lib/api";

type ProtectedImageProps = { mediaId: string; alt: string; className?: string };

export default function ProtectedImage({ mediaId, alt, className }: ProtectedImageProps) {
  const [result, setResult] = useState<{ mediaId: string; source?: string; error?: string }>();
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let objectUrl: string | undefined;
    const load = async () => {
      const token = getAccessToken();
      if (!token) { setResult({ mediaId, error: "Sign in to view this image." }); return; }
      const response = await fetch(mediaUrl(mediaId), { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal });
      if (!response.ok) throw new Error("Image unavailable. Try again.");
      objectUrl = URL.createObjectURL(await response.blob());
      if (!controller.signal.aborted) setResult({ mediaId, source: objectUrl });
    };
    load().catch(() => { if (!controller.signal.aborted) setResult({ mediaId, error: "Image unavailable. Try again." }); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [mediaId, retry]);
  const current = result?.mediaId === mediaId ? result : undefined;
  if (current?.error) return <div className={`${className ?? ""} flex flex-col items-center justify-center gap-2 bg-slate-100 p-3 text-center text-xs text-slate-600`} role="status"><p>{current.error}</p><button type="button" onClick={() => setRetry((value) => value + 1)} className="min-h-10 rounded-lg px-3 font-semibold underline">Retry image</button></div>;
  return current?.source
    ? <img src={current.source} alt={alt} className={className} decoding="async" />
    : <div className={`${className ?? ""} ui-skeleton flex items-center justify-center bg-slate-100 p-3 text-center text-xs text-slate-500`} role="status" aria-label={`Loading ${alt}`}>Loading image…</div>;
}
