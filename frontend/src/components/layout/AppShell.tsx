import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, ScanText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/stores/authStore";

interface Props {
  children: ReactNode;
  /** Extra controls rendered in the header (e.g. document title, page nav). */
  toolbar?: ReactNode;
  /** When true, the main area fills the viewport without scroll (editor). */
  fill?: boolean;
}

export function AppShell({ children, toolbar, fill = false }: Props) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-background px-4">
        <button
          onClick={() => navigate("/documents")}
          className="flex items-center gap-2 font-semibold tracking-tight"
        >
          <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ScanText className="size-4" />
          </span>
          <span>Fatourat OCR</span>
        </button>

        {toolbar && (
          <>
            <Separator orientation="vertical" className="mx-1 h-6" />
            <div className="flex min-w-0 flex-1 items-center gap-2">{toolbar}</div>
          </>
        )}

        <div className="ml-auto flex items-center gap-3">
          {user && (
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {user.email}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            <LogOut className="size-4" />
            Log out
          </Button>
        </div>
      </header>

      <main className={fill ? "min-h-0 flex-1" : "flex-1 overflow-y-auto"}>
        {children}
      </main>
    </div>
  );
}
