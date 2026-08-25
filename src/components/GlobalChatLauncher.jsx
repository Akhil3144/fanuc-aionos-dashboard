import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import AskMyRobot from "./AskMyRobot";
import { robotRegistry } from "../data/robotRegistry";
import { resolveChatContext } from "../utils/chatContext";
import "./GlobalChatLauncher.css";

export const OPEN_GLOBAL_CHAT = "fanuc:open-chat";

export default function GlobalChatLauncher() {
  const [open, setOpen] = useState(false);
  const closeRef = useRef(null);
  const location = useLocation();
  const { scope, registryRobot } = resolveChatContext(location.pathname);

  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener(OPEN_GLOBAL_CHAT, show);
    return () => window.removeEventListener(OPEN_GLOBAL_CHAT, show);
  }, []);
  useEffect(() => { if (open) closeRef.current?.focus(); }, [open]);

  return (
    <>
      <button className="global-chat-button" type="button" aria-label="Ask My Robot" title="Ask My Robot" aria-expanded={open} onClick={() => setOpen(true)}>
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 5h14v10H9l-4 4V5Z"/><path d="M8 9h8M8 12h5"/></svg>
      </button>
      {open && <div className="global-chat-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
        <aside className="global-chat-drawer" role="dialog" aria-modal="true" aria-label="Ask My Robot chat">
          <div className="global-chat-drawer-head"><div><span>{scope} CONTEXT</span><strong>{registryRobot?.id || `ALL ${robotRegistry.length} ROBOTS`}</strong></div><button ref={closeRef} type="button" aria-label="Close Ask My Robot" onClick={() => setOpen(false)}>×</button></div>
          <AskMyRobot scope={scope} robotId={registryRobot?.id} selectedRobotId={registryRobot?.id} registry={robotRegistry} robots={robotRegistry} registryRobot={registryRobot} />
        </aside>
      </div>}
    </>
  );
}
