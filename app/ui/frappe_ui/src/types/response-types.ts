export type ResultType = {
  _meta: {
    ui: {
      resourceUri: string;
    };
    toolname: string;
  };
  content: { type: string; text: string }[];
  structuredContent: StructuredContent;
};

export type StructuredContent =
  | CRMDealList
  | FrappeGet
  | FrappeList
  | FrappeCreatePrepare;

export type FrappeFieldType =
  | "Check"
  | "Currency"
  | "Data"
  | "Date"
  | "Datetime"
  | "Duration"
  | "Float"
  | "Link"
  | "Percent"
  | "Select"
  | "Small Text"
  | "Table"
  | "Text";

export type FrappeFormField = {
  fieldname: string;
  label: string;
  fieldtype: FrappeFieldType;
  options: string | null;
  reqd: boolean;
  default: string | null;
  description: string | null;
  depends_on: string | null;
  mandatory_depends_on: string | null;
  precision: string | null;
  child_doctype?: string;
  child_fields?: FrappeFormField[];
};

export type FrappeMissingRequired = {
  fieldname: string;
  label: string;
};

export type FrappeCreatePrepare = {
  mode: "create_form";
  doctype: string;
  fields: FrappeFormField[];
  values: Record<string, unknown>;
  missing_required: FrappeMissingRequired[];
};

export type FrappeGet = {
  doctype: string;
  record: Record<string, unknown>;
};

export type FrappeList = {
  doctype: string;
  records: Record<string, unknown>[];
  columns: FrappeColumn[];
};

export type FrappeColumn = {
  label: string;
  key: string;
  type: string;
  options: string | null;
};

export type CRMDealList = {
  doctype: "CRM Deal";
  records: CRMDealRecord[];
  columns: CRMDealColumn[];
};

type CRMDealRecord = {
  naming_series: "CRM-DEAL-.YYYY.-";
  organization: string;
  next_step: string | null;
  status: string;
  deal_owner: string;
  custom_service_line:
    | "Product"
    | "Dev as a Service"
    | "Consulting"
    | "Sourcing";
  probability: number;
  expected_deal_value: number;
  deal_value: number;
  custom_budget_confirmed: 0 | 1;
  custom_economic_buyer_identified: 0 | 1;
  custom_timeline_confirmed: 0 | 1;
  custom_decision_process_understood: 0 | 1;
  custom_technical_fit_confirmed: 0 | 1;
  custom_commercial_fit_confirmed: 0 | 1;
  custom_opportunity_type: "New Business" | "Expansion" | "Renewal" | null;
  custom_primary_competitor: string | null;
  custom_competition_notes: string | null;
  custom_customer_pain__need: string | null;
  custom_proposed_solution: string | null;
  custom_delivery_capacity_confirmed: 0 | 1;
  custom_capacity_confirmed_at: string | null;
  custom_capacity_confirmed_by: string | null;
  custom_contract_signed: 0 | 1;
  custom_metrics: string | null;
  custom_decision_criteria: string | null;
  custom_paper_process: string | null;
  custom_champion: string | null;
  expected_closure_date: string | null;
  closed_date: string | null;
  contact: string | null;
  lead: string;
  source: string;
  lead_name: string;
  organization_name: string | null;
  website: string;
  no_of_employees:
    | "1-10"
    | "11-50"
    | "51-200"
    | "201-500"
    | "501-1000"
    | "1000+";
  job_title: string;
  territory: string | null;
  currency: string;
  exchange_rate: number;
  annual_revenue: number;
  industry: string;
  salutation: string | null;
  first_name: string;
  last_name: string;
  email: string;
  mobile_no: string;
  phone: string;
  gender: string | null;
  total: number;
  net_total: number;
  sla: string | null;
  sla_creation: string | null;
  sla_status:
    | ""
    | "First Response Due"
    | "Rolling Response Due"
    | "Failed"
    | "Fulfilled";
  communication_status: string;
  response_by: string | null;
  first_response_time: number | null;
  first_responded_on: string | null;
  last_response_time: number | null;
  last_responded_on: string | null;
  lost_reason: string | null;
  lost_notes: string | null;
  name: string;
  owner: string;
  creation: string;
  modified: string;
};

type CRMDealColumn = {
  label: string;
  key: keyof CRMDealRecord;
  type:
    | "Select"
    | "Link"
    | "Data"
    | "Percent"
    | "Currency"
    | "Check"
    | "Small Text"
    | "Datetime"
    | "Date"
    | "Float"
    | "Text"
    | "Duration";
  options: string | null;
};
