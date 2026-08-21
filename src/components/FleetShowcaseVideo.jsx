import { useCallback, useEffect, useRef, useState } from "react";
import { fleetVideoPlaylist } from "../services/fleetVideoPlaylist";
import "./FleetShowcaseVideo.css";

export const DISPLAY_DURATION_MS = 7000;
const PLAYBACK_FAILURE_TIMEOUT_MS = 4000;
const REQUESTED_PLAYBACK_RATE = 2;

function youtubeEmbedUrl(videoId) {
  const params = new URLSearchParams({
    autoplay: "1", mute: "1", playsinline: "1", controls: "0",
    rel: "0", enablejsapi: "1", modestbranding: "1",
  });
  return `https://www.youtube.com/embed/${videoId}?${params}`;
}

function FleetShowcaseVideo() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const iframeRef = useRef(null);
  const failureTimerRef = useRef(null);
  const displayTimerRef = useRef(null);
  const current = fleetVideoPlaylist[currentIndex] || null;

  const playNext = useCallback(() => {
    setCurrentIndex((index) => fleetVideoPlaylist.length ? (index + 1) % fleetVideoPlaylist.length : 0);
  }, []);

  const sendCommand = useCallback((func, args = []) => {
    iframeRef.current?.contentWindow?.postMessage(
      JSON.stringify({ event: "command", func, args }),
      "*",
    );
  }, []);

  const startSnippet = useCallback(() => {
    if (!current) return;
    window.clearTimeout(failureTimerRef.current);
    window.clearTimeout(displayTimerRef.current);
    sendCommand("mute");
    sendCommand("seekTo", [current.startSeconds, true]);
    sendCommand("getAvailablePlaybackRates");
    sendCommand("playVideo");
    displayTimerRef.current = window.setTimeout(playNext, (current.durationSeconds * 1000) || DISPLAY_DURATION_MS);
    failureTimerRef.current = window.setTimeout(playNext, PLAYBACK_FAILURE_TIMEOUT_MS);
  }, [current, playNext, sendCommand]);

  useEffect(() => {
    if (!current) return undefined;
    failureTimerRef.current = window.setTimeout(playNext, PLAYBACK_FAILURE_TIMEOUT_MS);

    const receiveMessage = (event) => {
      if (!String(event.origin).includes("youtube.com") || event.source !== iframeRef.current?.contentWindow) return;
      try {
        const message = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (message?.event === "onReady") startSnippet();
        if (message?.event === "infoDelivery" && Array.isArray(message.info?.availablePlaybackRates)) {
          const rates = message.info.availablePlaybackRates.filter(Number.isFinite);
          const supportedRate = [REQUESTED_PLAYBACK_RATE, 1.5, 1].find((rate) => rates.includes(rate)) || 1;
          sendCommand("setPlaybackRate", [supportedRate]);
        }
        if (message?.event === "onStateChange" && message.info === 1) window.clearTimeout(failureTimerRef.current);
        if (message?.event === "onStateChange" && message.info === 0) playNext();
      } catch {
        // Ignore unrelated window messages.
      }
    };

    window.addEventListener("message", receiveMessage);
    return () => {
      window.clearTimeout(failureTimerRef.current);
      window.clearTimeout(displayTimerRef.current);
      window.removeEventListener("message", receiveMessage);
    };
  }, [current, playNext, sendCommand, startSnippet]);

  const connectPlayer = () => {
    const player = iframeRef.current?.contentWindow;
    if (!player) return;
    player.postMessage(JSON.stringify({ event: "listening", id: "fleet-showcase-player" }), "*");
    ["onReady", "onStateChange"].forEach((eventName) => {
      player.postMessage(JSON.stringify({ event: "command", func: "addEventListener", args: [eventName] }), "*");
    });
    // Some embeds are already ready before the listener handshake completes.
    window.setTimeout(startSnippet, 600);
  };

  return (
    <section className="showcase-section" aria-labelledby="showcase-title">
      <div className="section-heading">
        <div><p>Visual operations</p><h2 id="showcase-title">Fleet showcase</h2></div>
        <span>Open House Robot Fleet</span>
      </div>
      <div className="showcase-frame">
        {current && (
          <iframe
            ref={iframeRef}
            key={current.robotId}
            src={youtubeEmbedUrl(current.videoId)}
            title={`${current.model} — ${current.application || "Application"}`}
            allow="autoplay; encrypted-media; picture-in-picture"
            onLoad={connectPlayer}
          />
        )}
        <div className="showcase-shade" />
        <div className="showcase-application">{String(currentIndex + 1).padStart(2, "0")} / {fleetVideoPlaylist.length}</div>
        <div className="showcase-copy">
          <strong>{current?.model || "Open House Robot Fleet"}</strong>
          <span>{current?.application || "Application information unavailable"}</span>
        </div>
        <div className="showcase-progress" aria-label={`${currentIndex + 1} of ${fleetVideoPlaylist.length}`}>
          {fleetVideoPlaylist.map((video, index) => <span className={index === currentIndex ? "active" : ""} key={video.robotId} />)}
        </div>
      </div>
    </section>
  );
}

export default FleetShowcaseVideo;
