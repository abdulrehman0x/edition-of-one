"use client";

import { useEffect, useState } from "react";

interface Props {
  message: string;
  onDone?: () => void;
  durationMs?: number;
}

export default function Toast({ message, onDone, durationMs = 2400 }: Props) {
 const [visible, setVisible] = useState(true);
 useEffect(() => {
   const t = setTimeout(() => {
     setVisible(false);
     onDone?.();
   }, durationMs);
   return () => clearTimeout(t);
 }, [onDone, durationMs]);

 if (!visible) return null;

 return (
  <div
    style={{
     position: "fixed",
     bottom: 24,
     left: "50%",
     transform: "translateX(-50%)",
     background: "var(--ink)",
     color: "var(--paper)",
     padding: "10px 20px",
         fontSize: 12,
         letterSpacing: "0.1em",
         zIndex: 200,
       }}
      >
       {message}
      </div>
    );
}
