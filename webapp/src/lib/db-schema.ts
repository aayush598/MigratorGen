import { pgTable, text, boolean, timestamp, jsonb, index } from "drizzle-orm/pg-core";

export const apiKey = pgTable(
  "api_key",
  {
    id: text("id").primaryKey(),
    userId: text("user_id").notNull(),
    name: text("name").notNull(),
    keyHash: text("key_hash").notNull(),
    keyPrefix: text("key_prefix").notNull(),
    scopes: jsonb("scopes").$type<string[]>().notNull().default([]),
    isActive: boolean("is_active").default(true).notNull(),
    createdAt: timestamp("created_at")
      .defaultNow()
      .notNull(),
  },
  (table) => [index("api_key_userId_idx").on(table.userId)],
);

export const userPacks = pgTable(
  "user_pack",
  {
    id: text("id").primaryKey(),
    userId: text("user_id").notNull(),
    name: text("name").notNull(),
    description: text("description").notNull().default(""),
    library: text("library").notNull(),
    schemaVersion: text("schema_version").notNull().default("1.0"),
    isPublished: boolean("is_published").default(false).notNull(),
    createdAt: text("created_at").notNull(),
    updatedAt: text("updated_at").notNull(),
    versions: jsonb("versions").$type<unknown[]>().notNull().default([]),
  },
  (table) => [index("user_pack_userId_idx").on(table.userId)],
);
