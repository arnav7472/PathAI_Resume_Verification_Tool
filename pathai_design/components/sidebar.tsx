"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Upload,
  LayoutDashboard,
  ListChecks,
  ShieldCheck,
  FileBarChart2,
  Settings,
  Zap,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Upload", href: "/", icon: Upload },
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Claims", href: "/claims", icon: ListChecks },
  { label: "Evidence", href: "/evidence", icon: ShieldCheck },
  { label: "Reports", href: "/reports", icon: FileBarChart2 },
  { label: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 h-full w-56 flex flex-col z-50 bg-sidebar border-r border-sidebar-border">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-sidebar-border shrink-0">
        <div className="relative flex items-center justify-center w-7 h-7">
          <div className="absolute inset-0 rounded-md bg-electric-blue opacity-20 blur-sm" />
          <Zap className="relative w-4 h-4 text-electric-blue" strokeWidth={2.5} />
        </div>
        <span className="text-sm font-semibold tracking-tight text-foreground">
          PathAI <span className="text-electric-blue">Verify</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="px-2 mb-2 text-[10px] font-semibold tracking-widest uppercase text-muted-foreground">
          Workspace
        </p>
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group flex items-center gap-3 px-2.5 py-2 rounded-md text-sm font-medium transition-all duration-150",
                active
                  ? "bg-secondary text-foreground border border-border"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  active ? "text-electric-blue" : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              <span className="flex-1">{label}</span>
              {active && (
                <ChevronRight className="w-3 h-3 text-muted-foreground" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-sidebar-border shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="relative w-7 h-7 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0">
            <span className="text-[10px] font-bold text-foreground">HR</span>
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-cyan-accent border border-sidebar" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-foreground truncate">HR Admin</p>
            <p className="text-[10px] text-muted-foreground truncate">Enterprise Plan</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
