"use client";

import React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Download, RefreshCw, Save } from "lucide-react";
import Layout from "@/components/Layout";

export default function OutfitVisualisationResultPage() {
  const searchParams = useSearchParams();
  const baseImageName = searchParams.get("name") || "Selected base image";

  return (
    <Layout>
      <div className="w-full space-y-7">
        <Link href="/try-on" className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition-colors hover:text-[#6d335b]">
          <ArrowLeft className="h-4 w-4" /> Back to base images
        </Link>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-4 border-b border-slate-100 pb-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-700"><CheckCircle2 className="h-4 w-4" /> Visualisation complete</div>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Your outfit preview</h1>
              <p className="mt-2 text-sm text-slate-500">Created from your selected base image and outfit suggestion.</p>
            </div>
            <span className="w-fit rounded-full bg-[#f5eaf1] px-3 py-1.5 text-xs font-semibold text-[#6d335b]">Ready to save</span>
          </div>

          <div className="mt-7 grid gap-7 lg:grid-cols-[minmax(0,1fr)_320px]">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-6">
              <div className="flex aspect-[4/5] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
                <div>
                  <p className="text-sm font-semibold text-slate-500">Completed outfit visualisation</p>
                  <p className="mt-1 text-xs text-slate-400">Image preview placeholder</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-slate-600">Base image: {baseImageName}</span>
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-slate-600">Outfit: Active essentials</span>
              </div>
            </section>

            <aside className="space-y-5">
              <div className="rounded-2xl bg-slate-50 p-5">
                <h2 className="text-base font-semibold text-slate-800">Outfit details</h2>
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3 text-sm"><span className="text-slate-500">Top</span><span className="font-medium text-slate-800">Graphic shirt</span></div>
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3 text-sm"><span className="text-slate-500">Bottom</span><span className="font-medium text-slate-800">Lounge pants</span></div>
                  <div className="flex items-center justify-between text-sm"><span className="text-slate-500">Accessory</span><span className="font-medium text-slate-800">Knit socks</span></div>
                </div>
              </div>

              <div className="grid gap-3">
                <button onClick={() => alert("Saved to your outfit collection.")} className="flex items-center justify-center gap-2 rounded-xl bg-[#263144] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#6d335b]"><Save className="h-4 w-4" /> Save visualisation</button>
                <button onClick={() => alert("Your download is ready.")} className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"><Download className="h-4 w-4" /> Download image</button>
                <Link href="/try-on" className="flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50"><RefreshCw className="h-4 w-4" /> Try another base image</Link>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </Layout>
  );
}
