import type { ResultType } from "@/types/response-types";

export const crmLeadData: ResultType = {
  _meta: {
    ui: {
      resourceUri: "ui://twynity/frappe-dashboard.html",
    },
    toolname: "frappe_list",
  },
  content: [
    {
      type: "text",
      text: "Found 14 CRM Lead records.\nRecord names (use these exact IDs with frappe_get): CRM-LEAD-2026-00001 (Alice Johnson); CRM-LEAD-2026-00002 (Bob Martinez); CRM-LEAD-2026-00003 (Carol Smith); CRM-LEAD-2026-00004 (David Lee); CRM-LEAD-2026-00005 (Emma Williams); CRM-LEAD-2026-00006 (Frank Turner); CRM-LEAD-2026-00007 (Grace Park); CRM-LEAD-2026-00008 (Henry Adams); CRM-LEAD-2026-00009 (Iris Chen); CRM-LEAD-2026-00010 (Jack Morrison); CRM-LEAD-2026-00011 (Karen White); CRM-LEAD-2026-00012 (Leo Brown); CRM-LEAD-2026-00013 (Mr Alfred Amoah); CRM-LEAD-2026-00014 (Master Nana Brown)\nFull record details are displayed on the canvas.",
    },
  ],
  structuredContent: {
    doctype: "CRM Lead",
    records: [
      {
        name: "CRM-LEAD-2026-00001",
        lead_name: "Alice Johnson",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00002",
        lead_name: "Bob Martinez",
        status: "Contacted",
        converted: 0,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00003",
        lead_name: "Carol Smith",
        status: "Nurture",
        converted: 0,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00004",
        lead_name: "David Lee",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00005",
        lead_name: "Emma Williams",
        status: "New",
        converted: 0,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00006",
        lead_name: "Frank Turner",
        status: "Nurture",
        converted: 0,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00007",
        lead_name: "Grace Park",
        status: "Contacted",
        converted: 0,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00008",
        lead_name: "Henry Adams",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00009",
        lead_name: "Iris Chen",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00010",
        lead_name: "Jack Morrison",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00011",
        lead_name: "Karen White",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00012",
        lead_name: "Leo Brown",
        status: "Qualified",
        converted: 1,
        salutation: null,
      },
      {
        name: "CRM-LEAD-2026-00013",
        lead_name: "Mr Alfred Amoah",
        status: "Contacted",
        converted: 0,
        salutation: "Mr",
      },
      {
        name: "CRM-LEAD-2026-00014",
        lead_name: "Master Nana Brown",
        status: "New",
        converted: 0,
        salutation: "Master",
      },
    ],
    columns: [
      {
        label: "Name",
        key: "name",
        type: "Data",
        options: null,
      },
      {
        label: "Full Name",
        key: "lead_name",
        type: "Data",
        options: null,
      },
      {
        label: "Status",
        key: "status",
        type: "Link",
        options: "CRM Lead Status",
      },
      {
        label: "Converted",
        key: "converted",
        type: "Check",
        options: null,
      },
      {
        label: "Salutation",
        key: "salutation",
        type: "Link",
        options: "Salutation",
      },
    ],
  },
  isError: false,
};
