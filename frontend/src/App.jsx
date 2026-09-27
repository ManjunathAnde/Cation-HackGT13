import { useEffect } from "react";
import { redirect, useDoctorId, useLocation } from "./router.jsx";
import Brief from "./pages/Brief.jsx";
import Console from "./pages/Console.jsx";
import NotFound from "./pages/NotFound.jsx";
import Onboard from "./pages/Onboard.jsx";
import Vault from "./pages/Vault.jsx";

const ROUTES = {
  "/console": Console,
  "/phone/onboard": Onboard,
  "/phone/brief": Brief,
  "/phone/vault": Vault,
};

const REDIRECTS = {
  "/": "/console",
  "/phone": "/phone/brief",
};

export default function App() {
  const { path, search } = useLocation();
  const doctorId = useDoctorId();
  const target = REDIRECTS[path];

  useEffect(() => {
    if (target) redirect(target + search); // keeps ?doctor=
  }, [target, search]);

  if (target) return null;
  const Page = ROUTES[path] || NotFound;
  // Keyed by doctor: switching ?doctor= rebuilds the page, so no data from the previous doctor remains.
  return <Page key={path.startsWith("/phone/") ? doctorId : path} />;
}
