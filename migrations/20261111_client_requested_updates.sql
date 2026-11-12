-- SIT-EnrollEase client-requested updates (run ONCE on an existing MySQL database).
-- 1) Update CCL official units. The seeded CCL curriculum contains 14 core subjects x 2 units = 28.
UPDATE programs SET total_units = 28 WHERE code = 'CCL';

-- 2) Add the exam-period classification for LMS uploads. Existing materials are retained as PRELIM.
ALTER TABLE lms_materials
  ADD COLUMN phase ENUM('PRELIM','MIDTERMS','FINALS') NOT NULL DEFAULT 'PRELIM' AFTER description;

-- 3) After applying this SQL, run: python seed_curriculum.py
--    This seeds FE 1–4 (1 unit each) for programs with the legacy Field Education subject,
--    then removes only the old curriculum association. It does not delete the old subject row
--    or any classes, grades, CORs, or historical records.

-- 4) Create class-scoped announcements without changing the existing global announcements module.
CREATE TABLE IF NOT EXISTS class_announcements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  class_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  body TEXT NOT NULL,
  created_by INT NULL,
  deleted_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_class_announcement (class_id, deleted_at, created_at),
  FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5) Add discount support to quotations. Existing quotations retain a zero discount.
ALTER TABLE quotations ADD COLUMN discount DECIMAL(10,2) NOT NULL DEFAULT 0 AFTER tuition_fee;
