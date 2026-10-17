"use client";

import { useRef } from "react";
import type { ArticleRecord } from "../lib/types";
import FeedbackBar from "./FeedbackBar";
import { useImpression } from "../lib/tracker";

interface Props {
  article: ArticleRecord;
  onOpen: () => void;
  compact?: boolean;
}

export default function StoryCard({ article, onOpen, compact }: Props) {
 const ref = useRef<HTMLElement>(null);
 useImpression(ref as React.RefObject<HTMLElement>, article.id);
 const body = compact
  ? article.body.short
  : article.body.medium || article.body.short;

 return (
  <article
    ref={ref}
    id={`story-${article.id}`}
    style={{ borderTop: "1px solid var(--ink)", paddingTop: 8 }}
  >
    <h3
      style={{
        fontFamily: "var(--font-playfair)",
        fontSize: compact ? 15 : 20,
        margin: "4px 0 6px",
        lineHeight: 1.2,
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
       </h3>
       <p style={{ fontSize: compact ? 12 : 13, color: "var(--ink-soft)", margin: 0 }}>
        {body}
       </p>
       <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 6,
          fontSize: 10,
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
