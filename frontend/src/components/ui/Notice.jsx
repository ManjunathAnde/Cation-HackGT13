import "./ui.css";

export default function Notice({ children }) {
  if (!children) return null;
  return (
    <p className="notice" role="alert">
      {children}
    </p>
  );
}
