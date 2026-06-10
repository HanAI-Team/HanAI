/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.tsx", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: "#EF6600",
        background: "#EDE8E2",
        border: "#D4CCC4",
        borderStrong: "#C8BFB6",
        text: "#232323",
        subtext: "#8A8480",
        muted: "#B0AAA4",
        avatar: "#68413E",
        surface: "#FFFFFF",
        panel: "#F5F2EE",
        tag: "#585753",
      },
    },
  },
  plugins: [],
};
