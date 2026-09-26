import { useId, useState } from "react";
import TextInput from "./ui/TextInput.jsx";
import RemovablePill from "./ui/RemovablePill.jsx";
import "./ConditionTypeahead.css";

// Friendly label → exact API value. Only these can be selected; free text is never sent.
export const CONDITION_OPTIONS = [
  { label: "Type 2 diabetes (T2D)", value: "type 2 diabetes" },
  { label: "Chronic kidney disease (CKD)", value: "chronic kidney disease" },
];
const COVERAGE_HINT = "Cation currently covers: Type 2 diabetes, Chronic kidney disease.";

export default function ConditionTypeahead({ inputId, selected, onChange, invalid, describedBy }) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [navigated, setNavigated] = useState(false); // arrow keys used since the last keystroke

  const needle = query.trim().toLowerCase();
  const suggestions = CONDITION_OPTIONS.filter(
    (option) => !selected.includes(option.value) && option.label.toLowerCase().includes(needle),
  );
  const listOpen = open && suggestions.length > 0;
  const active = Math.min(highlight, suggestions.length - 1);

  function select(option) {
    onChange([...selected, option.value]);
    setQuery("");
    setHighlight(0);
    setShowHint(false);
    setNavigated(false);
  }

  function onKeyDown(event) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setNavigated(true);
      if (suggestions.length) {
        const step = event.key === "ArrowDown" ? 1 : -1;
        setHighlight((active + step + suggestions.length) % suggestions.length);
      }
    } else if (event.key === "Enter") {
      event.preventDefault(); // Enter here never submits the form
      if (listOpen && (needle || navigated)) select(suggestions[active]);
      else if (needle) setShowHint(true);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="typeahead">
      <TextInput
        id={inputId}
        type="text"
        role="combobox"
        autoComplete="off"
        placeholder="Type a condition, e.g. CKD"
        aria-expanded={listOpen}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={listOpen ? `${listId}-${active}` : undefined}
        aria-describedby={describedBy}
        invalid={invalid}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          setHighlight(0);
          setShowHint(false);
          setNavigated(false);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />

      {listOpen && (
        <ul className="typeahead__list" id={listId} role="listbox">
          {suggestions.map((option, index) => (
            <li
              key={option.value}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              className={`typeahead__option ${index === active ? "typeahead__option--active" : ""}`}
              onMouseDown={(event) => event.preventDefault()} // keep focus in the input
              onMouseEnter={() => setHighlight(index)}
              onClick={() => select(option)}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}

      {showHint && <p className="typeahead__hint">{COVERAGE_HINT}</p>}

      {selected.length > 0 && (
        <div className="typeahead__pills">
          {selected.map((value) => {
            const option = CONDITION_OPTIONS.find((o) => o.value === value);
            return (
              <RemovablePill
                key={value}
                label={option.label}
                onRemove={() => onChange(selected.filter((v) => v !== value))}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
