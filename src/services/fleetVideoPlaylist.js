import { robotRegistry } from "../data/robotRegistry.js";

export const FANUC_VIDEO_IDS = Object.freeze({
  collaborativeRobot: "dhPMY6B3RKE",
  crx: "5xisd9D2IVo",
  collaborativeAssembly: "UUJOLrxpxhI",
  spotWelding: "oK-CkU9y23I",
  automotiveSpotWelding: "LWg7EV06p5c",
  arcWelding: "pP5pDqmMOqk",
  coordinatedWelding: "lY_i77wRdM8",
  handlingAssembly: "5qCJ1anwAbg",
  handlingApplication: "s--aXsLnLXg",
  crankshaftBinPicking: "dzRr6UMcgQg",
  visionPartsAlignment: "vxZh4I-uSHI",
  lrMateVisualTracking: "QpEPjVXTzRw",
  lrMateBinPicking: "rz0XOOpkjLM",
  lrMateBottleVision: "XgFqwUfsNfA",
  highSpeedLabeling: "9Fly6yeBZBc",
  r2000Palletizing: "HCWBkK54zFw",
  m410Palletizing: "Vywviafx9L8",
  softGripper: "bP8bs_a3U3c",
  paintingRobot: "SKg3pMBUEhk",
  paintingApplication: "orruzcYcNi0",
});

function selectVideo(robot) {
  const application = String(robot.application || "").toLowerCase();
  const model = String(robot.model || "").toLowerCase();
  const combined = `${application} ${model}`;

  if (application.includes("automotive") && application.includes("spot")) return FANUC_VIDEO_IDS.automotiveSpotWelding;
  if (application.includes("spot weld")) return FANUC_VIDEO_IDS.spotWelding;
  if (application.includes("fixtureless") || application.includes("coordinated")) return FANUC_VIDEO_IDS.coordinatedWelding;
  if (/weld|arc|cladding/.test(combined)) return FANUC_VIDEO_IDS.arcWelding;

  if (/pallet|palletizing/.test(application)) {
    return model.includes("m-410") ? FANUC_VIDEO_IDS.m410Palletizing : FANUC_VIDEO_IDS.r2000Palletizing;
  }

  if (application.includes("paint")) return model.includes("crx") ? FANUC_VIDEO_IDS.paintingApplication : FANUC_VIDEO_IDS.paintingRobot;
  if (/bin pick|bin picking|picking/.test(application)) return model.includes("lr-mate") ? FANUC_VIDEO_IDS.lrMateBinPicking : FANUC_VIDEO_IDS.crankshaftBinPicking;
  if (application.includes("bottle") && application.includes("vision")) return FANUC_VIDEO_IDS.lrMateBottleVision;
  if (/vision|inspection|error proof|rtvt/.test(application)) return model.includes("lr-mate") ? FANUC_VIDEO_IDS.lrMateVisualTracking : FANUC_VIDEO_IDS.visionPartsAlignment;
  if (application.includes("gripper")) return FANUC_VIDEO_IDS.softGripper;
  if (application.includes("label")) return FANUC_VIDEO_IDS.highSpeedLabeling;

  if (/assembly|order fulfilment|nut tightening/.test(application)) {
    return model.includes("crx") ? FANUC_VIDEO_IDS.collaborativeAssembly : FANUC_VIDEO_IDS.handlingAssembly;
  }

  if (/crx|collaborative/.test(combined)) return FANUC_VIDEO_IDS.crx;
  if (model.includes("lr-mate")) return FANUC_VIDEO_IDS.lrMateVisualTracking;
  if (/material handling|handling|machine tending/.test(application)) return FANUC_VIDEO_IDS.handlingApplication;

  return FANUC_VIDEO_IDS.handlingApplication;
}

function isFallback(robot, videoId) {
  const text = `${robot.application || ""} ${robot.model || ""}`.toLowerCase();
  return videoId === FANUC_VIDEO_IDS.handlingApplication && !/material handling|handling|machine tending/.test(text);
}

// Curated action windows begin after the source videos' opening graphics.
const ACTION_SEGMENTS = Object.freeze({
  [FANUC_VIDEO_IDS.collaborativeRobot]: [18, 7], [FANUC_VIDEO_IDS.crx]: [14, 7],
  [FANUC_VIDEO_IDS.collaborativeAssembly]: [20, 7], [FANUC_VIDEO_IDS.spotWelding]: [16, 7],
  [FANUC_VIDEO_IDS.automotiveSpotWelding]: [22, 7], [FANUC_VIDEO_IDS.arcWelding]: [17, 7],
  [FANUC_VIDEO_IDS.coordinatedWelding]: [24, 7], [FANUC_VIDEO_IDS.handlingAssembly]: [15, 7],
  [FANUC_VIDEO_IDS.handlingApplication]: [19, 7], [FANUC_VIDEO_IDS.crankshaftBinPicking]: [21, 7],
  [FANUC_VIDEO_IDS.visionPartsAlignment]: [18, 7], [FANUC_VIDEO_IDS.lrMateVisualTracking]: [16, 7],
  [FANUC_VIDEO_IDS.lrMateBinPicking]: [20, 7], [FANUC_VIDEO_IDS.lrMateBottleVision]: [14, 7],
  [FANUC_VIDEO_IDS.highSpeedLabeling]: [17, 7], [FANUC_VIDEO_IDS.r2000Palletizing]: [23, 7],
  [FANUC_VIDEO_IDS.m410Palletizing]: [21, 7], [FANUC_VIDEO_IDS.softGripper]: [15, 7],
  [FANUC_VIDEO_IDS.paintingRobot]: [19, 7], [FANUC_VIDEO_IDS.paintingApplication]: [18, 7],
});

export const fleetVideoPlaylist = Object.freeze(
  robotRegistry.map((robot) => {
    const videoId = selectVideo(robot);
    const [startSeconds, durationSeconds] = ACTION_SEGMENTS[videoId] || [18, 7];
    return Object.freeze({
      robotId: robot.id,
      serialNo: robot.serialNo,
      model: robot.model,
      application: robot.application,
      videoId,
      source: "FANUC_OFFICIAL_YOUTUBE",
      startSeconds,
      durationSeconds,
      fallback: isFallback(robot, videoId),
    });
  }),
);
