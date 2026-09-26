import "./ui.css";

export default function SecondaryButton({ children, ...props }) {
  return (
    <button className="secondary-button" {...props}>
      {children}
    </button>
  );
}
