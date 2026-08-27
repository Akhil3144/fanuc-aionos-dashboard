const CLIENT_IMAGE_ROOT = "/robot-images/client";

const modelImages = Object.freeze({
  "R-2000IC/270F": "R2000iC_270F.avif",
  "R-2000IC/210F": "r-2000ic-210f.jpg",
  "SR-6IA": "SR-6iA-Beauty-Shot.png",
  "SR-20IA": "sr-20ia.png",
  "R-2000IC/165F": "r-2000ic-165f.avif",
  "ARC MATE 100ID/8L": "arc-mate-100id-8l.png",
  "ARC MATE 120ID": "arc-mate-120id.png",
  "ARC MATE 120ID/12L": "arc-mate-120id-12l.png",
  "CRX-3IA": "CRX-3iA-Beauty-Shot.avif",
  "CRX-5IA": "CRX-5iA-cobot.png",
  "CRX-10IA": "CRX-10iA-Beauty-Shot.png",
  "CRX-10IA/L": "crx-10ial-cobot.avif",
  "CRX-20IA/L": "crx-20ia-l.png",
  "CRX-30IA": "crx-30ia.avif",
  "LR MATE 200ID/4S": "lr-mate-200id-4s.png",
  "LR MATE 200ID/7L": "lr-mate-200id-7l.png",
  "M-2IA/3SL": "m-2ia-3sl.avif",
  "M-20ID/25": "m-20id-25.png",
  "M-20ID/35": "m-20id-35.png",
  "M-410IC/185": "m-410ic-185.png",
  "M-900IB/360": "m-900ib-360.png",
  "P-50IB/10L": "p-50ib-10l.png",
});

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
  if (value.includes("LR MATE") || value.includes("LR-MATE")) return "LR-MATE";
  if (value.includes("ARC MATE")) return "ARC-MATE";
  if (value.includes("R-2000")) return "R-2000";
  return "DEFAULT";
}

export function imageForRobot(robot) {
  const model = String(robot?.model || "").trim().toUpperCase();
  const image = modelImages[model];
  const family = robotFamily(model);
  return image
    ? { src: `${CLIENT_IMAGE_ROOT}/${encodeURIComponent(image)}`, fallback: familyImage[family], family, isPlaceholder: false }
    : { src: familyImage[family], fallback: familyImage.DEFAULT, family, isPlaceholder: true };
}
