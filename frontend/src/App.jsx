import { useEffect } from "react";
import { redirect, usePath } from "./router.jsx";
import Brief from "./pages/Brief.jsx";
import Console from "./pages/Console.jsx";
import NotFound from "./pages/NotFound.jsx";
import Onboard from "./pages/Onboard.jsx";

const ROUTES = {
  "/console": Console,
  "/phone/onboard": Onboard,
  "/phone/brief": Brief,
};

const REDIRECTS = {
  "/": "/console",
  "/phone": "/phone/brief",
};

export default function App() {
  const path = usePath();
  const target = REDIRECTS[path];

  useEffect(() => {
    if (target) redirect(target);
  }, [target]);

  if (target) return null;
  const Page = ROUTES[path] || NotFound;
  return <Page />;
}
