# SIT-EnrollEase — Implementation Status

## Implemented in source

| Request | Status | Notes |
|---|---|---|
| Separate electives by program | Already supported | Curriculum is queried by program and displayed in program-specific groups. |
| Edit curriculum units | Implemented | Registrar can update an individual program-curriculum row; 1–12 whole units validation and audit log. |
| Hide units on public landing page | Implemented | Public Offered Programs no longer displays unit counts; internal units remain. |
| CCL 24 → 28 units | Implemented in seed/migration | Seed total matches 14 existing core subjects × 2 units. |
| Field Education I–IV, 1 unit each | Implemented for curricula already containing legacy Field Education | `seed_curriculum.py` replaces the old curriculum association after adding four subjects; old subject row is retained. Other programs that currently have no Field Education were not given new courses because that changes their official curricula. |
| Manual account number | Implemented | System suggestion removed; Finance enters it manually; existing uniqueness check remains. Existing account numbers are not overwritten. |
| Accounting receipt format | Implemented | Uses stored student/program/term/fee/payment data; discount field added with zero default. |
| Pre-Enrollment Form | Implemented | Printable form uses the signed-in student's own application and COR; subjects/schedule populate once a COR exists. |
| Remove rating feature | Implemented in interface | Removal-rating controls/report columns removed; database field retained for historical data. |
| Faculty Upload sidebar | Implemented | Separate Upload page reuses assigned-class material management. |
| PRELIM/MIDTERMS/FINALS | Implemented | Material records now carry a phase; student view groups by phase. |
| Current-trimester-only student visibility | Implemented | Student material/announcement queries are limited to current-term classes on that student's COR. |
| Class announcements | Implemented | Faculty can post/delete announcements within assigned classes; students see only announcements for classes on their COR. |
| Student Classes | Implemented | Current-trimester classes, announcements, and materials are shown. |
| My Registration Form → printable COR | Implemented | Uses the signed-in student's own COR route. |
| Watermark on printouts | Implemented in print templates | Faint institutional watermark added to updated printable forms. |

## Clarifications incorporated in the 2026-11-12 follow-up update

| Request | Status | Notes |
|---|---|---|
| Personal Info Form | Removed from scope | It is not required. No new Personal Info Form route or duplicate form is created. |
| Field Education I–IV | Confirmed against official Programs of Study | The official document lists FE in BThPM, BThCE, MACE, and MACM. Each of those four program curricula has Field Education I, II, III, and IV as separate 1-unit subjects. No FE was added to programs without it in the official curriculum. |
| Student Portal layout | Refined while preserving SIT identity | The existing SIT logo, teal/green brand palette, and shared application layout are retained. Student navigation is rearranged and a University Resources area is added. The LearnU screenshots are used only as layout/feature references, not as branding to copy. |
| COR print layout | Matches supplied Certificate of Registration sample | The print template follows the supplied sample fields and columns: student no., name, program, year, date enrolled, trimester, scholarship, course code, descriptive title, units, day/time, professor, and total units. |
| Faculty year-level filter | Implemented | Faculty can filter their class list by the year levels represented by students enrolled in each class, and filter the roster within a class. This is a filter only; it does not assign classes to a year level or alter CORs. |
| Student portal terms and navigation | Preserved and rearranged | Existing term labels and feature names are retained. No student calendar feature is added. Existing SIT application styling remains in place. |
| University Resources | Implemented | Admin and Registrar can publish/hide university-wide files or links by category. Students see published resources only. This is separate from class handouts. |
| Classes announcements | Implemented | Each enrolled class always displays its own Announcements section, including an empty state. Faculty can post announcements; students see announcements only for classes on their COR. |
| Class handouts/materials | Preserved | Existing faculty upload/edit/show/hide/delete workflows and student access restrictions remain connected to the class. |

## Verification notes

- The four FE-bearing programs were cross-checked against the supplied Programs of Study document: Bachelor of Theology Major in Pastoral Ministry, Bachelor of Theology Major in Christian Education, Master of Arts in Christian Education, and Master of Arts in Christian Ministry.
- The existing COR print template already follows the supplied Certificate of Registration sample; it was retained rather than replaced with an unrelated layout.
- The Student Portal retains SIT branding and the existing shared app shell. The LearnU screenshots are used as layout inspiration only.
- University-wide Resources require the new migration `20261112_university_resources.sql` on an existing database.
- The Faculty year filter reads year level from the student's existing COR. It does not mutate student records or class assignments.

## Verification

- `python -m compileall -q .`: passed after the follow-up update.
- Jinja parsing of all HTML templates: passed after the follow-up update.
- Flask runtime and MySQL integration have not been run in this environment.
- No live database was connected or modified. No user accounts, student records, payments, CORs, grades, or historical records were deleted.
