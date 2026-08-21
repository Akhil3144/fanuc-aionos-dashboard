import "./RobotVideo.css";

const videos = {
  "EXH-R01": "/videos/robot-r01.mp4",
  "EXH-R02": "/videos/robot-r02.mp4",
  "EXH-R03": "/videos/robot-r03.mp4",
};

export default function RobotVideo({ robotId, robot }) {
  const src = videos[robotId];

  if (!src) return null;

  return (
    <section className="robot-video-section">
      <div className="robot-video-title">
        <div>
          <span>ROBOT VISUAL</span>
          <h2>
            {robot?.display_name ||
              robot?.robot_name ||
              robotId}
          </h2>
        </div>

        <strong>ROBOT VIDEO</strong>
      </div>

      <div className="robot-video-wrapper">
        <video
          key={robotId}
          src={src}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          className="robot-demo-video"
        />

        <div className="robot-video-label">
          <strong>{robotId}</strong>
          <span>{robot?.role || "Exhibition Robot"}</span>
        </div>
      </div>
    </section>
  );
}
