import { useEffect, useState } from "react";

import AdminPanel from "./AdminPanel";
import Console, { type Phase } from "./Console";
import FencerHome, { useUpcoming } from "./FencerHome";
import FencerShell, { type HomeTab } from "./FencerShell";
import Login from "./Login";
import ProfilePage from "./ProfilePage";
import TournamentDetail from "./TournamentDetail";
import TournamentPicker from "./TournamentPicker";
import { type Account, type Tournament, api, getToken } from "./api";
import i18n from "./i18n";

type View = "home" | "tournament" | "picker" | "console" | "admin" | "profile";

/** The fencer's area: one heading over either the tournament list or a
 *  tournament's detail. Both live under the same shell, and the selected tab
 *  is held above them, so opening a tournament changes only what is under the
 *  heading. Mounted only while authenticated, so its fetches never fire on the
 *  login page. */
function FencerArea({
  view,
  slug,
  readOnly,
  tab,
  onSelectTab,
  onOpen,
  onClose,
  onProfile,
  onAdmin,
  onOrganizer,
  onLogout,
}: {
  view: View;
  slug: string | null;
  readOnly: boolean;
  tab: HomeTab;
  onSelectTab: (tab: HomeTab) => void;
  onOpen: (slug: string, readOnly?: boolean) => void;
  onClose: () => void;
  onProfile: () => void;
  onAdmin: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
}) {
  const [account, setAccount] = useState<Account | null>(null);
  const { announced, open } = useUpcoming();

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  return (
    <FencerShell
      account={account}
      tab={tab}
      onSelectTab={onSelectTab}
      counts={{ announced: announced?.length, open: open?.length }}
      onProfile={onProfile}
      onAdmin={onAdmin}
      onOrganizer={onOrganizer}
      onLogout={onLogout}
    >
      {view === "tournament" && slug !== null ? (
        <TournamentDetail slug={slug} readOnly={readOnly} onClose={onClose} />
      ) : (
        <FencerHome tab={tab} announced={announced} open={open} onOpen={onOpen} />
      )}
    </FencerShell>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(() => getToken() !== null);
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [initialPhase, setInitialPhase] = useState<Phase>("load");
  const [view, setView] = useState<View>("home");
  const [tab, setTab] = useState<HomeTab>("open");
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [detailReadOnly, setDetailReadOnly] = useState(false);

  useEffect(() => {
    if (authed) {
      api.account().then((account) => void i18n.changeLanguage(account.language), () => {});
    }
  }, [authed]);

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
  return (
    <FencerArea
      view={view}
      slug={selectedSlug}
      readOnly={detailReadOnly}
      tab={tab}
      // selecting a filter tab leaves an open detail for that list — the
      // heading is the list's, so it navigates like the list's
      onSelectTab={(next) => {
        setTab(next);
        setView("home");
      }}
      onOpen={(slug, readOnly) => {
        setSelectedSlug(slug);
        setDetailReadOnly(readOnly ?? false);
        setView("tournament");
      }}
      onClose={onHome}
      onProfile={onProfile}
      onAdmin={onAdmin}
      onOrganizer={onOrganizer}
      onLogout={logout}
    />
  );
}
