import "./ui.css";

export default function SerifHeading({ as: Tag = "h2", size = "section", children }) {
  return <Tag className={`serif-heading serif-heading--${size}`}>{children}</Tag>;
}
