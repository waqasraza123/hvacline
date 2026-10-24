import { describe, expect, it } from "vitest";

import type { ReceptionistSettingsDraft } from "./contracts";
import { categoriesFromDraft, validateSettingsDraft } from "./settings-form";

const VALID_DRAFT: ReceptionistSettingsDraft = {
  publicName: "Harborline Heating & Air",
  greeting: "Welcome to our synthetic receptionist.",
  officeHours: "Monday through Friday, 9 AM to 5 PM Eastern",
  contactEmail: "receptionist@example.com",
  contactPhone: "",
  supportedServiceCategories: "Auto\nHomeowners",
  escalationMessage: "A service team member will follow up.",
};

describe("receptionist settings form", () => {
  it("normalizes newline-delimited HVAC services", () => {
    expect(categoriesFromDraft(" Auto \n\nHomeowners\nRenters ")).toEqual([
      "Auto",
      "Homeowners",
      "Renters",
    ]);
  });

  it("requires a contact method and unique categories", () => {
    expect(
      validateSettingsDraft({
        ...VALID_DRAFT,
        contactEmail: "",
        contactPhone: "",
      }),
    ).toBe("Add a public email address or phone number.");
    expect(
      validateSettingsDraft({
        ...VALID_DRAFT,
        supportedServiceCategories: "Auto\nauto",
      }),
    ).toBe("Supported HVAC services must be unique.");
  });

  it("accepts a complete receptionist configuration", () => {
    expect(validateSettingsDraft(VALID_DRAFT)).toBeUndefined();
  });
});
