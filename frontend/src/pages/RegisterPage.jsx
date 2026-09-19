import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Avatar from "../components/Avatar";
import { api, apiErrorMessage } from "../services/api";
import { useAuthStore } from "../store/authStore";
import { fieldErrors, registerSchema, validateField } from "../schemas/auth";

const initial = {
  identification: "",
  fullName: "",
  phone: "",
  email: "",
  password: "",
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (key) => (event) => {
    const value = event.target.value;
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({
      ...current,
      [key]: validateField(registerSchema, key, value),
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setServerError("");
    const parsed = registerSchema.safeParse(form);
    if (!parsed.success) {
      setErrors(fieldErrors(parsed));
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", {
        identification: form.identification,
        full_name: form.fullName,
        phone: form.phone,
        email: form.email,
        password: form.password,
      });
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
        <h2>Crea tu cuenta</h2>
        <p className="muted">Regístrate para hablar con Emmet.</p>

        <form onSubmit={submit} noValidate>
          <label>
            Identificación
            <input
              value={form.identification}
              onChange={update("identification")}
              inputMode="numeric"
              placeholder="Entre 4 y 11 dígitos"
            />
            {errors.identification && (
              <span className="field-error">{errors.identification}</span>
            )}
          </label>
          <label>
            Nombre completo
            <input value={form.fullName} onChange={update("fullName")} />
            {errors.fullName && <span className="field-error">{errors.fullName}</span>}
          </label>
          <label>
            Teléfono
            <input
              value={form.phone}
              onChange={update("phone")}
              inputMode="numeric"
              placeholder="10 dígitos, inicia en 3 o 6"
            />
            {errors.phone && <span className="field-error">{errors.phone}</span>}
          </label>
          <label>
            Correo
            <input type="email" value={form.email} onChange={update("email")} />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={form.password}
              onChange={update("password")}
              placeholder="Mínimo 8 caracteres"
            />
            {errors.password && <span className="field-error">{errors.password}</span>}
          </label>

          {serverError && <div className="alert">{serverError}</div>}

          <button type="submit" className="primary" disabled={loading}>
            {loading ? "Creando cuenta…" : "Registrarme"}
          </button>
        </form>

        <p className="switch">
          ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
        </p>
      </div>
    </div>
  );
}
