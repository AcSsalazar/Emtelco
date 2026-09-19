import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import Avatar from "./Avatar";

function formatPrice(value) {
  if (value === null || value === undefined) return "";
  const number = Number(value);
  if (Number.isNaN(number)) return "";
  return `$${number.toLocaleString("es-CO")} COP`;
}

function ProductCards({ products }) {
  if (!products?.length) return null;
  return (
    <div className="product-cards">
      {products.map((product) => (
        <div className="product-card" key={product.id}>
          <div className="product-thumb">
            {product.image_url ? (
              <img src={product.image_url} alt={product.name} loading="lazy" />
            ) : (
              <span className="thumb-fallback">{product.brand?.[0] || "?"}</span>
            )}
          </div>
          <div className="product-info">
            <span className="product-brand">{product.brand}</span>
            <span className="product-name">{product.name}</span>
            {product.sku && <span className="product-sku">{product.sku}</span>}
            <span className="product-price">{formatPrice(product.price)}</span>
            {product.in_stock === false && (
              <span className="product-stock">Sin stock</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const products = message.metadata?.products;

  return (
    <div className={`message-row ${isUser ? "is-user" : "is-assistant"}`}>
      {!isUser && <Avatar />}
      <div className="message-content">
        {isUser ? (
          <div className="bubble user">{message.content}</div>
        ) : (
          <div className="bubble assistant markdown">
            <ReactMarkdown remarkPlugins={[remarkBreaks]}>{message.content}</ReactMarkdown>
          </div>
        )}
        {!isUser && <ProductCards products={products} />}
      </div>
    </div>
  );
}
