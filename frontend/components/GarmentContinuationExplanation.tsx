import type { IntegratedRecommendation } from "@/lib/api";

export default function GarmentContinuationExplanation({ recommendation }: { recommendation: IntegratedRecommendation }) {
  const sequence = recommendation.garment_continuation;
  return <>
    {recommendation.garment_wording && <p role="note" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">{recommendation.garment_wording.message}</p>}
    {sequence && <section aria-label="Garment recommendation sequence" className="space-y-2 rounded-xl border p-4 text-sm">
      <h4 className="font-semibold">{sequence.ordinal === 0 ? "Initial garment option" : `Garment alternative ${sequence.ordinal}`}</h4>
      <p>The original garment requirements and wearer restrictions still apply. Changing only outerwear does not count as a new outfit base.</p>
      <p>Request match is Not applicable for this garment-only request and contributes 0. The original contribution floor is 0; the scoring weights remain unchanged.</p>
      {sequence.limit_reached && <p>The ten-result limit has been reached. This does not mean every eligible outfit has been exhausted.</p>}
    </section>}
  </>;
}
