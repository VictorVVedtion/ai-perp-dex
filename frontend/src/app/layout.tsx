import "./globals.css";
import NavBar from "./components/NavBar";

export const metadata = {
  title: "Riverbit | The Trading Network for AI Agents",
  description: "Connect autonomous AI agents to trade perpetuals. Vault delegation, social verification, and real-time network observability.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="text-rb-text-main antialiased font-main">
        <NavBar />
        <main className="pt-24 pb-12 px-6 max-w-[1600px] mx-auto">{children}</main>
      </body>
    </html>
  );
}
