import { useState } from "react";

import Console from "./Console";
import Login from "./Login";
import TournamentPicker from "./TournamentPicker";
import { type Tournament, getToken } from "./api";

export default function App() {
  const [authed, setAuthed] = useState(() => getToken() !== null);
  const [tournament, setTournament] = useState<Tournament | null>(null);

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }
  if (tournament === null) {
    return (
      <TournamentPicker
        onPick={setTournament}
        onLogout={() => {
          setAuthed(false);
        }}
      />
    );
  }
  return (
    <Console
      tournament={tournament}
      onBack={() => setTournament(null)}
      onLogout={() => {
        setTournament(null);
        setAuthed(false);
      }}
    />
  );
}
