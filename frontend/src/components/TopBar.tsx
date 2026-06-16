import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

export function TopBar({ children }: { children?: React.ReactNode }) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
      <button
        onClick={() => navigate("/documents")}
        className="text-lg font-semibold text-slate-800 hover:text-indigo-600"
      >
        OCR Web App
      </button>
      <div className="flex items-center gap-4">
        {children}
        {user && <span className="text-sm text-slate-500">{user.email}</span>}
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="rounded-md border border-slate-300 px-3 py-1 text-sm hover:bg-slate-50"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
