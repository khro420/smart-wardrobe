"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getCompletedChat, type CompletedChat } from "@/lib/api";
import { errorMessage } from "@/lib/recommendation-messages";
import RecommendationResult from "./RecommendationResult";

export default function CompletedChatView({ chatId }: { chatId: string }) {
  const [chat,setChat] = useState<CompletedChat>();
  const [error,setError] = useState("");
  useEffect(() => {
    let active = true;
    getCompletedChat(chatId).then(value => { if (active) setChat(value); }).catch(cause => { if (active) setError(errorMessage(cause)); });
    return () => { active = false; };
  },[chatId]);
  return <div className="space-y-5"><Link href="/history" className="inline-flex min-h-11 items-center text-sm font-semibold underline">Back to history</Link><h1 className="text-3xl font-semibold">Completed interaction</h1>
    {error ? <p role="alert" className="text-rose-800">{error}</p> : !chat ? <p role="status">Loading saved interaction…</p> : <>
      <section className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-sm font-semibold text-slate-500">Original request · read-only</h2><p className="mt-2 whitespace-pre-wrap">{chat.request_text}</p></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Saved interpretation</h2>{chat.structured_request ? <dl className="mt-3 grid gap-3 sm:grid-cols-2">{["occasion","style","colours","garment_categories","formality"].map(field => <div key={field}><dt className="text-sm capitalize text-slate-500">{field.replaceAll("_"," ")}</dt><dd className="text-sm">{chat.structured_request?.[field] == null ? "Not supplied" : typeof chat.structured_request[field] === "string" ? String(chat.structured_request[field]).replaceAll("_"," ") : JSON.stringify(chat.structured_request[field])}</dd></div>)}</dl> : <p className="mt-2 text-sm text-slate-600">Structured interpretation is unavailable for this older record.</p>}</section>
      <RecommendationResult key={chat.recommendation.id} recommendation={chat.recommendation} historical historicalActions />
      <Link href="/assistant" className="inline-flex min-h-11 items-center text-sm font-semibold underline">Open Outfit Assistant</Link>
    </>}
  </div>;
}
