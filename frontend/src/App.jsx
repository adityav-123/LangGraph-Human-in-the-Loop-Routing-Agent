import Queue from "./pages/Queue";
import { Dashboard } from "./pages/Dashboard";
import { AuthProvider, useAuth } from "./components/AuthProvider";
import { Login } from "./pages/Login";

function AppContent() {
  const { user } = useAuth();
  
  if (!user) {
    return <Login />;
  }

  return (
    <Dashboard>
      <Queue />
    </Dashboard>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
