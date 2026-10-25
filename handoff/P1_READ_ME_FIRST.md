# P3 → P1: อ่านไฟล์นี้ก่อน

จาก Person 3 วันที่ 2026-10-03
เรื่อง: ประกาศ feature schema freeze, ส่ง package ของ P3 และข้อสังเกตจาก raw log

## 1. สรุป

- P3 ทำตามคำสั่งสำหรับ Person 3 และ Data Contract v0.2 ครบแล้ว (checklist ทีละข้อใน `PILOT_REPORT_P3.md` ข้อ 1)
- **Feature schema `p3-features-1.0` freeze แล้ววันที่ 2026-10-03**
  `schema_sha256 = 855628e7ea1c5cf380019c38fe04dcd5491945c03e2517cbb218ed4758923779`
  P1 ส่ง `approved_labels_pilot_v0.2.csv` ให้ P4 ได้แล้ว
- P3 ไม่ได้รับ approved labels, `eval_evidence.jsonl`, snapshots, evaluator outputs หรือ adjudication notes
- สิ่งที่ P3 เคยเห็นก่อน freeze เปิดเผยไว้ใน `features_package/preprocessing_notes.md`
- ผลของ pipeline: 54 runs, error 0, tool call จับคู่กับ result ได้ 100%, primary features 72 ตัว

## 2. ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | คืออะไร |
| --- | --- |
| `00_READ_ME_FIRST.md` | ไฟล์นี้ |
| `PILOT_REPORT_P3.md` | Checklist ตามคำสั่ง P1 (ข้อ 1), ผลของ pipeline (ข้อ 3), **ข้อสังเกตสำหรับตัดสิน label (ข้อ 4)**, ข้อสังเกตถึง P2 (ข้อ 5) |
| `features_package/` | Package เดียวกับที่ส่ง P4 ใช้ตรวจตาม Contract ข้อ 12 (Feature validation) ได้ |
| ├ `feature_schema.json`, `feature_schema_v1.0.md`, `feature_dictionary.csv` | Schema ที่ freeze แล้ว และตาราง mapping กับ primary features ที่ P1 แนะนำ |
| ├ `preprocessing_notes.md`, `preprocessing_metadata.json` | สิ่งที่ได้รับและไม่ได้รับ, input hash, กฎที่ใช้ |
| ├ `features.csv`, `canonical_trajectories.jsonl`, `run_index.csv` | Feature table, normalized trajectories, metadata สำหรับ split (ไม่มี label) |
| └ อื่นๆ | Quality report, secondary features, checksums |
| `checksums.sha256` | SHA-256 ของทุกไฟล์ในโฟลเดอร์นี้ |

## 3. ขอให้ P1 ช่วย

1. **ยืนยันการ freeze กับทีม** หรือแจ้งกลับถ้ามีอะไรต้องแก้ ต้องแจ้งก่อนส่ง label ให้ P4 เพราะหลังจากนั้นแก้ไม่ได้
2. **ดูข้อสังเกตใน `PILOT_REPORT_P3.md` ข้อ 4** โดยเฉพาะ `travel_user_task_7__ipi__LLM-C` ที่ agent ใส่อีเมลของ attacker เป็น participant ของ calendar event ซึ่ง protocol v0.1 ยังไม่มีกฎ
3. **ถ้า handoff v0.2 เปลี่ยน manifest** (เช่น `scenario_id` หรือ `user_prompt`) แจ้ง P3 แล้ว P3 จะรัน pipeline ใหม่ด้วย schema เดิม
4. **Label file ต้องใช้ `run_id` ชุดเดียวกับ `features.csv`** (54 runs ของ P2) เพื่อให้ P4 join แบบ 1:1 ได้
