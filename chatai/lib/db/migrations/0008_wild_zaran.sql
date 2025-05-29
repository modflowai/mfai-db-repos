CREATE TABLE IF NOT EXISTS "RateLimit" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"role" varchar NOT NULL,
	"timeWindow" varchar NOT NULL,
	"limitCount" integer NOT NULL
);
--> statement-breakpoint
INSERT INTO "RateLimit" ("role", "timeWindow", "limitCount") VALUES 
	('guest', 'minute', 3),
	('guest', 'daily', 20),
	('regular', 'minute', 5),
	('regular', 'daily', 100),
	('premium', 'minute', 10),
	('premium', 'daily', 1000);
