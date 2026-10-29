"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { getChatHistory, type ChatPage } from "@/lib/api";
import { errorMessage } from "@/lib/recommendation-messages";

export default function RecommendationHistoryPage() {
  const [input,setInput] = useState("");
  const [term,setTerm] = useState("");
  const [page,setPage] = useState<{ term: string; value: ChatPage }>();
  const [error,setError] = useState<{ term: string; message: string }>();
  const [loadingMore,setLoadingMore] = useState(false);
  const generation = useRef(0);
  const moreBusy = useRef(false);
  useEffect(() => {
    let active = true;
    const version = generation.current;
    getChatHistory(term).then(value => { if (active && version === generation.current) setPage({ term,value }); }).catch(cause => { if (active && version === generation.current) setError({ term,message:errorMessage(cause) }); });
    return () => { active = false; };
  },[term]);
  const current = page?.term === term ? page.value : undefined;
  const message = error?.term === term ? error.message : "";
  const more = async () => {
    if (!current?.next_cursor || moreBusy.current) return;
    const version = generation.current;
    moreBusy.current = true; setLoadingMore(true);
    try {
      const next = await getChatHistory(term,current.next_cursor);
      if (version === generation.current) setPage({ term,value:{ ...next,items:[...current.items,...next.items] } });
    } catch (cause) { if (version === generation.current) setError({ term,message:errorMessage(cause) }); }
    finally { moreBusy.current = false; setLoadingMore(false); }
  };
  const search = () => {
    if (input === term) return;
    generation.current++; setError(undefined); setTerm(input);
  };
  return <Layout><div className="space-y-5"><h1 className="text-3xl font-semibold">Recommendation history</h1><p className="text-sm text-slate-600">Search your completed, read-only requests. Opening history never generates a new outfit.</p>
    <form onSubmit={event => { event.preventDefault(); search(); }} className="flex flex-wrap items-end gap-3"><label className="flex-1 text-sm font-semibold">Search original requests<input value={input} onChange={event => setInput(event.target.value)} maxLength={500} className="mt-1 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3" /></label><button className="min-h-11 rounded-xl bg-[#6d335b] px-4 text-sm font-semibold text-white">Search history</button></form>
    {message && <p role="alert" className="text-sm text-rose-800">{message}</p>}
    {!current && !message && <p role="status">Loading history…</p>}
    {current && <><p role="status" className="text-sm text-slate-500">{current.total} completed interaction{current.total === 1 ? "" : "s"}{term ? ` matching “${term}”` : ""}</p>
      {!current.items.length ? <p className="rounded-xl bg-white p-5 text-sm text-slate-600">No completed chats found.</p> : <div className="grid gap-4 md:grid-cols-2">{current.items.map(chat => <article key={chat.chat_id} className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-xs text-slate-500">{new Date(chat.created_at).toLocaleString()} · Read-only</p><h2 className="mt-2 whitespace-pre-wrap font-semibold">{chat.request_text}</h2><Link href={`/history/${encodeURIComponent(chat.chat_id)}`} className="mt-3 inline-flex min-h-11 items-center text-sm font-semibold underline">Open completed interaction</Link></article>)}</div>}
      {current.next_cursor && <button disabled={loadingMore} onClick={() => void more()} className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold disabled:opacity-50">{loadingMore ? "Loading more…" : "Load more chats"}</button>}
    </>}
  </div></Layout>;
}
