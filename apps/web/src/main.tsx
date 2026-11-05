import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { detectLocale } from "@/lib/i18n"

// The document language must match the language actually rendered, otherwise a
// screen reader reads German text with an English voice. `index.html` carries a
// static `lang="de"` for the no-JS case; this corrects it before first paint.
document.documentElement.lang = detectLocale()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>
)
