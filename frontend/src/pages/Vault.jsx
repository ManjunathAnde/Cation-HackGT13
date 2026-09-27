import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useDoctorId } from "../router.jsx";
import DoctorGate from "../components/phone/DoctorGate.jsx";
import ResearchCard from "../components/phone/ResearchCard.jsx";
import Eyebrow from "../components/ui/Eyebrow.jsx";
import PhoneColumn from "../components/ui/PhoneColumn.jsx";
import SearchInput from "../components/ui/SearchInput.jsx";
import SerifHeading from "../components/ui/SerifHeading.jsx";
import TabBar from "../components/ui/TabBar.jsx";
import Wordmark from "../components/ui/Wordmark.jsx";
import "./brief.css";

const DEBOUNCE_MS = 300;

function vaultPath(doctorId, q) {
  return `/vault/${doctorId}` + (q ? `?q=${encodeURIComponent(q)}` : "");
}

function readsLine(count) {
  return `${count} ${count === 1 ? "read" : "reads"} worth returning to`;
}

// Loads the vault right away on open, then searches on the backend 300 ms after typing stops.
// Only the newest request's response is used. `total` comes from the latest load without a query.
function useVaultSearch(doctorId, query) {
  const [state, setState] = useState({ cards: null, total: 0, shownQuery: "", failed: false });
  const sent = useRef(0);
  const loaded = useRef(false);

  useEffect(() => {
    const q = query.trim();
    const timer = setTimeout(
      async () => {
        const id = ++sent.current;
        const result = await api("GET", vaultPath(doctorId, q));
        if (id !== sent.current) return;
        loaded.current = true;
        setState((previous) =>
          result.ok
            ? { cards: result.data, total: q ? previous.total : result.data.length, shownQuery: q, failed: false }
            : { ...previous, failed: true }
        );
      },
      loaded.current ? DEBOUNCE_MS : 0
    );
    return () => clearTimeout(timer);
  }, [doctorId, query]);

  return state;
}

function Saved() {
  const [query, setQuery] = useState("");
  const doctorId = useDoctorId();
  const { cards, total, shownQuery, failed } = useVaultSearch(doctorId, query);

  return (
    <PhoneColumn withTabBar>
      <div className="brief">
        <Wordmark />
        <header className="brief__header">
          <Eyebrow>Saved research</Eyebrow>
          <SerifHeading as="h1" size="page">
            Your Vault
          </SerifHeading>
          {total > 0 && <p className="brief__subtitle">{readsLine(total)}</p>}
        </header>
        <div className="vault__search">
          <SearchInput
            label="Search saved research"
            placeholder="Search title or topic"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {failed && <p className="vault__note">Couldn't search right now.</p>}
        </div>
        {cards && cards.length === 0 && (
          <p className="vault__empty">
            {shownQuery
              ? `No saved reads match '${shownQuery}'.`
              : "Nothing saved yet. Cards you answer 'Yes, more on this' appear here."}
          </p>
        )}
        {cards && cards.length > 0 && (
          <ul className="vault__list">
            {cards.map((card) => (
              <li key={card.id} data-card={card.id}>
                <ResearchCard card={card} />
              </li>
            ))}
          </ul>
        )}
      </div>
      <TabBar />
    </PhoneColumn>
  );
}

// The doctor's vault: saved cards with backend search, at /phone/vault.
export default function Vault() {
  return (
    <DoctorGate>
      <Saved />
    </DoctorGate>
  );
}
