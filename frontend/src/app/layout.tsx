import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { WalletContextProvider } from "./providers";
import { Header } from "@/components/Header";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Perp DEX",
  description: "AI-Powered Perpetual Futures DEX on Solana",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-900 text-white min-h-screen`}>
        <WalletContextProvider>
          <Header />
          <main>{children}</main>
        </WalletContextProvider>
      </body>
    </html>
  );
}
