
import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard, MessageSquare, Bot, Workflow,
  Brain, Database, Plug, Activity, Settings,
  Search, Bell, Plus, ArrowUpRight, Cpu,
  HardDrive, Zap, Moon, Sun,
  MoreHorizontal, Circle, Command
} from "lucide-react";

const navigation: { title: string; items: { name: string; icon: LucideIcon }[] }[] = [
  { title: "WORKSPACE", items: [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "Conversations", icon: MessageSquare },
    { name: "My Agents", icon: Bot },
    { name: "Workflows", icon: Workflow },
  ]},
  { title: "RESOURCES", items: [
    { name: "Models", icon: Brain },
    { name: "Knowledge Base", icon: Database },
    { name: "Integrations", icon: Plug },
  ]},
  { title: "SYSTEM", items: [
    { name: "Runtime Monitor", icon: Activity },
    { name: "Settings", icon: Settings },
  ]},
];

const stats: { label: string; value: string; detail: string; icon: LucideIcon }[] = [
  { label: "Active Agents", value: "04", detail: "2 currently running", icon: Bot },
  { label: "Local Models", value: "06", detail: "Ollama connected", icon: Brain },
  { label: "Conversations", value: "128", detail: "Across all agents", icon: MessageSquare },
  { label: "Tokens Processed", value: "2.4M", detail: "This month", icon: Zap },
];

const quickActions: { label: string; icon: LucideIcon }[] = [
  { label: "New Conversation", icon: MessageSquare },
  { label: "Build an Agent", icon: Bot },
  { label: "Explore Models", icon: Brain },
  { label: "Create Workflow", icon: Workflow },
];

const recentActivity = [
  { name: "Research Assistant", description: "Completed a research task", time: "2 min ago", status: "Completed" },
  { name: "Code Assistant", description: "Generated Python script", time: "18 min ago", status: "Completed" },
  { name: "Local Llama", description: "Conversation started", time: "42 min ago", status: "Active" },
];

export default function App() {
  const [dark, setDark] = useState(true);
  const [active, setActive] = useState("Dashboard");

  return (
    <div className={dark ? "dark" : ""}>
      <main className="min-h-screen bg-[#f7f7f7] text-[#171717] dark:bg-[#111] dark:text-[#f5f5f5] flex">
        {/* SIDEBAR */}
        <aside className="w-[248px] shrink-0 border-r border-black/10 dark:border-white/10 p-5 flex flex-col">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-9 h-9 rounded-xl bg-black text-white dark:bg-white dark:text-black flex items-center justify-center">
              <Command size={20}/>
            </div>
            <div>
              <h1 className="font-semibold tracking-[0.16em]">NEXUS</h1>
              <p className="text-[10px] tracking-[0.24em] text-neutral-500">AI PLATFORM</p>
            </div>
          </div>

          {navigation.map(group => (
            <section key={group.title} className="mb-8">
              <p className="text-[10px] font-semibold tracking-[0.18em] text-neutral-500 mb-3">
                {group.title}
              </p>
              <div className="space-y-1">
                {group.items.map(({ name, icon: Icon }) => (
                  <button
                    key={name}
                    onClick={() => setActive(name)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      active === name
                        ? "bg-neutral-200 dark:bg-[#292929] font-medium"
                        : "text-neutral-500 hover:bg-neutral-100 dark:hover:bg-white/5"
                    }`}
                  >
                    <Icon size={17}/>
                    {name}
                  </button>
                ))}
              </div>
            </section>
          ))}

          <div className="mt-auto border border-black/10 dark:border-white/10 rounded-xl p-3">
            <div className="flex items-center gap-2 text-xs">
              <Circle size={8} fill="#16a34a" color="#16a34a"/>
              <span className="font-medium">Ollama Connected</span>
            </div>
            <p className="text-[11px] text-neutral-500 mt-2">
              localhost:11434
            </p>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <div className="flex-1 min-w-0">
          <header className="h-[72px] border-b border-black/10 dark:border-white/10 px-8 flex items-center justify-between">
            <div className="text-sm text-neutral-500">
              Workspace <span className="mx-2">/</span>
              <span className="text-neutral-900 dark:text-white">{active}</span>
            </div>
            <div className="flex items-center gap-4">
              <button className="flex items-center gap-2 text-sm text-neutral-500 border border-black/10 dark:border-white/10 rounded-lg px-3 py-2">
                <Search size={15}/> Search
              </button>
              <button className="text-neutral-500">
                <Bell size={19}/>
              </button>
              <button onClick={() => setDark(!dark)} className="p-2 rounded-lg hover:bg-neutral-200 dark:hover:bg-white/10">
                {dark ? <Sun size={18}/> : <Moon size={18}/>}
              </button>
              <div className="w-8 h-8 rounded-full bg-neutral-300 dark:bg-neutral-700 flex items-center justify-center text-xs font-semibold">
                N
              </div>
            </div>
          </header>

          <div className="max-w-[1500px] mx-auto p-8">
            <div className="flex justify-between items-start mb-9">
              <div>
                <p className="text-xs text-neutral-500 mb-2">SUNDAY, NOVEMBER 8, 2026</p>
                <h2 className="text-3xl font-semibold tracking-tight">Welcome to Nexus.</h2>
                <p className="text-sm text-neutral-500 mt-2">
                  Your local intelligence workspace is ready.
                </p>
              </div>
              <button className="bg-black text-white dark:bg-white dark:text-black rounded-lg px-4 py-2.5 text-sm font-medium flex items-center gap-2">
                <Plus size={16}/> Create Agent
              </button>
            </div>

            {/* STATISTICS */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-7">
              {stats.map(item => (
                <div key={item.label} className="border border-black/10 dark:border-white/10 rounded-xl p-5 bg-white dark:bg-[#191919]">
                  <div className="flex justify-between text-neutral-500">
                    <span className="text-xs">{item.label}</span>
                    <item.icon size={17}/>
                  </div>
                  <p className="text-3xl font-semibold mt-5 tracking-tight">{item.value}</p>
                  <p className="text-xs text-neutral-500 mt-2">{item.detail}</p>
                </div>
              ))}
            </div>

            {/* RUNTIME + ACTIVITY */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-7">
              <section className="xl:col-span-2 border border-black/10 dark:border-white/10 rounded-xl p-5 bg-white dark:bg-[#191919]">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="font-semibold">Runtime Overview</h3>
                    <p className="text-xs text-neutral-500 mt-1">Local infrastructure</p>
                  </div>
                  <span className="text-xs text-green-600 flex items-center gap-2">
                    <Circle size={7} fill="currentColor"/> Operational
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-5">
                  {[
                    { name: "CPU Usage", value: "24%", icon: Cpu, width: "24%" },
                    { name: "Memory Usage", value: "62%", icon: HardDrive, width: "62%" }
                  ].map(resource => (
                    <div key={resource.name}>
                      <div className="flex justify-between text-sm mb-3">
                        <span className="text-neutral-500 flex gap-2 items-center">
                          <resource.icon size={16}/>{resource.name}
                        </span>
                        <strong>{resource.value}</strong>
                      </div>
                      <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-800">
                        <div className="h-full rounded-full bg-neutral-800 dark:bg-neutral-200" style={{width: resource.width}}/>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-7 pt-5 border-t border-black/10 dark:border-white/10 flex justify-between text-xs">
                  <span className="text-neutral-500">Ollama API Endpoint</span>
                  <code>localhost:11434</code>
                </div>
              </section>

              <section className="border border-black/10 dark:border-white/10 rounded-xl p-5 bg-white dark:bg-[#191919]">
                <div className="flex justify-between mb-5">
                  <h3 className="font-semibold">Quick Actions</h3>
                  <MoreHorizontal size={18}/>
                </div>
                {quickActions.map(({ label, icon: Icon }) => (
                  <button key={label} className="w-full flex items-center justify-between py-3 border-b last:border-0 border-black/5 dark:border-white/5 text-sm hover:opacity-60">
                    <span className="flex gap-3 items-center">
                      <Icon size={16} className="text-neutral-500"/>
                      {label}
                    </span>
                    <ArrowUpRight size={14} className="text-neutral-500"/>
                  </button>
                ))}
              </section>
            </div>

            {/* RECENT ACTIVITY */}
            <section className="border border-black/10 dark:border-white/10 rounded-xl p-5 bg-white dark:bg-[#191919]">
              <div className="flex justify-between items-center mb-5">
                <div>
                  <h3 className="font-semibold">Recent Activity</h3>
                  <p className="text-xs text-neutral-500 mt-1">Latest workspace events</p>
                </div>
                <button className="text-xs text-neutral-500 flex items-center gap-1">
                  View all <ArrowUpRight size={13}/>
                </button>
              </div>

              {recentActivity.map(({ name, description, time, status }) => (
                <div key={name} className="grid grid-cols-4 py-4 border-t border-black/5 dark:border-white/5 items-center text-sm">
                  <span className="font-medium">{name}</span>
                  <span className="text-neutral-500 col-span-2">{description}</span>
                  <span className="text-right text-xs text-neutral-500">{time} · {status}</span>
                </div>
              ))}
            </section>

            <footer className="mt-8 flex justify-between text-[11px] text-neutral-500">
              <span>NEXUS AI · LOCAL INTELLIGENCE</span>
              <span>DEMO DATA · VERSION 0.1.0</span>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}
