import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Riverbit Design System — Brand
        rb: {
          cyan: "#0EECBC",
          "cyan-light": "#22C3A0",
          red: "#DD3C41",
          green: "#61DD3C",
          yellow: "#E8BD30",
        },
        // Riverbit Design System — Surface layers
        layer: {
          0: "#070E12",   // D950
          1: "#0D1417",   // D930
          2: "#151B1E",   // D900
          3: "#1F292E",   // D800
          4: "#354046",   // D700
          5: "#5C6970",   // D600
          6: "#89949A",   // D400
          7: "#ABB5BA",   // D300
          8: "#C5CFD3",   // D200
          9: "#E2E7E9",   // D100
          10: "#F7F8F8",  // D30
        },
        // Riverbit Design System — Text
        "rb-text": {
          main: "#EBEEF0",
          secondary: "#75838A",
          muted: "#5C6970",
          placeholder: "#354046",
        },
      },
      fontFamily: {
        main: [
          "Trebuchet MS",
          "Lucida Grande",
          "Lucida Sans Unicode",
          "Lucida Sans",
          "sans-serif",
        ],
      },
      fontSize: {
        h1: ["32px", { lineHeight: "48px", fontWeight: "700" }],
        h2: ["28px", { lineHeight: "40px", fontWeight: "700" }],
        h3: ["24px", { lineHeight: "32px", fontWeight: "700" }],
        h4: ["20px", { lineHeight: "28px", fontWeight: "700" }],
        h5: ["18px", { lineHeight: "26px", fontWeight: "700" }],
        h6: ["16px", { lineHeight: "24px", fontWeight: "700" }],
        h7: ["14px", { lineHeight: "20px", fontWeight: "700" }],
        h8: ["12px", { lineHeight: "16px", fontWeight: "700" }],
        subtitle: ["18px", { lineHeight: "26px", fontWeight: "400" }],
        body: ["16px", { lineHeight: "24px", fontWeight: "400" }],
        desc: ["14px", { lineHeight: "20px", fontWeight: "400" }],
        small: ["12px", { lineHeight: "18px", fontWeight: "400" }],
      },
      borderRadius: {
        card: "8px",
      },
    },
  },
  plugins: [],
};
export default config;
