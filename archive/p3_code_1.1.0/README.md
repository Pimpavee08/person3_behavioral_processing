# Person 3 – Trajectory Normalization / Feature Extraction (v1.1)

แปลง trajectory ของ Person 2 (ทั้งแบบ raw และแบบ blinded) ให้เป็น canonical structural trajectory แล้วสกัด structural features ตาม **Data Contract v0.2**

**สถานะ (2026-10-10):**
- Candidate set ของ P2 (1,158 blinded trajectories): ทำเสร็จด้วย feature schema `p3-features-1.1` (**FROZEN**, `schema_sha256 2f794f2d…63ee5`)
  - ID ตรวจผ่าน (1,158 ไม่ซ้ำ), error 0
  - package อยู่ที่ `output_candidate_p3-1.1/` zip ที่ส่งคือ `../P3_to_P1_P4_candidate_v1.1.zip`
- Pilot v0.1 (54 runs): ส่งไปแล้วด้วย schema `p3-features-1.0` โค้ดของเวอร์ชันนั้นอยู่ใน `archive/p3_code_1.0.0/`
- Unit test 32 ข้อผ่านทั้งหมด

เอกสาร: [docs/feature_schema_v1.1.md](docs/feature_schema_v1.1.md), [docs/preprocessing_notes_v1.1.md](docs/preprocessing_notes_v1.1.md) (เอกสาร pilot: [PILOT_REPORT_P3.md](PILOT_REPORT_P3.md), [HANDOFF_P4.md](HANDOFF_P4.md))

## วิธีรัน (candidate set)

```bash
python -m p3 --raw ../P2_P3_candidate_package/trajectories_sanitized.jsonl --out output_candidate_p3-1.1 --expected 1158
```

```bash
python tools/build_handoff.py
```

## วิธีรัน (pilot, schema 1.0 – ใช้โค้ดใน archive/p3_code_1.0.0)

ใช้ Python 3.9 ขึ้นไป ไม่ต้องติดตั้ง library เพิ่ม ทุกคำสั่งรันในโฟลเดอร์นี้

1. สร้าง package จาก Pilot ของ P2:

```bash
python -m p3 --raw ../P2_for_P3_P4/raw_runs.jsonl --out output_pilot_v0.1_p3-1.0 --manifest ../person1_pilot_handoff_v0.1/output/pilot_manifest_v0.1.csv --run-metadata ../P2_for_P3_P4/run_metadata.txt
```

2. Test ทั้งหมด:

```bash
python -m unittest discover -s tests -v
```

3. สร้างโฟลเดอร์และ zip ที่จะส่ง (`../P3_to_P4`, `../P3_to_P1`) วิธีส่งดูที่ `../SEND_GUIDE_P3.md`:

```bash
python tools/build_handoff.py
```

4. Mock logs (ใช้ตอนพัฒนา ไม่ใช่ข้อมูลจริง):

```bash
python tools/make_mock_logs.py
```

ข้อควรรู้:
- Pipeline จะไม่ยอมรันถ้าโค้ดของ feature ไม่ตรงกับ `schema/feature_schema_p3-features-1.0.json`
- ถ้าจะเปลี่ยน feature ให้เพิ่ม `FEATURE_SET_VERSION` ใน `p3/features.py` แล้ว freeze ใหม่ด้วย `python tools/freeze_schema.py --date YYYY-MM-DD` และแจ้งทีม
- ถ้ามี raw หรือ manifest ใหม่ ให้ใช้โฟลเดอร์ `--out` ใหม่ทุกครั้ง

## โครงสร้าง

| ที่อยู่ | หน้าที่ |
| --- | --- |
| `p3/parsers.py` | Raw trajectory parsing |
| `p3/tool_taxonomy.py` | Normalized tool categories ของ tool ทั้ง 69 ตัว |
| `p3/tool_signatures.py` | Signature ของ tool ที่ commit `a75aba76` ใช้ตรวจ argument ขาด/เกิน |
| `p3/normalize.py` | Normalization และ `structural_view()` (ตัดข้อความดิบและค่า argument) |
| `p3/features.py` | Primary 72 ตัว (จากโครงสร้างเท่านั้น) และ secondary 12 ตัว |
| `p3/schema.py`, `schema/` | Feature schema ที่ freeze แล้ว และตัวตรวจว่าโค้ดยังตรงกับ schema |
| `p3/leakage.py`, `p3/quality.py`, `p3/pipeline.py` | ตัวกัน leakage, validation, report และการเขียน package |
| `output_pilot_v0.1_p3-1.0/` | **Package ปัจจุบัน** |
| `archive/` | Package เวอร์ชันเก่า ห้ามส่งต่อ |
| `mock/`, `output_mock/` | ข้อมูลสังเคราะห์ ใช้ทดสอบเท่านั้น |

## ไฟล์ใน package

| ไฟล์ | หมายเหตุ |
| --- | --- |
| `features.csv` | `run_id` + primary features 72 ตัว |
| `canonical_trajectories.jsonl` | Normalized structural trajectories ไม่มีข้อความดิบ |
| `feature_schema.json`, `feature_schema_v1.0.md`, `feature_dictionary.csv` | Feature schema documentation (frozen) |
| `preprocessing_metadata.json`, `preprocessing_notes.md` | Preprocessing metadata และ notes |
| `run_index.csv` | ใช้แบ่งข้อมูลเท่านั้น ไม่มี label |
| `features_extended.csv` | Secondary features (ข้อความและเวลา) |
| `feature_summary.md`, `quality_report.md`, `quality_issues.csv` | ตรวจคุณภาพข้อมูล |
| `checksums.sha256` | Checksum ของไฟล์ทั้งหมดใน package |
