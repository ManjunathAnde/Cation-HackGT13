import "./ui.css";

export default function PrimaryButton({ children, ...props }) {
  return (
    <button className="primary-button" {...props}>
      {children}
    </button>
  );
}
