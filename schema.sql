-- SIT-EnrollEase schema, Part 1: Foundation
-- Patakbuhin sa phpMyAdmin (database: sit_enrollease)

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE,
  username VARCHAR(30) NULL UNIQUE
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
  user_id INT NOT NULL UNIQUE,
  term_id INT NULL,
  program_id INT NULL,
  applicant_type VARCHAR(20) NOT NULL DEFAULT 'New',
  status VARCHAR(30) NOT NULL DEFAULT 'Draft',
  birthdate DATE NULL,
  birthplace VARCHAR(120) NULL,
  sex VARCHAR(10) NULL,
  civil_status VARCHAR(20) NULL,
  nationality VARCHAR(60) NULL,
  mobile VARCHAR(20) NULL,
  address VARCHAR(255) NULL,
  guardian_name VARCHAR(120) NULL,
  guardian_relationship VARCHAR(40) NULL,
  guardian_mobile VARCHAR(20) NULL,
  last_school VARCHAR(150) NULL,
  education_level VARCHAR(60) NULL,
  year_graduated SMALLINT NULL,
  occupation VARCHAR(100) NULL,
  employer VARCHAR(150) NULL,
  church_name VARCHAR(150) NULL,
  church_address VARCHAR(255) NULL,
  pastor_name VARCHAR(120) NULL,
  pastor_mobile VARCHAR(20) NULL,
  is_baptized TINYINT(1) NULL,
  ministry_experience TEXT NULL,
  remarks TEXT NULL,
  submitted_at DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_app_status (status),
  INDEX idx_app_program (program_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

ALTER TABLE applications ADD CONSTRAINT fk_app_program FOREIGN KEY (program_id) REFERENCES programs(id);

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