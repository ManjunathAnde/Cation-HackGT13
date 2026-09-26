import "./ui.css";

export default function FieldError({ id, children }) {
  if (!children) return null;
  return (
    <p className="field-error" id={id} role="alert">
      {children}
    </p>
  );
}
