"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const PRESET_TEMPLATES = [
  {
    id: "tech-founder",
    title: "Tech Founder",
    description: "AI, Software, Venture Capital, and Global Tech Trends",
    categories: ["technology", "business", "science"],
    customPrompt: "Focus on AI research, open-source models, and developer tools.",
  },
  {
    id: "macro-analyst",
    title: "Macro Analyst",
    description: "Economy, International Relations, and Policy Updates",
    categories: ["world", "business", "politics"],
    customPrompt: "Highlight trade agreements, inflation, and market movements.",
  },
  {
    id: "sports-fanatic",
    title: "Sports & Culture",
    description: "Cricket Tests, Football, Culture, and Entertainment",
    categories: ["sports", "culture", "world"],
    customPrompt: "Prioritize Pakistan cricket match summaries and world sports news.",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    "technology",
    "world",
  ]);
  const [customPrompt, setCustomPrompt] = useState("");
  const [readingTime, setReadingTime] = useState(5);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);

  useEffect(() => {
    const savedUser = localStorage.getItem("edition_one_user");
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        console.error("Invalid user session");
      }
    }
  }, []);

  const handleApplyTemplate = (tpl: typeof PRESET_TEMPLATES[0]) => {
    setSelectedCategories(tpl.categories);
    setCustomPrompt(tpl.customPrompt);
  };

  const handleToggleCategory = (cat: string) => {
    if (selectedCategories.includes(cat)) {
      setSelectedCategories(selectedCategories.filter((c) => c !== cat));
    } else {
      setSelectedCategories([...selectedCategories, cat]);
    }
  };

  const handleGenerate = () => {
    const profile = {
      categories: selectedCategories,
      customPrompt,
      readingTimeMinutes: readingTime,
      user: user || { name: "Guest" },
    };
    localStorage.setItem("edition_one_profile", JSON.stringify(profile));
    router.push("/today");
  };

  return (
    <div style={{ backgroundColor: "#f5efe0", color: "#111111", fontFamily: "serif", minHeight: "100vh", padding: "24px" }}>
      <div style={{ maxWidth: "800px", margin: "0 auto" }}>
        
        {/* Header Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "2px solid #111", paddingBottom: "16px", marginBottom: "32px" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: "900", textTransform: "uppercase", margin: 0, letterSpacing: "-1px" }}>
              Edition of One
            </h1>
            <p style={{ fontSize: "12px", fontFamily: "sans-serif", textTransform: "uppercase", letterSpacing: "1.5px", color: "#555", margin: 0 }}>
              Personal Broadsheet Setup
            </p>
          </div>
          <div>
            {user ? (
              <div style={{ textAlign: "right", fontFamily: "sans-serif", fontSize: "12px" }}>
                <strong>Welcome, {user.name}</strong><br />
                <button
                  onClick={() => { localStorage.removeItem("edition_one_user"); setUser(null); }}
                  style={{ background: "none", border: "none", textDecoration: "underline", color: "#900", cursor: "pointer", padding: 0 }}
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link href="/auth" style={{ backgroundColor: "#111", color: "#f5efe0", fontFamily: "sans-serif", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase", padding: "8px 16px", textDecoration: "none", display: "inline-block" }}>
                Sign In / Register
              </Link>
            )}
          </div>
        </div>

        {/* Option 1: Persona Templates */}
        <div style={{ marginBottom: "36px" }}>
          <h2 style={{ fontSize: "14px", fontFamily: "sans-serif", textTransform: "uppercase", fontWeight: "bold", letterSpacing: "1px", marginBottom: "16px", color: "#333" }}>
            Option 1: Select a Starter Persona
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: "16px" }}>
            {PRESET_TEMPLATES.map((tpl) => (
              <div
                key={tpl.id}
                onClick={() => handleApplyTemplate(tpl)}
                style={{
                  border: "1px solid #111",
                  backgroundColor: "#fcf8ed",
                  padding: "16px",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: "2px 2px 0px #111"
                }}
              >
                <div>
                  <h3 style={{ margin: "0 0 8px 0", fontSize: "18px", fontWeight: "bold" }}>{tpl.title}</h3>
                  <p style={{ fontFamily: "sans-serif", fontSize: "12px", color: "#555", margin: "0 0 16px 0", lineHeight: "1.4" }}>
                    {tpl.description}
                  </p>
                </div>
                <span style={{ fontFamily: "sans-serif", fontSize: "11px", textTransform: "uppercase", fontWeight: "bold", color: "#800000", borderTop: "1px solid #ddd", paddingTop: "8px" }}>
                  Apply Template →
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Option 2: Custom Preferences */}
        <div style={{ backgroundColor: "#fcf8ed", border: "1px solid #111", padding: "24px", marginBottom: "32px", boxShadow: "2px 2px 0px #111" }}>
          <h2 style={{ fontSize: "14px", fontFamily: "sans-serif", textTransform: "uppercase", fontWeight: "bold", letterSpacing: "1px", marginBottom: "20px", color: "#333", marginTop: 0 }}>
            Option 2: Customize Topics & Instructions
          </h2>

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", fontSize: "12px", fontFamily: "sans-serif", fontWeight: "bold", textTransform: "uppercase", marginBottom: "8px" }}>
              Selected Topics:
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {["technology", "world", "business", "sports", "science", "culture"].map((cat) => {
                const active = selectedCategories.includes(cat);
                return (
                  <button
                    key={cat}
                    onClick={() => handleToggleCategory(cat)}
                    style={{
                      padding: "6px 12px",
                      fontSize: "12px",
                      fontFamily: "sans-serif",
                      fontWeight: "bold",
                      textTransform: "uppercase",
                      border: "1px solid #111",
                      cursor: "pointer",
                      backgroundColor: active ? "#111" : "#fff",
                      color: active ? "#f5efe0" : "#111"
                    }}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", fontSize: "12px", fontFamily: "sans-serif", fontWeight: "bold", textTransform: "uppercase", marginBottom: "8px" }}>
              Custom Curation Prompt:
            </label>
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="e.g. Focus on AI developments, Pakistan economic news, and global cricket tests..."
              style={{
                width: "100%",
                backgroundColor: "#fff",
                border: "1px solid #111",
                padding: "10px",
                fontFamily: "sans-serif",
                fontSize: "12px",
                boxSizing: "border-box"
              }}
              rows={3}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontFamily: "sans-serif", fontWeight: "bold", textTransform: "uppercase", marginBottom: "8px" }}>
              Target Reading Time: {readingTime} Minutes
            </label>
            <input
              type="range"
              min={3}
              max={15}
              value={readingTime}
              onChange={(e) => setReadingTime(Number(e.target.value))}
              style={{ width: "100%", accentColor: "#111" }}
            />
          </div>
        </div>

        {/* Action Button */}
        <div style={{ textAlign: "center" }}>
          <button
            onClick={handleGenerate}
            style={{
              backgroundColor: "#111",
              color: "#f5efe0",
              fontFamily: "sans-serif",
              fontSize: "14px",
              fontWeight: "bold",
              textTransform: "uppercase",
              letterSpacing: "2px",
              padding: "16px 32px",
              border: "none",
              cursor: "pointer",
              boxShadow: "3px 3px 0px #800000"
            }}
          >
            Print My Custom Edition →
          </button>
        </div>

      </div>
    </div>
  );
}
