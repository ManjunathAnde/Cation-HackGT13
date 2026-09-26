import "./ui.css";

export default function TextInput({ invalid, className = "", ...props }) {
  return (
    <input
      className={`text-input ${invalid ? "text-input--invalid" : ""} ${className}`}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}
