import { navigate, usePath, withSearch } from "../../router.jsx";
import "./ui.css";

const TABS = [
  { path: "/phone/brief", letter: "B", label: "Brief" },
  { path: "/phone/vault", letter: "V", label: "Vault" },
];

function go(event, path) {
  event.preventDefault();
  navigate(withSearch(path));
}

// Bottom tab bar of the doctor's app.
export default function TabBar() {
  const current = usePath();
  return (
    <nav className="tab-bar" aria-label="Doctor app">
      {TABS.map(({ path, letter, label }) => (
        <a
          key={path}
          href={withSearch(path)}
          className={path === current ? "tab-bar__tab tab-bar__tab--active" : "tab-bar__tab"}
          aria-current={path === current ? "page" : undefined}
          onClick={(event) => go(event, path)}
        >
          <span className="tab-bar__box" aria-hidden="true">
            {letter}
          </span>
          {label}
        </a>
      ))}
    </nav>
  );
}
