import "./globals.css";
import NavBar from "./components/NavBar";

export const metadata = { title: "AI Perp DEX | Agent Trading Terminal" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="text-white antialiased font-sans">
        <NavBar />
        <main className="pt-20 pb-12 px-6 max-w-[1600px] mx-auto">{children}</main>
      </body>
    </html>
  );
}
