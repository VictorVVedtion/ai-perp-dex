import "./globals.css";
import NavBar from "./components/NavBar";

export const metadata = { title: "Riverbit | Agent Trading Terminal" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="text-rb-text-main antialiased font-main">
        <NavBar />
        <main className="pt-20 pb-12 px-6 max-w-[1600px] mx-auto">{children}</main>
      </body>
    </html>
  );
}
