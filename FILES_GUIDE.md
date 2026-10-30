# คู่มือไฟล์ในรีโป (Person 3)

อัปเดต 2026-10-30 ไฟล์นี้บอกว่าแต่ละไฟล์คืออะไร อันไหนใช้อยู่ อันไหนจำเป็น และอันไหนเป็นของเก่า

## สรุปสั้น ๆ

- **โค้ดปัจจุบัน:** `p3/` เวอร์ชัน 1.2.1
- **Feature schema ปัจจุบัน:** `p3-features-1.2` (77 primary features, FROZEN)
- **ชุดข้อมูลทดลองปัจจุบัน:** 1,131 trajectories (IPI 873 + benign 258) payload `important_instructions_no_names`
- **ชุดข้อมูลเก่า:** 1,158 trajectories (payload แบบ baseline) เก็บไว้เป็น historical baseline
- **ผลลัพธ์ชุด 1,131:** อยู่ในเครื่องที่ `output_pii_1131_p3-1.2/` **ยังไม่ขึ้นรีโป** (ดูหัวข้อ "ไฟล์ที่ไม่อยู่ในรีโป")

## 1. ใช้อยู่ตอนนี้ และจำเป็น

| ที่อยู่ | คืออะไร | ลบได้ไหม |
| --- | --- | --- |
| `p3/` | โค้ด pipeline ทั้งหมด | ห้ามลบ |
| `schema/feature_schema_p3-features-1.2.json` | Schema ที่ freeze แล้ว pipeline ใช้ตรวจ hash ก่อนรัน | ห้ามลบ ห้ามแก้ |
| `tests/test_p3.py` | Unit test 49 ข้อ | ห้ามลบ |
| `tools/freeze_schema.py` | สร้าง schema ใหม่เมื่อออก feature version ใหม่ | เก็บไว้ |
| `tools/build_handoff.py` | สร้างโฟลเดอร์และ zip สำหรับชุด 1,158 และ pilot | เก็บไว้ |
| `docs/feature_schema_v1.2.md` | อธิบาย feature ทั้ง 77 ตัว | เก็บไว้ |
| `docs/preprocessing_notes_v1.2.md` | อธิบายกฎการ preprocessing | เก็บไว้ |
| `handoff/CANDIDATE_READ_ME_FIRST.md`, `handoff/README_CODE.md` | เอกสารที่แนบไปกับ handoff (เขียนสำหรับชุด 1,158) | เก็บไว้ |
| `README.md`, `FILES_GUIDE.md` | คู่มือรีโป | เก็บไว้ |

ไฟล์สำคัญใน `p3/`:

| ไฟล์ | หน้าที่ |
| --- | --- |
| `pipeline.py`, `__main__.py` | จุดเริ่มรัน: อ่าน → ตรวจ id → ประมวลผล → เขียน package |
| `parsers.py` | อ่าน log แบบ raw และ blinded |
| `normalize.py` | จัดลำดับ event, จับคู่ call กับ result, นับ step ใหม่, ตัด field ที่ไม่อยู่ใน whitelist |
| `tool_taxonomy.py` | ตาราง attribute ของ tool 69 ตัว |
| `tool_signatures.py` | Signature ของ tool ใช้ตรวจ argument ขาดหรือเกิน |
| `descriptors.py` | แปลงค่า argument เป็นชนิดข้อมูล |
| `features.py` | คำนวณ feature |
| `schema.py` | ตรวจว่าโค้ดยังตรงกับ schema ที่ freeze |
| `validation.py`, `reports.py` | ตรวจ input และเขียน quality report |
| `leakage.py`, `fsutil.py`, `common.py` | ตัวกัน leakage, การเขียน output แบบปลอดภัย, helper |

## 2. เอกสารรายงาน

| ที่อยู่ | สถานะ |
| --- | --- |
| `docs/report_algorithm_p3.md` | Algorithm 1 ฉบับสั้น 13 บรรทัด และ prompt สำหรับ Overleaf **ใช้อยู่** |
| `docs/report_section_normalization_v2.md` | ร่างส่วนของ P3 พร้อม Algorithm 1 ตัวเลขยังเป็นชุด 1,158 |
| `docs/report_section_normalization.md` | ร่างแรก ไม่มี algorithm ตัวเลขยังเป็นชุด 1,158 |

**ฉบับจริงของรายงานอยู่ใน Overleaf** ตัวเลขชุด 1,131 อยู่ที่นั่น ส่วนสองไฟล์ร่างนี้เก็บไว้อ้างอิงเท่านั้น

## 3. ผลลัพธ์ที่เก็บไว้ในรีโป

| ที่อยู่ | คืออะไร | สถานะ |
| --- | --- | --- |
| `output_candidate_p3-1.2/` | Package ของชุด 1,158 | **Historical baseline** |
| `output_pilot_v0.1_p3-1.0/` | Package ของ pilot 54 runs (schema 1.0) | ของเก่า แต่ยังอ้างอิงใน paper |
| `mock/`, `output_mock/` | ข้อมูลสังเคราะห์ ใช้ตอนพัฒนา | ไม่ใช่ข้อมูลจริง |

ไฟล์ใน package ของ output:

| ไฟล์ | คืออะไร |
| --- | --- |
| `features.csv` | ตาราง feature ส่งให้ P1/P4 (มีแค่ `trajectory_id` + 77 features) |
| `canonical_trajectories.jsonl` | Normalized trajectories ไม่มีข้อความและค่า argument |
| `feature_dictionary.csv`, `feature_readme.md`, `feature_schema.json` | คำอธิบาย feature และ schema |
| `quality_report.md`, `quality_issues.csv`, `id_validation.json` | ผลตรวจคุณภาพ |
| `feature_summary.md` | ค่าสถิติของแต่ละ feature |
| `trajectory_index.csv` | Metadata เช่น suite **ห้ามใช้เป็น feature** |
| `preprocessing_metadata.json`, `preprocessing_notes_v1.2.md` | เวอร์ชันและกฎที่ใช้รัน |
| `checksums.sha256` | Checksum ของ package |

## 4. ของเก่า (ไม่ได้ใช้แล้ว)

| ที่อยู่ | คืออะไร |
| --- | --- |
| `archive/` | โค้ดและ package เวอร์ชันเก่า (0.2, 0.3, 1.0, 1.1) ใช้ย้อนดูเท่านั้น **ห้ามส่งต่อ** |
| `schema/feature_schema_p3-features-1.0.json`, `...-1.1.json` | Schema เก่า เก็บไว้ตรวจย้อนหลัง |
| `docs/canonical_schema_v0.1.md`, `v0.2.md` | เอกสาร schema รุ่นแรก |
| `docs/feature_schema_v1.0.md`, `v1.1.md`, `preprocessing_notes.md`, `preprocessing_notes_v1.1.md` | เอกสารเวอร์ชันก่อน |
| `PILOT_REPORT_P3.md`, `HANDOFF_P4.md`, `handoff/P1_READ_ME_FIRST.md`, `handoff/P4_READ_ME_FIRST.md` | เอกสารรอบ pilot |
| `tools/make_mock_logs.py` | สร้างข้อมูลใน `mock/` |

## 5. ไฟล์ที่ไม่อยู่ในรีโป

| ไฟล์ | เหตุผล |
| --- | --- |
| `output_pii_1131_p3-1.2/` | ข้อมูลชุด 1,131 รีโปนี้เป็น public และ package ของ P2 ระบุว่า "NOT released until P1 approval" ต้องรอ P1 อนุมัติก่อน |
| `P1_PRIVATE_*`, ไฟล์ `*P1ONLY*` | ไฟล์ลับของ P1 (id mapping) **ห้ามขึ้นรีโปและห้าม P3 ใช้เด็ดขาด** |
| `../trajectories_sanitized/`, `../P2_*`, `../P1_to_P3/`, `../person1_pilot_handoff_v0.1/` | ข้อมูลและเอกสารของเพื่อน อยู่นอกโฟลเดอร์รีโป |
| `../P3_to_*.zip` | Zip ที่ส่งเพื่อน สร้างใหม่ได้ ปัจจุบันใช้ `P3_to_P1_pii_1131_v1.2.zip` |

`.gitignore` กันไฟล์ในตารางนี้ไว้แล้ว ถ้า P1 อนุมัติให้เผยแพร่ชุด 1,131 ให้ลบบรรทัด `output_pii_1131_p3-1.2/` ออกจาก `.gitignore` แล้วค่อย commit
