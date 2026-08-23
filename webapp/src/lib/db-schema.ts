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
