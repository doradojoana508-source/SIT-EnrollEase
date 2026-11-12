-- University-wide resources for student portal. Run once on an existing database.
CREATE TABLE IF NOT EXISTS university_resources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(150) NOT NULL,
  category VARCHAR(60) NOT NULL DEFAULT 'General',
  description VARCHAR(500) NULL,
  kind ENUM('File','Link') NOT NULL DEFAULT 'File',
  original_name VARCHAR(150) NULL,
  stored_name VARCHAR(80) NULL,
  mime_type VARCHAR(100) NULL,
  size_bytes INT UNSIGNED NULL,
  link_url VARCHAR(500) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  uploaded_by INT NULL,
  deleted_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_university_resource (is_active, deleted_at, category),
  FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
