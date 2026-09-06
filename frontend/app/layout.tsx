import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AURA — Smart Wardrobe",
  description: "Your AI-powered personal stylist and wardrobe curator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          background: "var(--aura-cream)",
          minHeight: "100vh",
          margin: "0px",
        }}
      >
        {children}
      </body>
    </html>
  );
}
