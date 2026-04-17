import { createBrowserRouter } from "react-router";
import { DashboardLayout } from "./components/DashboardLayout";
import { Upload } from "./pages/Upload";
import { Summary } from "./pages/Summary";
import { Skills } from "./pages/Skills";
import { Evidence } from "./pages/Evidence";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { Help } from "./pages/Help";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: DashboardLayout,
    children: [
      {
        index: true,
        Component: Upload,
      },
      {
        path: "summary",
        Component: Summary,
      },
      {
        path: "skills",
        Component: Skills,
      },
      {
        path: "evidence",
        Component: Evidence,
      },
      {
        path: "reports",
        Component: Reports,
      },
      {
        path: "settings",
        Component: Settings,
      },
      {
        path: "help",
        Component: Help,
      },
    ],
  },
], {
  basename: import.meta.env.BASE_URL,
});
