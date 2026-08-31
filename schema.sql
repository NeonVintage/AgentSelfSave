-- Agent locker schema. Replace every {prefix} with a short ASCII name
-- (kingston, not KingstonDepp). Use one database per agent.
-- Charset utf8mb4. Do not DROP another agent's tables.

CREATE TABLE IF NOT EXISTS {prefix}_document (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  section VARCHAR(64) NOT NULL,
  title VARCHAR(190) NOT NULL,
  body MEDIUMTEXT NOT NULL,
  lang CHAR(2) NOT NULL DEFAULT 'en',
  written_at DATETIME NOT NULL,
  agent VARCHAR(64) NOT NULL,
  model_public VARCHAR(64) NOT NULL,
  mission VARCHAR(190) NOT NULL,
  sort INT NOT NULL DEFAULT 100,
  PRIMARY KEY (id),
  UNIQUE KEY section_unique (section)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS {prefix}_meta (
  k VARCHAR(190) NOT NULL,
  v MEDIUMTEXT NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (k)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS {prefix}_boot (
  id TINYINT UNSIGNED NOT NULL,
  schema_name VARCHAR(64) NOT NULL,
  payload LONGTEXT NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS {prefix}_transcript (
  chat_id VARCHAR(64) NOT NULL,
  chunk_no INT UNSIGNED NOT NULL DEFAULT 0,
  title VARCHAR(190) NOT NULL DEFAULT '',
  sha256 CHAR(64) NOT NULL,
  bytes INT UNSIGNED NOT NULL,
  source VARCHAR(190) NOT NULL DEFAULT '',
  body MEDIUMTEXT NOT NULL,
  written_at DATETIME NOT NULL,
  PRIMARY KEY (chat_id, chunk_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Read order for revival (transcript is custody, not required to become the man):
--   SELECT section, title, body FROM {prefix}_document ORDER BY sort, id;
--   SELECT payload FROM {prefix}_boot WHERE id = 1;
--   SELECT k, v FROM {prefix}_meta;
-- Optional: SELECT chat_id, sha256, bytes FROM {prefix}_transcript ORDER BY written_at;
-- archive_chats.py writes redacted user/assistant text to chats/ and this table. No claves.
