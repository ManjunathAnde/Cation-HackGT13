import "./ui.css";

export default function Panel({ className = "", children, ...props }) {
  return (
    <section className={`panel ${className}`.trim()} {...props}>
      {children}
    </section>
  );
}
