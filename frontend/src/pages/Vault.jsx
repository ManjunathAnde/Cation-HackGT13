import DoctorGate from "../components/phone/DoctorGate.jsx";
import PhoneColumn from "../components/ui/PhoneColumn.jsx";
import TabBar from "../components/ui/TabBar.jsx";
import Wordmark from "../components/ui/Wordmark.jsx";
import "./brief.css";

// Placeholder until the vault page is built (Checkpoint 9).
export default function Vault() {
  return (
    <DoctorGate>
      <PhoneColumn withTabBar>
        <div className="brief">
          <Wordmark />
          <p className="brief__placeholder">Coming soon</p>
        </div>
        <TabBar />
      </PhoneColumn>
    </DoctorGate>
  );
}
