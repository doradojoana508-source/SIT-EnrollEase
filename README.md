# SIT-EnrollEase — Client Requested Updates

This package contains targeted updates to the existing Flask/MySQL SIT-EnrollEase project. It is not a rebuild.

## Important configuration note

`config.py` is intentionally not included in this export so that secrets, passwords, and database credentials are not redistributed. Keep your existing local `config.py` in place when replacing the project files. `config.example.py` is only a reference template and does not contain live credentials.

## Applying updates to an existing database

1. Back up your database first.
2. From the MySQL client, run `migrations/20261111_client_requested_updates.sql` exactly once.
3. From the project root, run `python seed_curriculum.py` to refresh curriculum rows, split the existing combined Field Education entries into Field Education I–IV (1 unit each), and update the CCL official unit total to 28.
4. Install project dependencies from `requirements.txt` in your existing virtual environment.
5. Start the app using your normal local workflow.

The migration adds LMS exam-period classification, class-scoped announcements, quotation discount support, and updates CCL's official unit requirement. Existing LMS materials default to PRELIM. Existing quotations default to zero discount. Existing payment history is preserved.

## Changes in this package

- Public Offered Programs no longer show units.
- Registrar curriculum detail has per-program unit editing with validation and audit logging.
- CCL is set to 28 units, matching its 14 existing 2-unit core subjects.
- Existing combined Field Education rows in curricula that already had Field Education are migrated to Field Education I–IV, each 1 unit. The legacy subject row is retained for historical class references.
- Account numbers are manually entered by Finance; existing account numbers remain unchanged and uniqueness validation remains in place.
- Finance quotations now support a discount field and calculate totals server-side.
- The printable accounting form uses existing student, program, term, unit, fee, discount, and payment data.
- A printable Pre-Enrollment Form is available from the student's own pre-enrollment record; course rows appear when the student's COR exists.
- Removal-rating controls and report columns are removed from the interface. The legacy database column is retained so historical records are not destroyed.
- Faculty has a separate Upload navigation page. Uploads can be grouped by PRELIM, MIDTERMS, and FINALS while the existing Classes workflow remains available.
- Class announcements are scoped to the faculty member's assigned class and are visible to students only when that class is on their current COR.
- Student Classes shows the student's current-trimester enrolled classes, class announcements, and available materials. Material file access is checked on the server against the student's COR.
- My Registration Form opens the student's own printable COR.
- Printable forms include a faint institutional watermark.

## Verification limitations

Python source compilation and Jinja template parsing were checked in the build environment. Full Flask route execution and database integration tests were not run because Flask dependencies and the target MySQL database are not available in this environment. Apply the migration and run the project in your existing environment before using it for a client demonstration.

### Student Portal Resources and Faculty year filters

- The student sidebar includes **Resources** for university-wide documents and official links. Admin and Registrar can manage these items under **University Resources**.
- University-wide resources are stored separately from class handouts. Run `migrations/20261112_university_resources.sql` once on an existing database before using the Resources pages.
- Faculty can filter assigned classes and class rosters by the year level stored on each student's COR. This is a display filter and does not change class assignments or student records.
- Student **Classes** keeps class-specific announcements and the existing class handout/materials feature. The student calendar is not part of this portal navigation.
