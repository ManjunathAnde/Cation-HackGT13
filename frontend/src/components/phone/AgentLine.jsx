import AgentAvatar from "../ui/AgentAvatar.jsx";

export default function AgentLine({ children }) {
  return (
    <div className="agent-line">
      <AgentAvatar />
      <p className="agent-line__text">{children}</p>
    </div>
  );
}
