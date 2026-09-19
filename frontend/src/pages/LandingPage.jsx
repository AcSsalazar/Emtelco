import { Link } from "react-router-dom";

const features = [
  {
    title: "Venta consultiva",
    text: "Entiende tu necesidad y presupuesto, consulta el catálogo real y recomienda justificando cada opción.",
  },
  {
    title: "Seguimiento de pedidos",
    text: "Consulta el estado, el número de seguimiento y la fecha estimada de entrega de tus pedidos.",
  },
  {
    title: "Garantías y soporte",
    text: "Valida la cobertura, registra solicitudes de garantía y crea tickets de soporte cuando hace falta.",
  },
];

export default function LandingPage() {
  return (
    <div className="landing">
      <section className="hero">
        <p className="eyebrow">Asistente IA para retail de tecnología</p>
        <h1>
          Compra y postventa más simples, con un asesor que entiende tu caso.
        </h1>
        <p className="lead">
          Emmet consulta el catálogo, tus pedidos y tus garantías en tiempo real y
          te acompaña hasta resolver. Sin datos inventados: cada precio, fecha y
          estado sale del sistema.
        </p>
        <div className="hero-actions">
          <Link to="/register" className="btn-primary">
            Crear cuenta
          </Link>
          <Link to="/login" className="btn-secondary">
            Iniciar sesión
          </Link>
        </div>
      </section>

      <section className="features">
        {features.map((feature) => (
          <article className="feature-card" key={feature.title}>
            <h2>{feature.title}</h2>
            <p>{feature.text}</p>
          </article>
        ))}
      </section>

      <section className="cta-band">
        <div>
          <h2>Prueba los tres escenarios de la demo</h2>
          <p>
            Venta consultiva, seguimiento de pedido y gestión de garantía, con
            memoria, moderación y escalamiento a una persona del equipo.
          </p>
        </div>
        <Link to="/register" className="btn-primary">
          Empezar
        </Link>
      </section>
    </div>
  );
}
