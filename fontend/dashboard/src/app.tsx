import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./router";
import "bootstrap/dist/css/bootstrap.min.css";
import "./styles/global.css";

/**
 * Main App Component
 * Entry point của ứng dụng
 */

export function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}

export default App;
