import "./ui.css";

// Search field with a small magnifier icon.
export default function SearchInput({ label, ...props }) {
  return (
    <label className="search-input">
      <svg className="search-input__icon" viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="9.5" cy="6.5" r="4.25" />
        <path d="M6.5 9.5 2.5 13.5" />
      </svg>
      <input type="search" className="search-input__field" aria-label={label} {...props} />
    </label>
  );
}
