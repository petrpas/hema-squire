import { useState } from "react";

import AdminPanel from "./AdminPanel";
import Console, { type Phase } from "./Console";
import FencerHome from "./FencerHome";
import Login from "./Login";
import ProfilePage from "./ProfilePage";
import TournamentDetail from "./TournamentDetail";
import TournamentPicker from "./TournamentPicker";
import { type Tournament, getToken } from "./api";

type View = "home" | "tournament" | "picker" | "console" | "admin" | "profile";

export default function App() {
  const [authed, setAuthed] = useState(() => getToken() !== null);
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [initialPhase, setInitialPhase] = useState<Phase>("load");
  const [view, setView] = useState<View>("home");
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [detailReadOnly, setDetailReadOnly] = useState(false);

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  function logout() {
    setTournament(null);
    setSelectedSlug(null);
    setView("home");
    setAuthed(false);
  }

  const onProfile = () => setView("profile");
  const onAdmin = () => setView("admin");
  const onOrganizer = () => setView("picker");
  const onHome = () => setView("home");

  if (view === "admin") {
    return (
      <AdminPanel
        onBack={() => setView(tournament ? "console" : "picker")}
        onProfile={onProfile}
        onOrganizer={onOrganizer}
        onFencer={onHome}
        onLogout={logout}
      />
    );
  }
  if (view === "profile") {
    return (
      <ProfilePage onAdmin={onAdmin} onOrganizer={onOrganizer} onFencer={onHome} onLogout={logout} />
    );
  }
  if (view === "console" && tournament) {
    return (
      <Console
        tournament={tournament}
        initialPhase={initialPhase}
        onBack={onOrganizer}
        onProfile={onProfile}
        onAdmin={onAdmin}
        onFencer={onHome}
        onLogout={logout}
      />
    );
  }
  if (view === "picker") {
    return (
      <TournamentPicker
        onPick={(picked, phase) => {
          setTournament(picked);
          setInitialPhase(phase ?? "load");
          setView("console");
        }}
        onProfile={onProfile}
        onAdmin={onAdmin}
        onFencer={onHome}
        onLogout={logout}
      />
    );
  }
  if (view === "tournament" && selectedSlug) {
    return (
      <TournamentDetail
        slug={selectedSlug}
        readOnly={detailReadOnly}
        onBack={onHome}
        onProfile={onProfile}
        onAdmin={onAdmin}
        onOrganizer={onOrganizer}
        onLogout={logout}
      />
    );
  }
  return (
    <FencerHome
      onOpen={(slug, readOnly) => {
        setSelectedSlug(slug);
        setDetailReadOnly(readOnly ?? false);
        setView("tournament");
      }}
      onProfile={onProfile}
      onAdmin={onAdmin}
      onOrganizer={onOrganizer}
      onLogout={logout}
    />
  );
}
