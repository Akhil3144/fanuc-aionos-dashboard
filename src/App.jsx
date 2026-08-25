import { Navigate, Route, Routes } from "react-router-dom";
import FleetPage from "./pages/FleetPage";
import HomePage from "./pages/HomePage";
import RobotDetailPage from "./pages/RobotDetailPage";
import GlobalChatLauncher from "./components/GlobalChatLauncher";

function App() {
  return (
    <><Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/fleet" element={<FleetPage />} />
      <Route path="/legacy" element={<RobotDetailPage />} />
      <Route path="/robot/:robotId" element={<RobotDetailPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes><GlobalChatLauncher /></>
  );
}

export default App;
