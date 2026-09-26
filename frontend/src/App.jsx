import { usePath } from "./router.jsx";
import Brief from "./pages/Brief.jsx";
import Health from "./pages/Health.jsx";
import NotFound from "./pages/NotFound.jsx";
import Onboard from "./pages/Onboard.jsx";

const ROUTES = {
  "/": Health,
  "/phone/onboard": Onboard,
  "/phone/brief": Brief,
};

export default function App() {
  const path = usePath();
  const Page = ROUTES[path] || NotFound;
  return <Page />;
}
