import type { Metadata } from "next";
import Link from "next/link";
import {
  Libre_Caslon_Text,
  Playfair_Display,
  UnifrakturCook,
} from "next/font/google";
import "./globals.css";

const caslon = Libre_Caslon_Text({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-caslon",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "700", "900"],
  variable: "--font-playfair",
});

const fraktur = UnifrakturCook({
  subsets: ["latin"],
  weight: "700",
  variable: "--font-fraktur",
});

export const metadata: Metadata = {
  title: "Edition of One",
  description: "A personalised daily broadsheet.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
     lang="en"
     className={`${caslon.variable} ${playfair.variable} ${fraktur.variable}`}
    >
     <body>
        <nav className="topnav">
          <Link href="/" className="brand">
           Edition of One
          </Link>
          <Link href="/today">Today</Link>
          <Link href="/archive">Archive</Link>
          <Link href="/profile">Profile</Link>
        </nav>
        <main>{children}</main>
       </body>
      </html>
    );
}
