// The doctor's answer, right-aligned under an answered item.
const CARD_REPLIES = {
  yes: { tone: "yes", text: "Yes, more on this", caption: "Saved to your Vault" },
  not_interested: { tone: "no", text: "Not interested" },
  no_reply: { tone: "muted", text: "No reply" },
};
const OFFER_REPLIES = {
  yes: { tone: "yes", text: "Yes" },
  no: { tone: "no", text: "No thanks" },
};

// type: "card" or "offer"; answer: the message's answer from /inbox.
export default function ReplyBubble({ type, answer }) {
  const reply = (type === "card" ? CARD_REPLIES : OFFER_REPLIES)[answer] || { tone: "muted", text: answer };
  return (
    <div className="reply">
      <p className={`reply__bubble reply__bubble--${reply.tone}`}>
        {reply.caption && <span className="reply__caption">{reply.caption}</span>}
        <span className="reply__text">{reply.text}</span>
      </p>
    </div>
  );
}
