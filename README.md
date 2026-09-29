# coep-unitime-pilot

See `unitime-out/README.md` to get started.

## Lunch Breaks Configuration

To configure automated 1-hour Student and Instructor lunch breaks (between 11:30 AM and 3:30 PM), upload and execute `scripts/setup_lunch_breaks.py` in the UniTime **Administration > Utilities > Scripts** menu.

## Spring 2026 Spr6 XML Exports

The `unitime-out-spr6/` directory contains 12 XML files. The primary dataset scope is campus `COEP`, year `2026`, term `Spr6`.

- **Offerings:** 54 course offerings (`offerings.xml`), containing 262 classes.
- **Students:** 1,290 student records in `students.xml` and `request.xml`; `studentEnrollments.xml` contains enrollment records for 990 students.
- **Staff:** 117 instructor records in `preferences.xml`. The Spr6 offerings/timetable reference 46 distinct instructors across 260 class-instructor assignments.

The inventory below gives each document's root element, creation timestamp (when supplied), size, and notable record counts. Root metadata is shown as `campus/year/term`; unless noted, it is `COEP/2026/Spr6`.

| XML file                   | Root                   | Created                   | Size (bytes) | Notable contents / metadata                                                                                                                    |
| -------------------------- | ---------------------- | ------------------------- | -----------: | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `curricula.xml`            | `curricula`            | Sep 27, 2026 16:05:23 IST |          262 | Empty export (no curriculum records)                                                                                                           |
| `lastLikeCourseDemand.xml` | `lastLikeCourseDemand` | Sep 27, 2026 16:05:23 IST |          284 | Empty export (no demand records)                                                                                                               |
| `offerings.xml`            | `offerings`            | Sep 27, 2026 16:05:17 IST |      139,774 | 54 offerings/courses; 262 classes; 260 instructor assignments; `includeExams=all`, date format `yyyy/M/d`, time format `HHmm`                  |
| `preferences.xml`          | `preferences`          | Sep 27, 2026 16:05:18 IST |      111,514 | 4 departments; 117 instructors; 717 preferences; date format `yyyy/M/d`, time format `HHmm`                                                    |
| `request.xml`              | `request`              | Not supplied              |    1,792,207 | 1,290 students; 4,798 course requests; 7,748 class requests                                                                                    |
| `reservations.xml`         | `reservations`         | Sep 27, 2026 16:05:23 IST |          157 | Empty export (no reservation records); date format `MM/dd/yyyy`                                                                                |
| `roomSharing.xml`          | `roomSharing`          | Sep 27, 2026 16:05:23 IST |       10,736 | 45 locations/departments/sharing rules/unavailable entries; time format `HHmm`                                                                 |
| `sessionSetup.xml`         | `sessionSetup`         | Sep 27, 2026 16:06:44 IST |       35,547 | 1 session; 6 holidays; 7 managers; 13 departments; 34 examination periods; 208 student groups; date format `yyyy/M/d`                          |
| `studentEnrollments.xml`   | `studentEnrollments`   | Not supplied              |    1,097,288 | 990 students; 7,748 class enrollment entries                                                                                                   |
| `students.xml`             | `students`             | Not supplied              |      442,950 | 1,290 students; 1,290 academic-area/classification and major records                                                                           |
| `timetable.xml`            | `timetable`            | Sep 27, 2026 16:05:18 IST |      122,952 | Action `update`; 262 classes, times, and rooms; 260 instructor assignments; date format `yyyy/M/d`, time format `HHmm`                         |
| `timetable_spr9.xml`       | `timetable`            | Sep 29, 2026 14:30:58 IST |       95,213 | **Different scope:** `COEP/2026/Spr9`; action `update`; 291 classes and 289 instructor assignments; date format `yyyy/M/d`, time format `HHmm` |
| `traveltimes.xml`          | `traveltimes`          | Sep 27, 2026 16:05:23 IST |        2,204 | 6 `from` and 21 `to` travel-time entries                                                                                                       |

Creation times are preserved from the XML root attributes and shown in IST. Sizes are the on-disk XML file sizes in bytes. Counts are XML element counts, so repeated `class`, `time`, `room`, and `instructor` elements are assignment or schedule rows rather than distinct entities.
