const definition = (index, label, group, unit = null) => Object.freeze({ index, label, group, unit, currentValue: null, valueSource: "UNAVAILABLE" });

const weldingRegisters = (start) => Object.freeze([
  definition(start, "Total Number of Spots", "Production Data"), definition(start + 1, "Completed Spots", "Production Data"),
  definition(start + 2, "Remaining Spots", "Production Data"), definition(start + 3, "Cycle Time", "Production Data", start === 21 ? "sec" : null),
  definition(start + 4, "Time Taken for Last Spot", "Production Data"), definition(start + 5, "Average Time per Spot", "Production Data"),
  definition(start + 6, "Total Cycle Time", "Production Data"), definition(start + 7, "Material Thickness – Actual", "Weld Quality"),
  definition(start + 8, "Material Thickness – Target", "Weld Quality"), definition(start + 9, "Thickness Tolerance", "Weld Quality"),
  definition(start + 10, "Electrode Life / Remaining Life", "Electrode & Tip Dress", "%"), definition(start + 11, "Number of Welds Since Tip Dress", "Electrode & Tip Dress"),
  definition(start + 12, "Tip-Dress Count", "Electrode & Tip Dress"), definition(start + 13, "Next Tip-Dress Due", "Electrode & Tip Dress"),
  definition(start + 14, "Electrode Wear Status", "Electrode & Tip Dress"), definition(start + 15, "Electrode Change Required", "Electrode & Tip Dress"),
  definition(start + 16, "Tip-Dress Status", "Electrode & Tip Dress"),
]);

export const registerDefinitions = Object.freeze({
  AI_ERROR_PROOFING: Object.freeze({
    key: "AI_ERROR_PROOFING", cellName: "AI Error Proofing", model: "LR Mate/7-9D", sourceSheet: "AI Error Proofing",
    registers: Object.freeze([
      definition(11, "No. of components", "Production Data"), definition(12, "Cycle Time", "Production Data", "seconds"),
      definition(13, "Total no. of cycles run", "Production Data"), definition(14, "Robot speed", "Production Data", "%"),
      definition(15, "Total no. of snaps taken", "AI Inspection"), definition(16, "Total no. of parameters inspected / cycle", "AI Inspection"),
      definition(17, "Total no. of parameters inspected / hour", "AI Inspection"), definition(19, "No. of OK parameters", "Quality"),
      definition(20, "No. of NG parameters", "Quality"), definition(21, "Inspection status", "Quality"),
    ]),
  }),
  FLEXIBLE_SPOT_WELDING_R2000IC_210F: Object.freeze({
    key: "FLEXIBLE_SPOT_WELDING_R2000IC_210F", cellName: "Flexible Spot Welding System", model: "R-2000iC/210F", sourceSheet: "Flexible spot welding", registers: weldingRegisters(21),
  }),
  FLEXIBLE_SPOT_WELDING_R2000_210F_31E: Object.freeze({
    key: "FLEXIBLE_SPOT_WELDING_R2000_210F_31E", cellName: "Flexible Spot Welding System", model: "R-2000/210F-31E", sourceSheet: "Flexible spot welding", registers: weldingRegisters(51),
  }),
});

export function registerDefinitionForRobot(robot) {
  return registerDefinitions[robot?.registerSchemaKey] || null;
}
