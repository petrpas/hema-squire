import { useState } from "react";

import Console, { type Phase } from "./Console";
import Login from "./Login";
import TournamentPicker from "./TournamentPicker";
import { type Tournament, getToken } from "./api";

export default function App() {
  const [authed, setAuthed] = useState(() => getToken() !== null);
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [initialPhase, setInitialPhase] = useState<Phase>("load");

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }
  if (tournament === null) {
    return (
      <TournamentPicker
        onPick={(picked, phase) => {
          setTournament(picked);
          setInitialPhase(phase ?? "load");
        }}
        onLogout={() => {
          setAuthed(false);
        }}
      />
    );
  }
  return (
    <Console
      tournament={tournament}
      initialPhase={initialPhase}
      onBack={() => setTournament(null)}
      onLogout={() => {
        setTournament(null);
        setAuthed(false);
      }}
    />
  );
}
