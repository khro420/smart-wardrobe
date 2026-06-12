export default function Home() {
  return (
    <>
      <link
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
        rel="stylesheet"
      />
      <style
        dangerouslySetInnerHTML={{
          __html:
            "\n        .font-serif { font-family: 'Noto Serif', serif; }\n        .glass { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px); color: #171717; }\n        .glass h3 { color: #171717; }\n        .glass p { color: #49454e; }\n        .glass span { color: inherit; }\n        .satin-gradient { background: linear-gradient(45deg, #5F5E5E 0%, #9F9E9E 100%); }\n        .hide-scrollbar::-webkit-scrollbar { display: none; }\n        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }\n    "
        }}
      />
      {/* Header / Greeting */}
      <header className="pt-12 px-10 flex justify-between items-end">
          <div>
            <p className="font-label text-sm uppercase tracking-[0.2em] text-secondary font-semibold mb-2">
              London — 18°C Sunny
            </p>
            <h2 className="font-display text-5xl font-light text-on-surface -ml-1">
              Good Morning, Alexander.
            </h2>
          </div>
          <div className="flex items-center space-x-4 mb-2">
            <button className="p-3 bg-surface-container-low rounded-full hover:bg-surface-container-high transition-colors">
              <span className="material-symbols-outlined">search</span>
            </button>
            <button className="p-3 bg-surface-container-low rounded-full hover:bg-surface-container-high transition-colors relative">
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute top-3 right-3 w-2 h-2 bg-error rounded-full" />
            </button>
            <div className="w-12 h-12 rounded-full overflow-hidden bg-surface-container-high ml-4">
              <img
                alt="User"
                className="w-full h-full object-cover"
                data-alt="A professional studio headshot of a stylish man in his early 30s with a clean-cut appearance. He is wearing a minimalist charcoal gray cashmere sweater. The lighting is soft and directional, typical of high-end editorial photography, against a neutral light gray background. The aesthetic is sophisticated, clean, and perfectly aligned with a luxury digital fashion platform."
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAYHrtms3mjTrqIMenfrbSG9Mf4YjA1noWgNtfa69ncryGZVZfzpZOwf1eQ0VMsipkOSnm8U-Rw3UMyCUulnHbfjKkIcRLkRGgO-MRoDoFyAIwmYXy26cCtrdFSeddJ_iV6va8Eux2wj5LwJR6iyCDfsr--tCZfmSAY_FrOToc4NrGbyAb4HSf3ONiBB4rFNgfuF3VUxm5N6uwYRJp9Dlc2wozqpgYaDSNjqrb3FGHo37qY-hQO0Bql7qcNy2M5JmMoeAIvq-RIB1U8"
              />
            </div>
          </div>
        </header>
        {/* Hero Section: Daily Recommendation */}
        <section className="mt-16 px-10">
          <div className="relative w-full h-[600px] overflow-hidden rounded-xl">
            <img
              className="w-full h-full object-cover"
              data-alt="A cinematic, full-body editorial photograph of a high-end fashion outfit styled for a crisp spring day. The look features a structured beige trench coat layered over a white organic cotton shirt and tailored sage green trousers. The setting is a minimalist architectural courtyard with soft morning sunlight casting long shadows. The color palette is composed of muted earth tones and soft whites, reflecting a premium and curated aesthetic."
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuA6z-GFCT6Awvf1j_68ml9Qbs1oVVBg75YFTgXSjyGYJO0Ql-CqOw84WvXyaWccVzV6ii6TQV3jG9kphrKZL9K_eKDr4BNTuGHDV9fewinE9PJPImqSeb-b3b8-3keMB_m7H_HEJpgac1BZHSRe_oCpPIfSFenlmm0vYUKco8QxMGF_y2fwrWU5ljk2K94BGvor0xCSd-mTzAdKdu1-ZO7Y092jLkZOMyEVYajypVhWe3z3gKKWufDXHRFa_qhbm55_SluUgBdsKnBx"
            />
            {/* Glass Overlay Info */}
            <div className="absolute bottom-10 left-10 p-8 glass rounded-xl max-w-lg">
              <div className="flex items-center space-x-2 mb-4">
                <span className="bg-secondary text-on-secondary text-[10px] px-2 py-1 rounded font-bold tracking-widest uppercase">
                  AI Recommended
                </span>
                <span className="text-on-surface-variant text-xs font-medium">
                  Matching your schedule: 3 Meetings
                </span>
              </div>
              <h3 className="font-display text-4xl mb-4 leading-tight">
                The Modern Professional
              </h3>
              <p className="text-on-surface-variant font-body mb-8 leading-relaxed">
                A refined balance of structure and breathability. Today's curation
                pairs our heritage wool-blend blazer with relaxed-fit chinos to
                navigate the city's shifting temperatures.
              </p>
              <div className="flex space-x-4">
                <button className="bg-primary text-on-primary px-8 py-3 rounded-lg font-semibold hover:opacity-90 transition-opacity">
                  View Ensemble
                </button>
                <button className="text-primary px-4 py-3 rounded-lg font-semibold flex items-center space-x-2 border border-outline-variant hover:bg-surface-container-low transition-all">
                  <span className="material-symbols-outlined text-sm">shuffle</span>
                  <span>Re-style</span>
                </button>
              </div>
            </div>
          </div>
        </section>
        {/* Recent Additions: Horizontal Scroll */}
        <section className="mt-24 pl-10 overflow-hidden">
          <div className="flex justify-between items-baseline pr-10 mb-8">
            <h4 className="font-display text-2xl">Recent Additions</h4>
            <a
              className="text-secondary font-label text-sm font-semibold hover:underline"
              href="#"
            >
              Browse Wardrobe
            </a>
          </div>
          <div className="flex space-x-6 overflow-x-auto hide-scrollbar pb-10">
            {/* Item 1 */}
            <div className="flex-shrink-0 w-64 group cursor-pointer">
              <div className="aspect-[3/4] rounded-lg overflow-hidden bg-surface-container-low mb-4 relative">
                <img
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  data-alt="A minimalist studio photograph of a premium navy blue textured knit polo shirt. The garment is presented against a clean white backdrop with soft, diffused lighting that highlights the intricate weave of the fabric. The aesthetic is clean, sharp, and focused on material quality, reflecting the luxury curation of the AURA platform."
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuAwhjZUqNbqhbRqPTqZBhkGQ0MpWUPZ__OnunOQA1xpY3PU9yxKuUMcd8NxEl9Z9lqO-E9cRFre_lznOWdknMNuZuOx9e3pNsIyoClo74YuIVjEImDZiGg_QBt5w4BzVo-o3iV09fRvhBdvw_KuBKGsb-Pxn8vrPoYC6O4mLZClU4hFKAhTREGiSZ3-uUn7h-q5Lhm_HOI-q_QaXHThz719AKlseii0Ubv9Ab6s5YSaljm5k-YHFsLcE-FSJXPt7WxZovyC--g914IR"
                />
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="w-8 h-8 bg-white/90 rounded-full flex items-center justify-center shadow-md">
                    <span className="material-symbols-outlined text-primary text-lg">
                      favorite
                    </span>
                  </button>
                </div>
              </div>
              <p className="font-label text-xs uppercase tracking-widest text-secondary font-bold">
                Loro Piana
              </p>
              <h5 className="font-body text-sm text-on-surface-variant mt-1">
                Cashmere Knit Polo
              </h5>
            </div>
            {/* Item 2 */}
            <div className="flex-shrink-0 w-64 group cursor-pointer">
              <div className="aspect-[3/4] rounded-lg overflow-hidden bg-surface-container-low mb-4 relative">
                <img
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  data-alt="A detailed shot of tailored slate gray trousers made from high-quality tropical wool. The image focuses on the sharp crease and the subtle texture of the fabric, set in a brightly lit studio environment with neutral tones. The mood is professional and elegant, emphasizing the sophisticated craftsmanship of the digital atelier's collection."
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuAisfYwchMpCqc52vlOICqhqgRuUccRoIwsojRx1xKYB8eQSkOGzEZFjh2qEM_wzRohUg7Uz7RhiB0lSciZ3JTFqbH3Bu0QYxMxuBkvLbFbOPmY6SxcuROL8m_ejetNHu35_zG6zkx-k3rlLX6ijkS_bTFxzAIgqGee1mgWPA53NaoefQJv9Z20pDQvBvTakngDw2c0wB282vJxbSKsyJz8vgcqFjNoWKhNd3jY-jCDfUuPALaLcL2eF4S5pjlCkB_jgdqFZpoMuZs-"
                />
              </div>
              <p className="font-label text-xs uppercase tracking-widest text-secondary font-bold">
                Acne Studios
              </p>
              <h5 className="font-body text-sm text-on-surface-variant mt-1">
                Tropical Wool Trousers
              </h5>
            </div>
            {/* Item 3 */}
            <div className="flex-shrink-0 w-64 group cursor-pointer">
              <div className="aspect-[3/4] rounded-lg overflow-hidden bg-surface-container-low mb-4 relative">
                <img
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  data-alt="A close-up photograph of a pair of minimalist white leather sneakers with a gum sole. The shoes are staged in a clean, high-key lighting setup that accentuates their sleek silhouette and premium materials. The overall aesthetic is bright, modern, and high-end, fitting a curated digital fashion experience."
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuDXZgZAVI4rvaxAks1eodmfZOMP2LagvNl_xHSNTSfdV8kNouIizPNRJmyGsFGeZLoSe8QWRK9ul5QyoRkz-epoy8ff8hOjZm9LosJzzK_zgtjpQu_lTB1G7veQK4i6Y8AG1s3QBIHhAQianhUF97ygDx6hkQ2C-bZlU54MRJDWaOseMY50bHnMwq6SsT3EGoiKs4pT1HTciLQFzPIfQm1ijmgJyp4H28NoHXyRVhro7J8HH5JlDaa3EnALUBILLmnfMXfskwDfkWD-"
                />
              </div>
              <p className="font-label text-xs uppercase tracking-widest text-secondary font-bold">
                Common Projects
              </p>
              <h5 className="font-body text-sm text-on-surface-variant mt-1">
                Achilles Low White
              </h5>
            </div>
            {/* Item 4 */}
            <div className="flex-shrink-0 w-64 group cursor-pointer">
              <div className="aspect-[3/4] rounded-lg overflow-hidden bg-surface-container-low mb-4 relative">
                <img
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  data-alt="A luxurious camel-colored overcoat displayed on a minimalist wooden hanger. The fabric's rich texture is visible under soft studio lighting, creating a warm and sophisticated atmosphere. The image emphasizes timeless elegance and quality, adhering to a minimalist editorial style for a premium fashion application."
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuClAU0qZ_XCPpVmzSJ0ps8LG-Kiew3l1fKmFVWo9q0chLYpnv2OGT-aXPwuQxbSQQ-CCrEQQMnNJYsgaSqDABjt_m-4KzWjQNi_DPlfFV3vmaeteYmcSmxQe4i18JZ3G6kUZPUXfcYyH7lCIHraBBHBypRAbJvryXslUw5hHQga6oRAzrMgnsyjnnH4d_ew_2EDLfglzPKXSupeMik7wXdVyWqDkZT8c-KPDIczB6lZJTudU3ngJ440uX8cPaeDuwoSb5JVo3HoGhxG"
                />
              </div>
              <p className="font-label text-xs uppercase tracking-widest text-secondary font-bold">
                Jil Sander
              </p>
              <h5 className="font-body text-sm text-on-surface-variant mt-1">
                Structured Wool Coat
              </h5>
            </div>
            {/* Item 5 */}
            <div className="flex-shrink-0 w-64 group cursor-pointer">
              <div className="aspect-[3/4] rounded-lg overflow-hidden bg-surface-container-low mb-4 relative">
                <img
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  data-alt="A premium black leather belt with a minimalist silver buckle, laid flat on a textured light gray surface. The lighting is sharp, creating subtle shadows that define the leather's grain and the metal's polish. This accessory shot is styled with a high-end, professional catalog look in mind."
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuCeuomwYYJeWm2P-Qg_2DfbaDILoPKzPY1Il3rLtT-ghncl_A8bLuAb_L7uHK3L2MXdntehxt_YVdCcJWgn9-aZk7yhE2j462RKI3_ioISVvS5LvRIzwaPZy4wWsFuacV9A3p0vL0usCchnWS_hpv3bCvTwn0XTS8LRfkEMNPNeZS7Czm8b3xJ55TEJfqYvnIS6dpkrR7jzgsFXIUx22uj8NoOGe0P_cHpC0bD8vUClqkjApsXN24giIF9noXRXQpAydpsXdno14mfn"
                />
              </div>
              <p className="font-label text-xs uppercase tracking-widest text-secondary font-bold">
                Saint Laurent
              </p>
              <h5 className="font-body text-sm text-on-surface-variant mt-1">
                Cinturon Narrow Belt
              </h5>
            </div>
          </div>
        </section>
        {/* Evening Selections: Asymmetric Grid */}
        <section className="mt-16 px-10 mb-32">
          <div className="bg-surface-container-low rounded-3xl p-12">
            <div className="max-w-2xl mb-12">
              <h4 className="font-display text-4xl mb-4">Evening Selections</h4>
              <p className="text-on-surface-variant leading-relaxed">
                Transition into night with curated ensembles designed for your
                dinner engagement at Sketch. The AI has considered the venue's dress
                code and the cooler evening forecast.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Card 1 */}
              <div className="md:col-span-2 relative group h-[500px] rounded-xl overflow-hidden shadow-sm">
                <img
                  className="w-full h-full object-cover"
                  data-alt="A moody, high-contrast editorial photograph of a sharp black velvet tuxedo ensemble for a night event. The lighting is low and sophisticated, featuring warm golden accents that mimic a luxury lounge environment. The image focuses on the opulent texture of the velvet and the crispness of a white pleated shirt. The mood is exclusive, evening-ready, and ultra-premium."
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuAj8DAhfhY6D9Inedrnt-ccwNlsv9wtkFbl5FQWRMuD8y1nJ3Us7TfN8Vcy2J49sTC6oKHIZnVYFq9WEne_JRJttTs52l-5B00OZkwo4Bwlyp4NR8Gxhcx1gHBZilXv6zpHvmUr_LkW4G-H9Oei1W8XK7yt1lhIdFs-CJYF5emsg66vAdqtiH9vWhVGOZ79wrQDYJI_EoMH1i8OGG8YxAkKVGHpO5qezD8V7ekrJywkUjmJVwp-6NoOpsb95RM7kLqbcnZxMjgdUb9i"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex flex-col justify-end p-8">
                  <span className="font-label text-[10px] text-white/70 tracking-[0.3em] uppercase mb-2">
                    Formal Evening
                  </span>
                  <h5 className="font-display text-2xl text-white">
                    Midnight Velvet Ensemble
                  </h5>
                  <button className="mt-6 w-fit bg-white text-on-background px-6 py-2 rounded-lg font-bold text-sm hover:bg-secondary-fixed transition-colors">
                    Select This Look
                  </button>
                </div>
              </div>
              {/* Card 2 */}
              <div className="flex flex-col space-y-8">
                <div className="relative group h-full rounded-xl overflow-hidden shadow-sm bg-surface">
                  <img
                    className="w-full h-full object-cover"
                    data-alt="A stylish and relaxed evening outfit featuring a charcoal turtleneck under a structured navy overcoat. The image is set against an urban backdrop with city lights blurred into a bokeh effect in the background. The lighting is cool-toned but inviting, highlighting the sophisticated layering and textures suitable for a casual yet elegant dinner."
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuC67hvHPZiKbVHZH4GCjLLiTleIQeKv03Tb6RWMK7mFFSnf58ZWnWM_mAvKDAFiNzkNHaABAHOo82Gp_Vi-SXjYCqdQXwY2_N2YhC5c69fp8lPQ0FD2xhWQmdVUKduAioXxDI0F2LmkJmCBOIJUlAdypsGSf6Ah5Ey-Qa0rqh1sGWJKTZvxaNV-GiFOOstMmClksha3EvH5wH_P3k5SFlb2eG8lTiDAbp9x2dVCmxZc5aKEALjPF-BgQZvgrrjXmc6jer84pw5SuUh6"
                  />
                  <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-colors flex flex-col justify-end p-6">
                    <h5 className="font-display text-xl text-white">
                      Modern Monochromatics
                    </h5>
                    <p className="text-white/80 text-xs mt-1">Smart Casual</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      {/* Floating Action Button: AI Assistant */}
      <div className="fixed bottom-10 right-10 z-50">
        <button className="group relative flex items-center justify-center w-16 h-16 rounded-full bg-on-background shadow-2xl transition-all duration-300 hover:scale-110 active:scale-95">
          <div className="absolute inset-0 rounded-full satin-gradient opacity-0 group-hover:opacity-100 transition-opacity" />
          <span className="material-symbols-outlined text-white relative z-10 transition-transform group-hover:rotate-12">
            auto_awesome
          </span>
          {/* Tooltip */}
          <div className="absolute right-20 bg-on-background text-white px-4 py-2 rounded-lg text-sm font-label whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity translate-x-2 group-hover:translate-x-0">
            Ask AURA AI Stylist
          </div>
        </button>
      </div>
      {/* Micro-interaction Scripts */}
    </>
  );
}