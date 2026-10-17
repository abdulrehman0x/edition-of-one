"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function AuthPage() {
  const router = useRouter();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    // Save session locally for demo/hackathon flow
    const userSession = {
      email,
      name: fullName || email.split("@")[0],
      signedInAt: new Date().toISOString(),
    };
    localStorage.setItem("edition_one_user", JSON.stringify(userSession));

    // Redirect to main onboarding flow
    router.push("/");
  };

  return (
    <div style={{ backgroundColor: "#f5efe0", color: "#111111", fontFamily: "serif", minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "24px" }}>
      <div style={{ maxWidth: "420px", width: "100%", backgroundColor: "#fcf8ed", border: "1px solid #111", padding: "32px", boxShadow: "3px 3px 0px #111" }}>
        
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <h1 style={{ fontSize: "28px", fontWeight: "900", textTransform: "uppercase", margin: "0 0 8px 0", letterSpacing: "-0.5px" }}>
            Edition of One
          </h1>
          <p style={{ fontSize: "11px", fontFamily: "sans-serif", textTransform: "uppercase", letterSpacing: "1.5px", color: "#555", margin: 0, borderTop: "1px solid #ccc", borderBottom: "1px solid #ccc", padding: "6px 0" }}>
            {isSignUp ? "Create Reader Account" : "Sign In to Your Broadsheet"}
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {isSignUp && (
            <div>
              <label style={{ display: "block", fontSize: "11px", fontFamily: "sans-serif", fontWeight: "bold", textTransform: "uppercase", marginBottom: "6px" }}>
                Full Name
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Abeer Khalil"
                style={{ width: "100%", backgroundColor: "#fff", border: "1px solid #111", padding: "10px", fontFamily: "sans-serif", fontSize: "13px", boxSizing: "border-box" }}
              />
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "11px", fontFamily: "sans-serif", fontWeight: "bold", textTransform: "uppercase", marginBottom: "6px" }}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="reader@domain.com"
              style={{ width: "100%", backgroundColor: "#fff", border: "1px solid #111", padding: "10px", fontFamily: "sans-serif", fontSize: "13px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontFamily: "sans-serif", fontWeight: "bold", textTransform: "uppercase", marginBottom: "6px" }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{ width: "100%", backgroundColor: "#fff", border: "1px solid #111", padding: "10px", fontFamily: "sans-serif", fontSize: "13px", boxSizing: "border-box" }}
            />
          </div>

          <button
            type="submit"
            style={{
              width: "100%",
              backgroundColor: "#111",
              color: "#f5efe0",
              fontFamily: "sans-serif",
              fontSize: "12px",
              fontWeight: "bold",
              textTransform: "uppercase",
              letterSpacing: "1.5px",
              padding: "14px",
              border: "none",
              cursor: "pointer",
              marginTop: "8px",
              boxShadow: "2px 2px 0px #800000"
            }}
          >
            {isSignUp ? "Create Account & Start →" : "Sign In & Continue →"}
          </button>
        </form>

        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid #ddd", textAlign: "center", fontFamily: "sans-serif", fontSize: "12px" }}>
          <span>
            {isSignUp ? "Already have an account?" : "New to Edition of One?"}{" "}
            <button
              onClick={() => setIsSignUp(!isSignUp)}
              style={{ background: "none", border: "none", textDecoration: "underline", fontWeight: "bold", color: "#800000", cursor: "pointer", padding: 0, marginLeft: "4px" }}
            >
              {isSignUp ? "Sign In" : "Sign Up Free"}
            </button>
          </span>
        </div>

        <div style={{ marginTop: "16px", textAlign: "center" }}>
          <Link
            href="/"
            style={{ fontFamily: "sans-serif", color: "#111", fontSize: "11px", textDecoration: "underline", textTransform: "uppercase", letterSpacing: "1px" }}
          >
            ← Back to Guest Setup
          </Link>
        </div>

      </div>
    </div>
  );
}
