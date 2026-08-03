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
      <Route element={<RequireAuth />}>
        <Route element={<FencerLayout />}>
          <Route index element={<FencerHome />} />
          <Route path="t/:slug" element={<TournamentDetail />} />
        </Route>
        <Route path="organizer" element={<TournamentPicker />} />
        <Route path="organizer/:slug/console" element={<ConsoleRoute />} />
        <Route path="organizer/:slug/console/:phase" element={<ConsoleRoute />} />
        <Route path="admin" element={<AdminPanel />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
