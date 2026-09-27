// Demo doctors the console can switch between and reset (Checkpoint 11d). Profiles are sent to
// POST /onboard exactly as written; the backend validates them against GET /specialties.
export const PRESET_DOCTORS = [
  {
    id: "dr_patel",
    name: "Dr. Patel",
    specialty: "endocrinology",
    conditions: ["type 2 diabetes", "chronic kidney disease"],
    interests: ["ozempic safety"],
    frequency: "weekly",
  },
  {
    id: "dr_evan",
    name: "Dr. Evan",
    specialty: "dermatology",
    conditions: ["plaque psoriasis", "atopic dermatitis"],
    interests: ["hidradenitis suppurativa"],
    frequency: "weekly",
  },
];

export const OTHER = "other";
