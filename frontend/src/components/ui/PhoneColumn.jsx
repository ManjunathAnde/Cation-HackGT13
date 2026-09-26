import "./ui.css";

// Phone-sized column: centered card on desktop, full width on narrow screens.
export default function PhoneColumn({ children }) {
  return <main className="phone-column">{children}</main>;
}
