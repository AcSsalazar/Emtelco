import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Avatar from "../components/Avatar";
import { api, apiErrorMessage } from "../services/api";
import { useAuthStore } from "../store/authStore";
import { fieldErrors, loginSchema, validateField } from "../schemas/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (key) => (event) => {
    const value = event.target.value;
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({
      ...current,
      [key]: validateField(loginSchema, key, value),
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setServerError("");
    const parsed = loginSchema.safeParse(form);
    if (!parsed.success) {
      setErrors(fieldErrors(parsed));
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", form);
      setSession({ user: data.user, access: data.access, refresh: data.refresh });
      navigate("/chat");
    } catch (error) {
      setServerError(apiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand">
          <Avatar size="brand" />
          <div>
            <h1>Emmet</h1>
            <p>Asesor de tecnología</p>
          </div>
        </div>
        <h2>Inicia sesión</h2>
        <p className="muted">Continúa tu conversación con Emmet.</p>

        <form onSubmit={submit} noValidate>
          <label>
            Correo o identificación
            <input
              type="text"
              value={form.email}
              onChange={update("email")}
              autoComplete="username"
              placeholder="correo@ejemplo.com o 1023456789"
            />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={form.password}
              onChange={update("password")}
              autoComplete="current-password"
            />
            {errors.password && <span className="field-error">{errors.password}</span>}
          </label>

          {serverError && <div className="alert">{serverError}</div>}

          <button type="submit" className="primary" disabled={loading}>
            {loading ? "Ingresando…" : "Ingresar"}
          </button>
        </form>

        <p className="switch">
          ¿No tienes cuenta? <Link to="/register">Regístrate</Link>
        </p>
      </div>
    </div>
  );
}
