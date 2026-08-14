import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ServiceStatus } from "@/components/service-status";
import { getHealth } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

const PLANNED_CAPABILITIES = [
  {
    name: "Knowledge Base",
    description: "Upload internal documents and search them with citations.",
  },
  {
    name: "RAG Assistant",
    description: "Ask questions and get answers grounded in your documents.",
  },
  {
    name: "Complaint Analysis",
    description: "An AI agent classifies complaints and drafts responses.",
  },
  {
    name: "Human Approvals",
    description: "Every AI-recommended action waits for human sign-off.",
  },
];

export default async function Home() {
  const health = await getHealth();
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-12 sm:px-6">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">OpsPilot AI</h1>
          <Badge variant="secondary">Portfolio MVP</Badge>
          <Button
            variant="outline"
            className="ml-auto"
            render={<a href={user ? "/dashboard" : "/login"} />}
          >
            {user ? "Dashboard" : "Log in"}
          </Button>
        </div>
        <p className="max-w-xl text-muted-foreground">
          An AI business-operations platform skeleton: this page is a Phase 2
          frontend skeleton that verifies the Next.js frontend can reach the
          FastAPI backend. No AI features are implemented yet.
        </p>
      </header>

      <ServiceStatus health={health} />

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-semibold tracking-tight">
          Planned capabilities
        </h2>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {PLANNED_CAPABILITIES.map((capability) => (
            <li
              key={capability.name}
              className="flex flex-col gap-1 rounded-xl border p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{capability.name}</span>
                <Badge variant="outline">Planned</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {capability.description}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <footer>
        <Button
          variant="outline"
          render={
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
            />
          }
        >
          View FastAPI docs
        </Button>
      </footer>
    </div>
  );
}
