/* eslint-disable react/no-unescaped-entities */
"use client";

import { useState } from "react";
import type { Edition, ArticleRecord } from "../lib/types";
import Masthead from "./Masthead";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
import BriefsList from "./BriefsList";
import SectionHeader from "./SectionHeader";
import ReadingPanel from "./ReadingPanel";
import AudioPlayer from "./extras/AudioPlayer";
import PressGallery from "./extras/PressGallery";
import BackPage from "./extras/BackPage";
import WhyChip from "./WhyChip";

export default function EditionView({ edition }: { edition: Edition }) {
 const [open, setOpen] = useState<ArticleRecord | null>(null);

 return (
  <div className="page">
    <Masthead edition={edition} />
    {edition.why_text && (
      <div style={{ margin: "8px 0 20px", textAlign: "center" }}>
       <WhyChip text={edition.why_text} />
      </div>
    )}

   <section
    style={{
      display: "grid",
      gridTemplateColumns: "3fr 1fr",
      gap: 24,
      borderBottom: "1px solid var(--ink)",
      paddingBottom: 24,
    }}
   >
    <div>
      {edition.front.lead && (
        <LeadStory
         article={edition.front.lead}
         onOpen={() => setOpen(edition.front.lead || null)}
        />
      )}
    </div>
    <aside style={{ borderLeft: "1px solid var(--rule)", paddingLeft: 18 }}>
      {edition.front.weather && (
        <div style={{ border: "1px solid var(--ink)", padding: 12, textAlign: "center",
marginBottom: 12 }}>
         <div style={{ fontSize: 11, letterSpacing: "0.2em", textTransform: "uppercase" }}>
           {edition.front.weather.city}
         </div>
         <div style={{ fontFamily: "var(--font-playfair)", fontSize: 36, lineHeight: 1 }}>
           {edition.front.weather.temp_c ?? "--"}°
         </div>
     <div style={{ fontSize: 11, color: "var(--ink-faint)" }}>
       H {edition.front.weather.high_c ?? "--"}° / L {edition.front.weather.low_c ?? "--"}°
     </div>
    </div>
  )}
  {edition.front.quote && (
    <blockquote
     style={{
       fontStyle: "italic",
       borderTop: "1px solid var(--ink)",
       borderBottom: "1px solid var(--ink)",
       padding: "12px 0",
       margin: 0,
     }}
    >
     {edition.front.quote}
    </blockquote>
  )}
  {edition.weight_snapshot && (
    <div style={{ marginTop: 16, fontSize: 11, color: "var(--ink-faint)" }}>
     Tonight&apos;s weights:{" "}
     {Object.entries(edition.weight_snapshot)
       .slice(0, 4)
       .map(([k, v]) => `${k} ${v.toFixed(2)}`)
       .join(" · ")}
    </div>
  )}
 </aside>
</section>

{edition.front.secondary.length > 0 && (
  <section
   style={{
     display: "grid",
     gridTemplateColumns: "repeat(3, 1fr)",
     gap: 20,
     marginTop: 24,
   }}
  >
   {edition.front.secondary.map((a) => (
     <StoryCard key={a.id} article={a} onOpen={() => setOpen(a)} />
   ))}
  </section>
)}
{edition.front.briefs.length > 0 && (
  <section style={{ marginTop: 24 }}>
   <BriefsList briefs={edition.front.briefs} onOpen={setOpen} />
  </section>
)}

{edition.sections.map((sec) => (
  <section key={sec.slug} style={{ marginTop: 32 }}>
    <SectionHeader name={sec.name} />
    <div
     style={{
       display: "grid",
       gridTemplateColumns: "repeat(3, 1fr)",
       gap: 20,
     }}
    >
     {sec.articles.map((a) => (
       <StoryCard key={a.id} article={a} onOpen={() => setOpen(a)} />
     ))}
    </div>
  </section>
))}

{edition.outside_bubble.length > 0 && (
  <section style={{ marginTop: 32 }}>
   <SectionHeader name="Outside Your Bubble" />
   <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
    {edition.outside_bubble.map((a) => (
      <StoryCard key={a.id} article={a} onOpen={() => setOpen(a)} compact />
    ))}
   </div>
  </section>
)}

<section style={{ marginTop: 32 }}>
 <AudioPlayer edition={edition} />
</section>

{edition.press_gallery && edition.press_gallery.rows.length > 0 && (
  <section style={{ marginTop: 24 }}>
   <PressGallery gallery={edition.press_gallery} />
  </section>
)}
       {edition.back_page && (
         <section style={{ marginTop: 24 }}>
          <BackPage backPage={edition.back_page} />
         </section>
       )}

       <ReadingPanel article={open} onClose={() => setOpen(null)} />
      </div>
    );
}
