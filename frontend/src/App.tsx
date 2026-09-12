import { Route, Routes } from "react-router-dom";

import AdminPanel from "./AdminPanel";
import ConsoleRoute from "./ConsoleRoute";
import FencerHome from "./FencerHome";
import FencerLayout from "./FencerLayout";
import NotFound from "./NotFound";
import ProfilePage from "./ProfilePage";
import RequireAuth from "./RequireAuth";
import TournamentDetail from "./TournamentDetail";
import TournamentPicker from "./TournamentPicker";

export default function App() {
  return (
    <Routes>
      {/* Public: the tournament list and a tournament's detail render for a
          visitor holding no credential (spec `public-browsing`). The one
          exception inside them is `/?tab=mine`, which names an account's own
          list — FencerLayout gates that tab itself, rather than `/` being
          split into two routes for what is otherwise the same screen. */}
      <Route element={<FencerLayout />}>
        <Route index element={<FencerHome />} />
        <Route path="t/:slug" element={<TournamentDetail />} />
      </Route>
      {/* Everything else keeps the gate: Login renders in place at the
          requested URL, so the destination survives signing in. */}
      <Route element={<RequireAuth />}>
        <Route path="organizer" element={<TournamentPicker />} />
        <Route path="organizer/:slug/console" element={<ConsoleRoute />} />
        <Route path="organizer/:slug/console/:phase" element={<ConsoleRoute />} />
        <Route path="admin" element={<AdminPanel />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
      {/* Not-found is public: an address that names no screen is not a
          credential problem, and showing Login for one would tell a
          signed-out visitor to sign in for a page that does not exist. */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
