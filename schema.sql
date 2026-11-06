-- SIT-EnrollEase schema, Part 1: Foundation
-- Patakbuhin sa phpMyAdmin (database: sit_enrollease)

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE,
  username VARCHAR(30) NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin','registrar','finance','faculty','student','applicant') NOT NULL DEFAULT 'applicant',
  first_name VARCHAR(50) NOT NULL,
  middle_name VARCHAR(50) NULL,
  last_name VARCHAR(50) NOT NULL,
  photo VARCHAR(255) NULL,
  is_verified TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  is_activated TINYINT(1) NOT NULL DEFAULT 1,
  failed_attempts INT NOT NULL DEFAULT 0,
  locked_until DATETIME NULL,
  session_version INT NOT NULL DEFAULT 0,
  last_login DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS settings (
  setting_key VARCHAR(60) PRIMARY KEY,
  setting_value VARCHAR(255) NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS academic_terms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  term_no TINYINT NOT NULL,
  academic_year VARCHAR(9) NOT NULL,
  start_date DATE NULL,
  end_date DATE NULL,
  admission_status ENUM('Draft','Open','Closed','Archived') NOT NULL DEFAULT 'Draft',
  admission_open DATE NULL,
  admission_close DATE NULL,
  is_current TINYINT(1) NOT NULL DEFAULT 0,
  UNIQUE KEY uq_term (term_no, academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS programs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(10) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  level ENUM('Certificate','Diploma','Bachelor','Master') NOT NULL,
  total_units SMALLINT NOT NULL,
  objective TEXT NULL,
  prerequisites TEXT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subjects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(15) NOT NULL UNIQUE,
  title VARCHAR(120) NOT NULL,
  units TINYINT NOT NULL,
  prerequisite VARCHAR(120) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS curriculum (
  id INT AUTO_INCREMENT PRIMARY KEY,
  program_id INT NOT NULL,
  subject_id INT NOT NULL,
   seq SMALLINT NOT NULL DEFAULT 0,
  grp ENUM('Core','Elective','Thesis','Project') NOT NULL DEFAULT 'Core',
  title VARCHAR(120) NOT NULL DEFAULT '',
  units TINYINT NOT NULL DEFAULT 0,
  year_level TINYINT NULL,
  term_no TINYINT NULL,
  UNIQUE KEY uq_program_subject (program_id, subject_id),
  FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS document_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  description VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS program_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  program_id INT NOT NULL,
  document_type_id INT NOT NULL,
  applicant_type ENUM('New','Transferee','Returnee') NOT NULL DEFAULT 'New',
  UNIQUE KEY uq_program_doc (program_id, document_type_id, applicant_type),
  FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE,
  FOREIGN KEY (document_type_id) REFERENCES document_types(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  action VARCHAR(80) NOT NULL,
  details VARCHAR(255) NULL,
  ip_address VARCHAR(45) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_created (created_at),
  INDEX idx_audit_user (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  term_id INT NULL,
  program_id INT NULL,
  applicant_type VARCHAR(20) NOT NULL DEFAULT 'New',
  status VARCHAR(30) NOT NULL DEFAULT 'Draft',
  address VARCHAR(255) NULL,
  home_tel VARCHAR(20) NULL,
  phone VARCHAR(20) NULL,
  father_name VARCHAR(120) NULL,
  father_mobile VARCHAR(20) NULL,
  mother_name VARCHAR(120) NULL,
  mother_mobile VARCHAR(20) NULL,
  birthdate DATE NULL,
  birthplace VARCHAR(120) NULL,
  gender VARCHAR(10) NULL,
  civil_status VARCHAR(20) NULL,
  nationality VARCHAR(60) NULL,
  school_name VARCHAR(150) NULL,
  school_place VARCHAR(150) NULL,
  year_graduated SMALLINT NULL,
  job_position VARCHAR(100) NULL,
  employer VARCHAR(150) NULL,
  church_name VARCHAR(150) NULL,
  church_address VARCHAR(255) NULL,
  pastor_name VARCHAR(120) NULL,
  responsibility VARCHAR(150) NULL,
  ministry VARCHAR(150) NULL,
  remarks TEXT NULL,
  certified_name VARCHAR(120) NULL,
  certified_at DATETIME NULL,
  submitted_at DATETIME NULL,
  originals_received_at DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_app_status (status),
  INDEX idx_app_program (program_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
  UNIQUE KEY uq_app_user_term (user_id, term_id),
) ENGINE=InnoDB;

ALTER TABLE applications ADD CONSTRAINT fk_app_program FOREIGN KEY (program_id) REFERENCES programs(id);
ALTER TABLE applications ADD CONSTRAINT fk_app_term FOREIGN KEY (term_id) REFERENCES academic_terms(id);

CREATE TABLE IF NOT EXISTS application_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL,
  document_type_id INT NOT NULL,
  stored_name VARCHAR(80) NOT NULL,
  original_name VARCHAR(150) NOT NULL,
  mime_type VARCHAR(60) NOT NULL,
  size_bytes INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Uploaded',
  remarks VARCHAR(255) NULL,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_app_doc (application_id, document_type_id),
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS interviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL,
  interviewer VARCHAR(40) NOT NULL,
  scheduled_at DATETIME NOT NULL,
  venue VARCHAR(150) NOT NULL,
  notes VARCHAR(255) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',
  created_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_interview_app (application_id),
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  message VARCHAR(500) NOT NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notice_user (user_id, is_read),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS enrollments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  term_id INT NOT NULL,
  student_type ENUM('New','Transferee','Continuing','Returnee') NOT NULL,
  status ENUM('Pre-enrolled','Quoted','Enrolled') NOT NULL DEFAULT 'Pre-enrolled',
  enrolled_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_enrollment (user_id, term_id),
  INDEX idx_enroll_term (term_id, status),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (term_id) REFERENCES academic_terms(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS quotations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL UNIQUE,
  student_id VARCHAR(10) NOT NULL,
  account_no VARCHAR(20) NOT NULL UNIQUE,
  units DECIMAL(4,1) NOT NULL,
  tuition_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
  energy_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
  book_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
  printouts_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
  admission_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
  total DECIMAL(10,2) NOT NULL,
  paid_at DATETIME NULL,
  created_by INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE quotations ADD COLUMN paid_at DATETIME NULL AFTER total;
ALTER TABLE quotations ADD COLUMN archived_at DATETIME NULL AFTER paid_at;

CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  quotation_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  receipt_no VARCHAR(20) NOT NULL UNIQUE,
  paid_on DATE NOT NULL,
  note VARCHAR(120) NULL,
  recorded_by INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  voided_at DATETIME NULL,
  voided_by INT NULL,
  INDEX idx_pay_quotation (quotation_id),
  FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
  FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (voided_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS faculty_profiles (
  user_id INT PRIMARY KEY,
  title VARCHAR(10) NOT NULL DEFAULT '',
  display_name VARCHAR(40) NULL,
  specialties VARCHAR(255) NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS classes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  term_id INT NOT NULL,
  subject_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  units TINYINT NOT NULL,
  section VARCHAR(10) NOT NULL DEFAULT 'A',
  day_code ENUM('M','T','W','TH','F','S') NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  faculty_id INT NULL,
  status ENUM('Tentative','Final') NOT NULL DEFAULT 'Tentative',
  created_by INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_class (term_id, subject_id, title, section),
  INDEX idx_class_faculty (faculty_id, term_id),
  FOREIGN KEY (term_id) REFERENCES academic_terms(id),
  FOREIGN KEY (subject_id) REFERENCES subjects(id),
  FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  term_id INT NOT NULL,
  program_id INT NOT NULL,
  year_level VARCHAR(4) NOT NULL DEFAULT '1st',
  scholarship VARCHAR(80) NULL,
  date_enrolled DATE NULL,
  status ENUM('Tentative','Final') NOT NULL DEFAULT 'Tentative',
  created_by INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cor (user_id, term_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (term_id) REFERENCES academic_terms(id),
  FOREIGN KEY (program_id) REFERENCES programs(id),
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cor_subjects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cor_id INT NOT NULL,
  class_id INT NOT NULL,
  UNIQUE KEY uq_cor_class (cor_id, class_id),
  FOREIGN KEY (cor_id) REFERENCES cors(id) ON DELETE CASCADE,
  FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  class_id INT NULL,
  term_no TINYINT NOT NULL,
  academic_year VARCHAR(9) NOT NULL,
  code VARCHAR(20) NOT NULL,
  title VARCHAR(120) NOT NULL,
  units TINYINT NOT NULL,
  grade VARCHAR(4) NOT NULL,
  removal_rating VARCHAR(4) NULL,
  updated_by INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_grade_class (user_id, class_id),
  UNIQUE KEY uq_grade_subject (user_id, academic_year, term_no, code),
  KEY idx_grade_user (user_id, academic_year, term_no),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL,
  FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tor_info (
  user_id INT PRIMARY KEY,
  last_attended VARCHAR(120) NULL,
  category VARCHAR(120) NULL,
  school VARCHAR(120) NULL,
  degree VARCHAR(120) NULL,
  major VARCHAR(120) NULL,
  admitted VARCHAR(120) NULL,
  conferred VARCHAR(120) NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  class_id INT NOT NULL,
  user_id INT NOT NULL,
  meeting_date DATE NOT NULL,
  status ENUM('P','A','E','L') NOT NULL,
  recorded_by INT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_att (class_id, user_id, meeting_date),
  KEY idx_att_user (user_id),
  FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS announcements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(150) NOT NULL,
  body TEXT NOT NULL,
  audience ENUM('everyone','applicant','student','faculty','registrar','finance') NOT NULL DEFAULT 'everyone',
  is_pinned TINYINT(1) NOT NULL DEFAULT 0,
  publish_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NULL,
  created_by INT NULL,
  deleted_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ann_audience (audience, deleted_at, publish_at),
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS landing_content (
  content_key VARCHAR(40) NOT NULL PRIMARY KEY,
  content_value TEXT NOT NULL,
  updated_by INT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lms_materials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  class_id INT NOT NULL,
  title VARCHAR(150) NOT NULL,
  description VARCHAR(500) NULL,
  kind ENUM('File','Link') NOT NULL DEFAULT 'File',
  original_name VARCHAR(150) NULL,
  stored_name VARCHAR(80) NULL,
  mime_type VARCHAR(100) NULL,
  size_bytes INT UNSIGNED NULL,
  link_url VARCHAR(500) NULL,
  is_visible TINYINT(1) NOT NULL DEFAULT 1,
  uploaded_by INT NULL,
  deleted_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_lms_class (class_id, deleted_at),
  FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS email_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  recipient VARCHAR(150) NOT NULL,
  subject VARCHAR(200) NOT NULL,
  template VARCHAR(40) NOT NULL,
  status ENUM('Sent','Failed','Skipped') NOT NULL,
  error VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_email_created (created_at),
  KEY idx_email_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;