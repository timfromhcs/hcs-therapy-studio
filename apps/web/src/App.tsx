import { useCallback, useEffect, useState } from "react"

import { AppShell, useHealth } from "@/components/app-shell"
import type { Screen } from "@/components/app-shell"
import type { Locale } from "@/lib/i18n"
import { detectLocale } from "@/lib/i18n"

const SCREENS: Screen[] = [
  "home",
  "chat",
  "journal",
  "reflection",
  "studio",
  "lab",
  "safety",
  "settings",
]

function readHash(): Screen {
  const value = window.location.hash.replace(/^#\/?/, "") as Screen
  return SCREENS.includes(value) ? value : "home"
}

export function App() {
  const [screen, setScreen] = useState<Screen>(readHash)
  const [locale] = useState<Locale>(detectLocale)
  const health = useHealth()

  const navigate = useCallback((next: Screen) => {
    setScreen(next)
    window.location.hash = next
  }, [])

  useEffect(() => {
    const onHashChange = () => setScreen(readHash())
    window.addEventListener("hashchange", onHashChange)
    return () => window.removeEventListener("hashchange", onHashChange)
  }, [])

  return <AppShell screen={screen} onNavigate={navigate} locale={locale} health={health} />
}

export default App
