import { z } from "zod";

export const migrationFormSchema = z.object({
  sourceCode: z.string().min(1, "Source code is required"),
  library: z.string().min(1, "Select a library"),
  sourceVersion: z.string().optional(),
  targetVersion: z.string().optional(),
});
export type MigrationFormInput = z.infer<typeof migrationFormSchema>;

export const packDetailsSchema = z.object({
  name: z.string().min(3, "Pack name must be at least 3 characters").max(100),
  description: z.string().max(500, "Description too long").optional().or(z.literal("")),
  library: z
    .string()
    .min(2, "Library slug required")
    .regex(/^[a-z0-9][a-z0-9._-]*$/i, "Use letters, numbers, dots, dashes or underscores"),
});
export type PackDetailsInput = z.infer<typeof packDetailsSchema>;

export const versionDraftSchema = z.object({
  version: z
    .string()
    .min(1, "Version required")
    .regex(/^\d+\.\d+(\.\d+)?$/, "Use semver format e.g. 1.0.0"),
  release_date: z.string().optional().or(z.literal("")),
  notes: z.string().optional().or(z.literal("")),
});
export type VersionDraftInput = z.infer<typeof versionDraftSchema>;

export const ruleDraftSchema = z.object({
  id: z.string().optional().or(z.literal("")),
  change_type: z.string().min(1, "Change type required"),
  description: z.string().min(3, "Describe the change"),
  old_name: z.string().optional().or(z.literal("")),
  new_name: z.string().optional().or(z.literal("")),
  function_name: z.string().optional().or(z.literal("")),
  argument_name: z.string().optional().or(z.literal("")),
  new_argument_name: z.string().optional().or(z.literal("")),
  replacement: z.string().optional().or(z.literal("")),
  safety: z.enum(["safe", "review_required", "risky"]).default("safe"),
  confidence_hint: z.enum(["high", "medium", "low"]).default("high"),
  tags: z.array(z.string()).default([]),
});
export type RuleDraftInput = z.infer<typeof ruleDraftSchema>;

export const apiKeyCreateSchema = z.object({
  name: z.string().min(3, "Key name must be at least 3 characters").max(60),
  scopes: z.array(z.string()).min(1, "Pick at least one scope"),
});
export type ApiKeyCreateInput = z.infer<typeof apiKeyCreateSchema>;

export const CHANGE_TYPES = [
  "rename_function",
  "rename_class",
  "rename_attribute",
  "rename_import",
  "add_argument",
  "remove_argument",
  "change_argument_default",
  "reorder_arguments",
  "deprecate_function",
  "remove_function",
  "remove_class",
  "change_return_type",
  "replace_with_property",
  "move_to_module",
  "wrap_in_context_manager",
  "add_decorator",
  "remove_decorator",
  "rename_argument",
  "sync_to_async",
  "class_split",
  "module_split",
  "enum_migration",
  "dataclass_field_change",
] as const;

// ─── API Response Schemas ─────────────────────────────────────────────────────

export const SafetyLevelSchema = z.enum(["safe", "review_required", "risky"]);
export type SafetyLevel = z.infer<typeof SafetyLevelSchema>;

const RuleWhenConditionSchema = z.object({
  target_version: z.string().optional(),
  min_python: z.string().optional(),
  requires_import: z.string().optional(),
});

export const RuleSchema = z.object({
  id: z.string(),
  change_type: z.enum([
    "rename_function", "rename_class", "rename_attribute", "rename_import",
    "add_argument", "remove_argument", "change_argument_default", "reorder_arguments",
    "deprecate_function", "remove_function", "remove_class", "change_return_type",
    "replace_with_property", "move_to_module", "wrap_in_context_manager", "add_decorator",
    "remove_decorator", "rename_argument", "sync_to_async", "class_split",
    "module_split", "enum_migration", "dataclass_field_change",
  ]),
  version_introduced: z.string().default(""),
  description: z.string().default(""),
  old_name: z.string().nullish(),
  new_name: z.string().nullish(),
  old_module: z.string().nullish(),
  new_module: z.string().nullish(),
  source_module: z.string().nullish(),
  target_module: z.string().nullish(),
  function_name: z.string().nullish(),
  class_name: z.string().nullish(),
  argument_name: z.string().nullish(),
  new_argument_name: z.string().nullish(),
  default_value: z.string().nullish(),
  replacement: z.string().nullish(),
  position: z.number().nullish(),
  safety: SafetyLevelSchema.default("safe"),
  confidence_hint: z.string().default("high"),
  reversible: z.boolean().default(true),
  tags: z.array(z.string()).default([]),
  when: RuleWhenConditionSchema.nullish(),
  extra: z.record(z.string(), z.unknown()).nullish(),
}).passthrough();
export type Rule = z.infer<typeof RuleSchema>;

export const VersionChangelogSchema = z.object({
  version: z.string(),
  release_date: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
  rules: z.array(RuleSchema).default([]),
});
export type VersionChangelog = z.infer<typeof VersionChangelogSchema>;

export const MigrationFileSchema = z.object({
  library: z.string(),
  description: z.string().default(""),
  schema_version: z.string().default("1.0"),
  versions: z.array(VersionChangelogSchema).default([]),
});
export type MigrationFile = z.infer<typeof MigrationFileSchema>;

export const MigrateResponseSchema = z.object({
  original_code: z.string().default(""),
  transformed_code: z.string().default(""),
  changes: z.array(z.string()).default([]),
  rules_applied: z.array(z.string()).default([]),
  average_confidence: z.number().default(0),
  was_modified: z.boolean().default(false),
  errors: z.array(z.string()).default([]),
});
export type MigrateResponse = z.infer<typeof MigrateResponseSchema>;

export const DiffPreviewSchema = z.object({
  original_code: z.string().default(""),
  transformed_code: z.string().default(""),
  diff: z.string().default(""),
  changes: z.array(z.string()).default([]),
  change_count: z.number().default(0),
  average_confidence: z.number().default(0),
});
export type DiffPreview = z.infer<typeof DiffPreviewSchema>;

export const ValidationIssueSchema = z.object({ rule_id: z.string(), message: z.string() });
export type ValidationIssue = z.infer<typeof ValidationIssueSchema>;

export const ValidationReportSchema = z.object({
  valid: z.boolean(),
  error_count: z.number().default(0),
  warning_count: z.number().default(0),
  info_count: z.number().default(0),
  errors: z.array(ValidationIssueSchema).default([]),
  warnings: z.array(ValidationIssueSchema).default([]),
  info: z.array(ValidationIssueSchema).default([]),
});
export type ValidationReport = z.infer<typeof ValidationReportSchema>;

const ResolvedPathStepSchema = z.object({ source: z.string(), target: z.string(), rules: z.number().default(0) });

export const ResolvedPathSchema = z.object({
  source_version: z.string(),
  target_version: z.string(),
  is_upgrade: z.boolean().default(true),
  steps: z.array(ResolvedPathStepSchema).default([]),
  rule_count: z.number().default(0),
});
export type ResolvedPath = z.infer<typeof ResolvedPathSchema>;

export const LibraryInfoSchema = z.object({
  name: z.string(),
  rule_count: z.number().default(0),
  source: z.string().default("builtin"),
  description: z.string().optional(),
  versions: z.array(VersionChangelogSchema).optional(),
});
export type LibraryInfo = z.infer<typeof LibraryInfoSchema>;

export const ApiKeySchema = z.object({
  id: z.string(),
  name: z.string(),
  key: z.string().nullish(),
  key_prefix: z.string(),
  scopes: z.array(z.string()).default([]),
  created_at: z.string(),
  is_active: z.boolean().default(true),
});
export type ApiKey = z.infer<typeof ApiKeySchema>;

export const UserPackSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().default(""),
  library: z.string(),
  version_count: z.number().default(0),
  rule_count: z.number().default(0),
  is_published: z.boolean().default(false),
  created_at: z.string().default(""),
  updated_at: z.string().default(""),
});
export type UserPackSummary = z.infer<typeof UserPackSummarySchema>;

export const UserPackDetailSchema = UserPackSummarySchema.extend({
  versions: z.array(VersionChangelogSchema).default([]),
});
export type UserPackDetail = z.infer<typeof UserPackDetailSchema>;

export const HealthStatusSchema = z.object({
  status: z.string(),
  version: z.string(),
  timestamp: z.string(),
});
export type HealthStatus = z.infer<typeof HealthStatusSchema>;
