export type ReceptionistSettings = Readonly<{
  id: string;
  agencyId: string;
  publicName: string;
  greeting: string;
  officeHours: string;
  contactEmail: string | null;
  contactPhone: string | null;
  supportedServiceCategories: readonly string[];
  escalationMessage: string;
  rowVersion: number;
  createdAt: string;
  updatedAt: string;
}>;

export type ReceptionistSettingsDraft = Readonly<{
  publicName: string;
  greeting: string;
  officeHours: string;
  contactEmail: string;
  contactPhone: string;
  supportedServiceCategories: string;
  escalationMessage: string;
}>;
