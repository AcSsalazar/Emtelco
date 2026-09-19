import { Link, Outlet } from "react-router-dom";
import Avatar from "./Avatar";
import { useAuthStore } from "../store/authStore";

export default function Layout() {
  const access = useAuthStore((state) => state.access);

  return (
    <div className="site">
      <header className="site-header">
        <div className="site-header-inner">
          <Link to="/" className="site-logo">
            <Avatar size="brand" />
            <span className="logo-text">
              Emtelco <span className="logo-sub">· Emmet</span>
            </span>
          </Link>
          <nav className="site-nav">
            <Link to="/">Home</Link>
            <Link to="/acerca">Acerca de</Link>
            {access ? (
              <Link to="/chat" className="nav-cta">
                Ir al chat
              </Link>
            ) : (
              <>
                <Link to="/login">Iniciar sesión</Link>
                <Link to="/register" className="nav-cta">
                  Registrarse
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="site-main">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="site-footer-inner">
          <div className="footer-brand">
            <strong>Emmet</strong>
            <p>Asesor IA de Emtelco para productos, pedidos, entregas y garantías.</p>
          </div>
          <nav className="footer-nav">
            <Link to="/">Home</Link>
            <Link to="/acerca">Acerca de</Link>
            <Link to="/login">Iniciar sesión</Link>
            <Link to="/register">Registrarse</Link>
          </nav>
        </div>
        <div className="footer-bottom">
          © {new Date().getFullYear()} Emtelco · Demo técnica
        </div>
      </footer>
    </div>
  );
}
