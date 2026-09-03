"use client";

import React, { useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Plus, Sparkles } from "lucide-react";
import Layout from "@/components/Layout";

type BaseImage = { id: number; label: string; detail: string };

const SAVED_BASE_IMAGES: BaseImage[] = [
  { id: 1, label: "Full-length photo", detail: "Added 12 Jun 2026" },
  { id: 2, label: "Mirror photo", detail: "Added 28 May 2026" },
];

export default function OutfitVisualisationPage() {
  const [baseImages, setBaseImages] = useState(SAVED_BASE_IMAGES);
  const [selectedImageId, setSelectedImageId] = useState(SAVED_BASE_IMAGES[0].id);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedImage = baseImages.find((image) => image.id === selectedImageId);

  const addBaseImage = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const nextImage = {
      id: Date.now(),
      label: file.name.replace(/\.[^/.]+$/, "") || "New base image",
      detail: "Added just now",
    };
    setBaseImages((images) => [...images, nextImage]);
    setSelectedImageId(nextImage.id);
    event.target.value = "";
  };

  return (
    <Layout>
      <div className="w-full space-y-7">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition-colors hover:text-[#6d335b]">
          <ArrowLeft className="h-4 w-4" /> Back to outfit ideas
        </Link>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="mb-8 max-w-2xl">
            <p className="text-sm font-semibold text-[#6d335b]">Outfit visualisation</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Choose a base image</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">Select a saved photo of yourself, then create a visualisation of this outfit on that image.</p>
          </div>

          <div className="grid gap-7 lg:grid-cols-[1.1fr_0.9fr]">
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-800">Saved base images</h2>
                <span className="text-xs text-slate-400">{baseImages.length} saved</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {baseImages.map((image) => {
                  const selected = image.id === selectedImageId;
                  return (
                    <button
                      key={image.id}
                      onClick={() => setSelectedImageId(image.id)}
                      className={`relative min-h-48 rounded-2xl border p-4 text-left transition-all ${selected ? "border-[#6d335b] bg-[#fcf7fa] ring-2 ring-[#6d335b]/15" : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"}`}
                    >
                      <div className="flex h-28 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-center text-xs font-medium text-slate-400">
                        Base image placeholder
                      </div>
                      <p className="mt-3 text-sm font-semibold text-slate-800">{image.label}</p>
                      <p className="mt-1 text-xs text-slate-500">{image.detail}</p>
                      {selected && <span className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-[#6d335b] text-white"><Check className="h-4 w-4" /></span>}
                    </button>
                  );
                })}

                <button onClick={() => fileInputRef.current?.click()} className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-center text-slate-500 transition-colors hover:border-[#6d335b] hover:bg-[#fcf7fa] hover:text-[#6d335b]">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm"><Plus className="h-5 w-5" /></span>
                  <span className="mt-3 text-sm font-semibold">Add a new base image</span>
                  <span className="mt-1 text-xs">Upload a clear photo of yourself</span>
                </button>
                <input ref={fileInputRef} onChange={addBaseImage} type="file" accept="image/*" className="hidden" />
              </div>
            </section>

            <aside className="rounded-2xl bg-slate-50 p-5">
              <div className="flex h-36 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white text-center text-sm font-medium text-slate-400">
                Outfit placeholder
              </div>
              <h2 className="mt-5 text-base font-semibold text-slate-800">Ready to visualise</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">Your selected base image will be paired with the outfit from this suggestion.</p>
              <div className="mt-5 rounded-xl border border-slate-200 bg-white p-3">
                <p className="text-xs text-slate-400">Selected base image</p>
                <p className="mt-1 text-sm font-semibold text-slate-700">{selectedImage?.label}</p>
              </div>
              <Link href={`/try-on/result?base=${selectedImageId}&name=${encodeURIComponent(selectedImage?.label ?? "Selected base image")}`} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-[#263144] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#6d335b]">
                <Sparkles className="h-4 w-4" /> Create visualisation
              </Link>
            </aside>
          </div>
        </div>
      </div>
    </Layout>
  );
}
