import "./ui.css";

// Phone-sized column: centered card on desktop, full width on narrow screens.
// withTabBar: lays the column out so the TabBar sits at the bottom even on short pages.
export default function PhoneColumn({ withTabBar = false, children }) {
  return <main className={withTabBar ? "phone-column phone-column--tabs" : "phone-column"}>{children}</main>;
}
