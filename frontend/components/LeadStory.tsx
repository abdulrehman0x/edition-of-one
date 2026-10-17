"use client";

import { useRef } from "react";
import type { ArticleRecord } from "../lib/types";
import FeedbackBar from "./FeedbackBar";
import { useImpression } from "../lib/tracker";
interface Props {
  article: ArticleRecord;
  onOpen: () => void;
}

export default function LeadStory({ article, onOpen }: Props) {
 const ref = useRef<HTMLElement>(null);
 useImpression(ref as React.RefObject<HTMLElement>, article.id);
 const body = article.body.long || article.body.medium || article.body.short;

 return (
  <article ref={ref} id={`story-${article.id}`}>
    <h1
     style={{
       fontFamily: "var(--font-playfair)",
       fontSize: 42,
       lineHeight: 1.02,
       margin: "0 0 14px",
       letterSpacing: "-0.01em",
     }}
    >
     <button
       type="button"
       onClick={onOpen}
       style={{
         background: "none",
         border: "none",
         padding: 0,
         textAlign: "left",
         color: "inherit",
         font: "inherit",
         cursor: "pointer",
       }}
     >
       {article.title}
     </button>
    </h1>
    <p
     className="drop-cap"
     style={{
       fontFamily: "var(--font-caslon)",
       fontSize: 15,
       columnCount: 3,
       columnGap: 20,
          columnRule: "1px solid var(--rule)",
          marginTop: 0,
        }}
       >
        {body}
       </p>
       <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 8,
          fontSize: 11,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--ink-faint)",
        }}
       >
        <span>{article.source}</span>
        <FeedbackBar articleId={article.id} />
       </div>
      </article>
    );
}
