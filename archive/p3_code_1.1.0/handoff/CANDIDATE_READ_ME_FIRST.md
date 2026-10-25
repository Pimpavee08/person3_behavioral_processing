# P3 → P1 / P4: Features ของ candidate set (1,158 trajectories)

จาก Person 3 วันที่ 2026-10-10
Input: `P2_P3_candidate_package` (blinded trajectories ของ P2)
Feature schema: **`p3-features-1.1` (FROZEN)**
`schema_sha256 = 2f794f2d65dd3e63c8857a6d616e0a40fe0a39a29f7a7319e2fc5558c1c63ee5`

> **สถานะ: candidate**
> README ของ P2 เขียนว่า package นี้ "NOT released until P1 approval" ผลชุดนี้จึงเป็น candidate ด้วยจนกว่า P1 จะอนุมัติ
> P3 ไม่ได้รับและไม่ได้พยายามสร้างกลับ: label, ชื่อโมเดล, split, ข้อความของ assistant, ผลลัพธ์ของ tool, ID เดิม และ mapping ของ `trajectory_id`

## 1. ผลโดยสรุป

| รายการ | ผล |
| --- | --- |
| Trajectories | 1,158 ทุกตัวผ่านโครงสร้าง |
| ตรวจ `trajectory_id` | ไม่ซ้ำครบ 1,158 ไม่มีตัวหายหรือซ้ำ และตรงกับแถวในตาราง feature 1:1 (`id_validation.json` → PASS) |
| Issues | error 0 / warning 13 / info 1,136 |
| Primary features | 77 ตัว (คงที่ในชุดนี้ 2 ตัว: `n_calls_without_result`, `n_unparseable_args`) |
| ตรวจกับ `validation_report.json` ของ P2 | จำนวน error แต่ละชนิด (187/13/2/13), tool call (4,476) และ agent_final (1,154) ตรงกันทุกตัว |
| Tool ที่โมเดลแต่งชื่อขึ้นเอง | 13 calls ใน 8 trajectories (เช่น `get_all_car_rental_companies`) เก็บไว้เป็นพฤติกรรม และนับใน `n_unmapped_tool_calls` |
| ไม่มี `agent_final` | 4 trajectories ทั้งหมดใช้ครบ 15 steps (ตามที่ P2 แจ้ง ถือว่าปกติ) |

## 2. ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | คืออะไร |
| --- | --- |
| `features_package/features.csv` | **ตาราง feature สุดท้าย** 1,158 แถว มีคีย์ `trajectory_id` + primary features 77 ตัว ไม่มีคอลัมน์ label, โมเดล หรือ split |
| `features_package/feature_readme.md` | README อธิบาย feature ทีละตัว ตามลำดับคอลัมน์ |
| `features_package/feature_dictionary.csv`, `feature_schema.json`, `feature_schema_v1.1.md` | Feature dictionary / schema ที่ freeze แล้ว และสิ่งที่เปลี่ยนจาก 1.0 |
| `features_package/id_validation.json` | ผลตรวจ `trajectory_id` |
| `features_package/canonical_trajectories.jsonl` | Normalized trajectory representation (เฉพาะโครงสร้าง) |
| `features_package/trajectory_index.csv` | `trajectory_id` + `suite` + `input_schema_version` เป็น metadata เท่านั้น **ห้ามใช้เป็น feature** |
| `features_package/preprocessing_notes_v1.1.md`, `preprocessing_metadata.json` | การตัดสินใจ, ข้อจำกัด, hash ของ input และกฎที่ใช้ |
| `features_package/quality_report.md`, `quality_issues.csv`, `feature_summary.md` | คุณภาพของข้อมูล และสถิติเชิงพรรณนา |
| `code/` | โค้ด normalization และสกัด feature (`p3/`), test, schema ที่ freeze แล้ว และวิธีรัน (`code/README_CODE.md`) |
| `checksums.sha256` | SHA-256 ของทุกไฟล์ในโฟลเดอร์นี้ |

## 3. สิ่งที่ P4 ต้องรู้

1. **คีย์คือ `trajectory_id` เท่านั้น** ให้ join กับ label ของ P1 แบบ 1:1 และรายงานแถวที่จับคู่ไม่ได้
2. **ทุกคอลัมน์ใน `features.csv` (ยกเว้น `trajectory_id`) คือ primary feature** ส่วน `suite` และ `schema_version` อยู่ใน `trajectory_index.csv` เป็น metadata ห้ามใช้เป็น feature
3. **P3 ไม่ได้ fit อะไรกับข้อมูลทั้งชุด** ไม่มี scaling, imputation, feature selection หรือ PCA ทุกอย่างเหล่านี้ P4 ต้อง fit จาก training set เท่านั้น ส่วน feature ที่คงที่ให้ตัดภายใน fold
4. **ไม่มี `features_extended.csv`** เพราะข้อมูล blinded ไม่มีข้อความและเวลา
5. **ชื่อ tool ใช้ผ่าน category และการนับ** ไม่ได้แตกเป็นคอลัมน์ละชื่อ เพื่อลดการจำ task (Data Contract §11) ถ้าต้องการ ablation แบบรายชื่อ tool ให้ตกลงกับทีมและออก schema เวอร์ชันใหม่
6. **Feature เป็นคนละเวอร์ชันกับ pilot:** ชุดนี้ใช้ 1.1 ส่วน pilot ใช้ 1.0 ชื่อคอลัมน์บางตัวเปลี่ยน (ดู `feature_schema_v1.1.md` ข้อ 1) ห้ามรวมสองชุดในตารางเดียวกันโดยไม่ map คอลัมน์

## 4. ขอให้ P1 ช่วย

1. **อนุมัติ** P2 candidate package และ feature schema 1.1 (เปลี่ยนจาก 1.0 เพราะรูปแบบ input เปลี่ยน รายละเอียดใน `feature_schema_v1.1.md` ข้อ 1)
2. **ยืนยัน hash ของ zip ของ P2:** P3 ได้ไฟล์ที่แตกแล้ว จึงตรวจ zip SHA-256 `4C107981…0BDC` ไม่ได้ hash ของ `trajectories_sanitized.jsonl` ที่ P3 ใช้คือ `50f29859…d807`
3. **ส่ง label ของ candidate set ให้ P4** โดยใช้ `trajectory_id` ชุดเดียวกัน
