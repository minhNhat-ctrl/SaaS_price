import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./router";
import { AuthProvider } from "./shared/AuthContext";
import "bootstrap/dist/css/bootstrap.min.css";
import "./styles/global.css";

/**
 * Main App Component
 * Entry point của ứng dụng
 */

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
