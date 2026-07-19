import { useState } from "react";

import AdminPanel from "./AdminPanel";
import Console, { type Phase } from "./Console";
import Login from "./Login";
import ProfilePage from "./ProfilePage";
import TournamentPicker from "./TournamentPicker";
import { type Tournament, getToken } from "./api";

type View = "picker" | "console" | "admin" | "profile";

export default function App() {
  const [authed, setAuthed] = useState(() => getToken() !== null);
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [initialPhase, setInitialPhase] = useState<Phase>("load");
  const [view, setView] = useState<View>("picker");

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  function logout() {
    setTournament(null);
    setView("picker");
    setAuthed(false);
  }

  const onProfile = () => setView("profile");
  const onAdmin = () => setView("admin");
  const onOrganizer = () => setView("picker");

  if (view === "admin") {
    return (
      <AdminPanel
        onBack={() => setView(tournament ? "console" : "picker")}
        onProfile={onProfile}
        onOrganizer={onOrganizer}
        onLogout={logout}
      />
    );
  }
  if (view === "profile") {
    return <ProfilePage onAdmin={onAdmin} onOrganizer={onOrganizer} onLogout={logout} />;
  }
  if (view === "console" && tournament) {
    return (
      <Console
        tournament={tournament}
        initialPhase={initialPhase}
        onBack={onOrganizer}
        onProfile={onProfile}
        onAdmin={onAdmin}
        onLogout={logout}
      />
    );
  }
  return (
    <TournamentPicker
      onPick={(picked, phase) => {
        setTournament(picked);
        setInitialPhase(phase ?? "load");
        setView("console");
      }}
      onProfile={onProfile}
      onAdmin={onAdmin}
      onLogout={logout}
    />
  );
}
