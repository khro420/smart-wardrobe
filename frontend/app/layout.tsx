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
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
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
