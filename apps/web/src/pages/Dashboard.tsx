import { Button } from "@/components/ui/button";
import { Bot, Brain, Database, Layers } from "lucide-react";

const services = [
  {
    name: "Orchestrator",
    description: "FastAPI gateway that routes requests to specialised agents",
    icon: Layers,
    port: 8000,
    status: "idle",
  },
  {
    name: "LLM Manager",
    description: "Manages model routing between OpenAI, Anthropic & Ollama",
    icon: Bot,
    port: 8001,
    status: "idle",
  },
  {
    name: "Memory",
    description: "Vector-based long-term and short-term memory service",
    icon: Brain,
    port: 8002,
    status: "idle",
  },
  {
    name: "Local Agent",
    description: "On-device agent for file system & tool execution",
    icon: Database,
    port: 8003,
    status: "idle",
  },
];

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="mb-12 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-gradient">
            Cammina-AI
          </h1>
          <p className="mt-1 text-muted-foreground text-sm">
            Local-first AI orchestration platform
          </p>
        </div>
        <Button variant="outline" size="sm" id="refresh-btn">
          Refresh Status
        </Button>
      </header>

      {/* Service Cards */}
      <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {services.map((svc) => {
          const Icon = svc.icon;
          return (
            <article
              key={svc.name}
              id={`service-card-${svc.name.toLowerCase().replace(/\s/g, "-")}`}
              className="glass rounded-xl p-6 animate-fade-in hover:glow transition-all duration-300 group"
            >
              <div className="mb-4 flex items-center justify-between">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
                  <Icon className="h-5 w-5" />
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    svc.status === "running"
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      svc.status === "running"
                        ? "bg-emerald-400 animate-pulse"
                        : "bg-muted-foreground"
                    }`}
                  />
                  {svc.status}
                </span>
              </div>
              <h2 className="text-sm font-semibold text-foreground">
                {svc.name}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                {svc.description}
              </p>
              <p className="mt-3 font-mono text-xs text-primary/70">
                :{svc.port}
              </p>
            </article>
          );
        })}
      </section>

      {/* Footer */}
      <footer className="mt-16 text-center text-xs text-muted-foreground">
        Cammina-AI Monorepo · React + FastAPI · pnpm workspaces
      </footer>
    </div>
  );
}
