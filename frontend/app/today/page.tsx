"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const SAMPLE_EDITION = {
  date: "2026-10-17",
  lead_story: {
    title: "Pakistan government advances major tax and subsidy reform initiative",
    summary: "The ministry of finance has announced updated fiscal guidelines aimed at stabilizing national inflation reserves and boosting IT sector exports.",
    source_name: "Dawn News",
    source_url: "https://www.dawn.com"
  },
  secondary_stories: [
    {
      title: "Global AI chipmakers announce next-generation open architecture",
      summary: "Major semiconductor vendors have unveiled open-source hardware specifications designed to accelerate localized LLM inference engines.",
      source_name: "TechCrunch",
      source_url: "https://techcrunch.com"
    },
    {
      title: "Pakistan vs England test series ends in high-stakes draw at Lahore",
      summary: "A resolute final wicket partnership secured a thrilling draw on the fifth day, leaving the three-match test series tied.",
      source_name: "ESPNcricinfo",
      source_url: "https://www.espncricinfo.com"
    },
    {
      title: "Clean energy investments hit record high across Asian markets",
      summary: "Renewable infrastructure funding has outpaced traditional grid expansions across major regional economies this quarter.",
      source_name: "BBC World News",
      source_url: "https://www.bbc.com/news"
    }
  ],
  weather: { city: "Islamabad", temp_c: 25.6, condition: "Clear" }
};

export default function TodayPage() {
  const [edition, setEdition] = useState<any>(SAMPLE_EDITION);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [feedbackState, setFeedbackState] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    fetch("http://localhost:8000/api/edition/today", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ categories: ["technology", "world", "business"] }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.lead_story) {
          setEdition(data);
        }
      })
      .catch((err) => {
        console.warn("Using instant sample edition fallback:", err);
      });
  }, []);

  const handleToggleAudio = () => {
    if (!("speechSynthesis" in window)) {
      alert("Text-to-speech not supported in this browser.");
      return;
    }
    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
    } else {
      const leadText = (edition?.lead_story?.title || "") + ". " + (edition?.lead_story?.summary || "");
      const utterance = new SpeechSynthesisUtterance(leadText);
      utterance.rate = 1.0;
      utterance.onend = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utterance);
      setIsPlayingAudio(true);
    }
  };

  const handleFeedback = (storyTitle: string, signal: string) => {
    setFeedbackState({ ...feedbackState, [storyTitle]: signal });
    const signals = JSON.parse(localStorage.getItem("edition_one_signals") || "[]");
    signals.push({ title: storyTitle, signal, timestamp: new Date().toISOString() });
    localStorage.setItem("edition_one_signals", JSON.stringify(signals));
  };

  const handleDownloadPDF = () => {
    window.print();
  };

  const lead = edition?.lead_story || SAMPLE_EDITION.lead_story;
  const secondaries = edition?.secondary_stories || SAMPLE_EDITION.secondary_stories;

  return (
    <div style={{ backgroundColor: "#f5efe0", color: "#111111", fontFamily: "serif", minHeight: "100vh", padding: "24px" }}>
      <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
        
        {/* Navigation / Action Bar */}
        <div className="no-print" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #111", paddingBottom: "8px", marginBottom: "16px", fontFamily: "sans-serif", fontSize: "12px", fontWeight: "bold" }}>
          <div>
            <Link href="/" style={{ marginRight: "16px", color: "#111", textDecoration: "none" }}>SETUP</Link>
            <Link href="/today" style={{ marginRight: "16px", color: "#800000", textDecoration: "underline" }}>TODAY</Link>
            <Link href="/archive" style={{ marginRight: "16px", color: "#111", textDecoration: "none" }}>ARCHIVE</Link>
            <Link href="/profile" style={{ color: "#111", textDecoration: "none" }}>PROFILE</Link>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={handleToggleAudio}
              style={{
                backgroundColor: isPlayingAudio ? "#800000" : "#111",
                color: "#f5efe0",
                border: "none",
                padding: "6px 12px",
                fontFamily: "sans-serif",
                fontSize: "11px",
                fontWeight: "bold",
                textTransform: "uppercase",
                cursor: "pointer",
                boxShadow: "2px 2px 0px #800000"
              }}
            >
              {isPlayingAudio ? "⏹ Stop Audio Briefing" : "🎙️ AI Morning Voice Briefing"}
            </button>

            <button
              onClick={handleDownloadPDF}
              style={{
                backgroundColor: "#fff",
                color: "#111",
                border: "1px solid #111",
                padding: "6px 12px",
                fontFamily: "sans-serif",
                fontSize: "11px",
                fontWeight: "bold",
                textTransform: "uppercase",
                cursor: "pointer"
              }}
            >
              📥 Download PDF Edition
            </button>
          </div>
        </div>

        {/* Print Styles for Clean PDF Export */}
        <style jsx global>{`
          @media print {
            .no-print {
              display: none !important;
            }
            body {
              background-color: #ffffff !important;
            }
          }
        `}</style>

        {/* Newspaper Nameplate */}
        <div style={{ textAlign: "center", borderBottom: "3px double #111", paddingBottom: "12px", marginBottom: "24px" }}>
          <h1 style={{ fontSize: "56px", fontWeight: "900", textTransform: "uppercase", margin: 0, letterSpacing: "-1px" }}>
            Edition of One
          </h1>
          <p style={{ fontFamily: "sans-serif", fontSize: "11px", textTransform: "uppercase", letterSpacing: "2px", color: "#555", margin: "4px 0 0 0" }}>
            ISLAMABAD — {edition?.date || "2026-10-17"} — AI CURATED & VERIFIED
          </p>
        </div>

        {/* Main Content Layout */}
        <div style={{ display: "grid", gridTemplateColumns: "3fr 1fr", gap: "24px", borderBottom: "1px solid #111", paddingBottom: "24px", marginBottom: "24px" }}>
          
          {/* Main Lead Column */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "sans-serif", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase", color: "#800000", letterSpacing: "1px" }}>
                LEAD STORY — {lead.source_name || "LIVE WIRE"}
              </span>
              
              <div className="no-print" style={{ fontFamily: "sans-serif", fontSize: "10px" }}>
                {feedbackState[lead.title] ? (
                  <span style={{ color: "#006600", fontWeight: "bold" }}>✓ Saved ({feedbackState[lead.title]})</span>
                ) : (
                  <span>
                    Rate: 
                    <button onClick={() => handleFeedback(lead.title, "more")} style={{ background: "none", border: "none", cursor: "pointer", marginLeft: "4px", fontWeight: "bold" }}>👍 More like this</button>
                    <button onClick={() => handleFeedback(lead.title, "less")} style={{ background: "none", border: "none", cursor: "pointer", marginLeft: "6px", fontWeight: "bold" }}>👎 Less</button>
                  </span>
                )}
              </div>
            </div>

            <h2 style={{ fontSize: "34px", fontWeight: "bold", margin: "6px 0 12px 0", lineHeight: "1.15" }}>
              {lead.title}
            </h2>
            <p style={{ fontSize: "15px", lineHeight: "1.6", margin: "0 0 12px 0" }}>
              {lead.summary}
            </p>
            {lead.source_url && (
              <a
                href={lead.source_url}
                target="_blank"
                rel="noreferrer"
                style={{ fontFamily: "sans-serif", fontSize: "11px", color: "#800000", fontWeight: "bold", textDecoration: "underline" }}
              >
                Read original source at {lead.source_name} →
              </a>
            )}
          </div>

          {/* Right Rail / Weather & Widgets */}
          <div style={{ borderLeft: "1px solid #111", paddingLeft: "16px" }}>
            <div style={{ border: "1px solid #111", padding: "12px", backgroundColor: "#fcf8ed", marginBottom: "16px", textAlign: "center", boxShadow: "2px 2px 0px #111" }}>
              <p style={{ fontFamily: "sans-serif", fontSize: "10px", textTransform: "uppercase", margin: 0, color: "#666" }}>ISLAMABAD</p>
              <p style={{ fontSize: "28px", fontWeight: "bold", margin: "4px 0" }}>25.6°C</p>
              <p style={{ fontFamily: "sans-serif", fontSize: "10px", margin: 0, color: "#555" }}>Condition: Clear</p>
            </div>

            <div style={{ border: "1px solid #111", padding: "12px", backgroundColor: "#fcf8ed", boxShadow: "2px 2px 0px #111" }}>
              <p style={{ fontFamily: "sans-serif", fontSize: "10px", textTransform: "uppercase", fontWeight: "bold", margin: "0 0 4px 0", color: "#800000" }}>Market Index</p>
              <p style={{ fontFamily: "sans-serif", fontSize: "12px", margin: 0, fontWeight: "bold" }}>KSE-100: 85,420 (+1.2%)</p>
            </div>
          </div>

        </div>

        {/* Secondary Stories Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", borderBottom: "1px solid #111", paddingBottom: "24px", marginBottom: "24px" }}>
          {secondaries.map((story: any, idx: number) => (
            <div key={idx} style={{ borderRight: idx < secondaries.length - 1 ? "1px solid #ccc" : "none", paddingRight: idx < secondaries.length - 1 ? "16px" : 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "sans-serif", fontSize: "9px", fontWeight: "bold", textTransform: "uppercase", color: "#800000" }}>
                  {story.source_name || "NEWS WIRE"}
                </span>
                <button
                  className="no-print"
                  onClick={() => handleFeedback(story.title, feedbackState[story.title] ? "reset" : "liked")}
                  style={{ background: "none", border: "none", fontSize: "10px", cursor: "pointer", color: feedbackState[story.title] ? "#800000" : "#666" }}
                >
                  {feedbackState[story.title] ? "★ Saved" : "☆ Save"}
                </button>
              </div>

              <h3 style={{ fontSize: "18px", fontWeight: "bold", margin: "4px 0 8px 0" }}>{story.title}</h3>
              <p style={{ fontSize: "13px", lineHeight: "1.4", margin: "0 0 8px 0", color: "#333" }}>{story.summary}</p>
              {story.source_url && (
                <a href={story.source_url} target="_blank" rel="noreferrer" style={{ fontFamily: "sans-serif", fontSize: "10px", color: "#800000", fontWeight: "bold" }}>
                  Source Link →
                </a>
              )}
            </div>
          ))}
        </div>

        {/* Back Page Feature */}
        <div style={{ backgroundColor: "#fcf8ed", border: "1px solid #111", padding: "16px", marginBottom: "24px", boxShadow: "3px 3px 0px #111" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #111", paddingBottom: "8px", marginBottom: "8px" }}>
            <h4 style={{ fontFamily: "sans-serif", fontSize: "12px", textTransform: "uppercase", fontWeight: "bold", margin: 0, letterSpacing: "1px" }}>
              Back Page: Daily News IQ Quiz
            </h4>
            <span style={{ fontFamily: "sans-serif", fontSize: "10px", color: "#800000", fontWeight: "bold" }}>EXCLUSIVES</span>
          </div>
          <p style={{ fontSize: "13px", margin: "0 0 8px 0" }}>
            <strong>Question of the Day:</strong> Which regional market index surged past 85,420 following recent fiscal policy announcements?
          </p>
          <div className="no-print" style={{ display: "flex", gap: "10px", fontFamily: "sans-serif", fontSize: "11px" }}>
            <button onClick={() => alert("Correct! KSE-100 hit new milestones.")} style={{ padding: "4px 8px", backgroundColor: "#111", color: "#f5efe0", border: "none", cursor: "pointer" }}>A) KSE-100</button>
            <button onClick={() => alert("Incorrect. Try again.")} style={{ padding: "4px 8px", backgroundColor: "#fff", border: "1px solid #111", cursor: "pointer" }}>B) NASDAQ</button>
            <button onClick={() => alert("Incorrect. Try again.")} style={{ padding: "4px 8px", backgroundColor: "#fff", border: "1px solid #111", cursor: "pointer" }}>C) FTSE 100</button>
          </div>
        </div>

      </div>
    </div>
  );
}