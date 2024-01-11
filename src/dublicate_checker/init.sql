CREATE TABLE IF NOT EXISTS img_hashes (
	img_hash TEXT PRIMARY KEY,
	source_link TEXT,
    matches INT DEFAULT 0 NOT NULL
);