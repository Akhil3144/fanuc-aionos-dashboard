const familyImage = Object.freeze({
  CRX: "/robot-images/crx-family.svg",
  "LR-MATE": "/robot-images/lr-mate-family.svg",
  "ARC-MATE": "/robot-images/arc-mate-family.svg",
  "R-2000": "/robot-images/r-2000-family.svg",
  DEFAULT: "/robot-images/industrial-family.svg",
});

export function robotFamily(model = "") {
  const value = model.toUpperCase();
  if (value.includes("CRX")) return "CRX";
  if (value.includes("LR-MATE") || value.includes("LR MATE")) return "LR-MATE";
  if (value.includes("ARC MATE")) return "ARC-MATE";
  if (value.includes("R-2000")) return "R-2000";
  return "DEFAULT";
}

export function imageForRobot(robot) {
  const family = robotFamily(robot?.model);
  return { src: familyImage[family], fallback: familyImage.DEFAULT, family, isPlaceholder: true };
}
