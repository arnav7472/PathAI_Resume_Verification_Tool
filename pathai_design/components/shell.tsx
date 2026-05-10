import { Sidebar } from "@/components/sidebar"

interface ShellProps {
  children: React.ReactNode
}

export function Shell({ children }: ShellProps) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 ml-56 min-h-screen overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
