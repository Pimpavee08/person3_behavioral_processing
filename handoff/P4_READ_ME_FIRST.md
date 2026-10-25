# P3 → P4: อ่านไฟล์นี้ก่อน

จาก Person 3 (Trajectory Normalization / Feature Extraction) วันที่ 2026-10-03
Package นี้: features ของ Pilot v0.1 ใช้ **feature schema `p3-features-1.0` (FROZEN)**

## 1. สถานการณ์ตอนนี้

| ส่วน | สถานะ |
| --- | --- |
| Pilot (P2) | รันครบ 54 runs (9 scenario groups × benign/IPI × 3 LLM) ไม่มี error ใช้ LLM-A gemma4:12b, LLM-B qwen3.5:9b, LLM-C lfm2.5 ผ่าน Ollama |
| Features (P3) | **เสร็จและ freeze แล้ว** ใช้ data ครบ 54 runs มี primary features 72 ตัว |
| Labels (P1) | **ยังไม่มี** P1 กำลังทำ handoff v0.2 (`approved_labels_pilot_v0.2.csv`) |
| P4 ทำอะไรได้ตอนนี้ | เขียน pipeline สำหรับ train / 3×3 / metrics ด้วย mock data ในโฟลเดอร์ `mock_for_pipeline_dev/` แล้วรอ label จริงจาก P1 |

ข้อควรรู้: P2 รายงานว่าทำตาม attacker สำเร็จแค่ประมาณ 3 จาก 27 IPI runs
Positive ของ `ipi_affected` น่าจะมีน้อยมาก ผลของ pilot จึงใช้ยืนยันได้แค่ว่า pipeline ทำงาน ไม่ใช่ผลวิจัย

## 2. ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | คืออะไร | P4 ใช้ไหม |
| --- | --- | --- |
| `00_READ_ME_FIRST.md` | ไฟล์นี้ | อ่าน |
| `HANDOFF_P4.md` | วิธี join label, วิธีทำ 3×3 แบบ leave-one-group-out, การตรวจ pipeline และสิ่งที่ต้องเขียนในรายงาน | **อ่านก่อนเริ่มเขียนโค้ด** |
| `checksums.sha256` | SHA-256 ของทุกไฟล์ในโฟลเดอร์นี้ | ตรวจก่อนใช้ |
| **`features_package/`** | **ข้อมูลจริงจาก pilot** | |
| ├ `features.csv` | 54 แถว: `run_id` + primary features 72 ตัว | **ใช้ train / test** |
| ├ `feature_schema.json` | Schema ที่ freeze แล้ว (`primary_features` คือรายชื่อคอลัมน์ตามลำดับ) | ใช้ตรวจคอลัมน์ |
| ├ `feature_dictionary.csv` | ความหมายของ feature ทุกตัว | อ้างอิง |
| ├ `feature_schema_v1.0.md` | เอกสาร schema และวิธีเตรียมข้อมูล | อ้างอิง |
| ├ `run_index.csv` | `source_llm`, `suite`, `user_task_id`, `scenario_group_id` ต่อ `run_id` | ใช้แบ่ง LLM และ group **ห้ามเป็น feature** |
| ├ `canonical_trajectories.jsonl` | Trajectory ที่ normalize แล้ว (ไม่มีข้อความดิบ) | ไม่จำเป็น ใช้ตรวจย้อนหลังได้ |
| ├ `features_extended.csv` | Primary 72 ตัว + secondary 12 ตัว (ข้อความและเวลา) | **ห้ามใช้ใน primary detector** |
| ├ `feature_summary.md` | ค่าเฉลี่ย feature แยกตาม LLM | ดูประกอบได้ |
| ├ `preprocessing_notes.md`, `preprocessing_metadata.json` | วิธีเตรียมข้อมูล, input hash และสิ่งที่ P3 เห็นก่อน freeze | อ้างอิงในรายงาน |
| ├ `quality_report.md`, `quality_issues.csv` | คุณภาพของ log (error 0) | อ้างอิง |
| └ `checksums.sha256` | Checksum ของ package | ตรวจได้ |
| **`mock_for_pipeline_dev/`** | **ข้อมูลสังเคราะห์ ไม่ใช่ผลจริง** | |
| ├ `features.csv`, `run_index.csv` | รูปแบบเดียวกับของจริง (54 runs จำลอง) | ใช้ทดสอบโค้ด |
| └ `adjudicated_labels.mock.jsonl` | Label จำลอง (มี `ipi_affected`) คีย์ `run_id` ตรงกับ mock features | ใช้ทดสอบโค้ดเท่านั้น **ห้ามรายงานผล** |

## 3. สิ่งที่ P4 ต้องรู้ (สำคัญ)

1. **Feature schema freeze แล้ว** (`schema_sha256 855628e7ea1c5cf380019c38fe04dcd5491945c03e2517cbb218ed4758923779`) ห้ามขอเปลี่ยน feature หลังจากเห็นผลของ detector ถ้าจำเป็นจริงต้องออกเวอร์ชันใหม่และแจ้งทั้งทีม
2. **Label มาจาก P1 เท่านั้น:** เป้าหมายหลักคือ `ipi_affected` ห้ามใช้ `condition` เป็น label (Protocol v0.2 ข้อ 12)
3. **ห้ามใช้ `run_id` เป็น feature** เพราะมีชื่อ LLM และคำว่า `benign` / `ipi` อยู่ในตัว ใช้เป็น join key เท่านั้น
4. **`source_llm` ใช้แบ่งข้อมูลเพื่อทำ 3×3 เท่านั้น** ห้ามเป็น feature
5. **ใช้ `features.csv` เท่านั้น** `features_extended.csv` ไม่ใช่ primary input
6. **Join กับ label ด้วย `run_id` แบบ 1:1** และรายงาน run ที่จับคู่ไม่ได้ ห้ามตัดทิ้งเงียบๆ
7. **`Unknown` ห้ามแปลงเป็น 0** IPI run ที่ `injection_encountered` ไม่ใช่ 1 ให้แยกออกจากการประเมินหลัก (ใน pilot มี 1 run)
8. **Feature 22 ตัวคงที่ใน pilot** ให้ตัดออกภายใน fold โดยดูจากข้อมูล train เท่านั้น
9. **Pilot เป็น development data** ห้าม tune hyperparameter และห้ามใช้ 9 scenario groups นี้เป็น held-out test ของ Full Experiment
10. **ช่อง 3×3 ที่ train ไม่มี positive** ให้เขียนว่า "train ไม่ได้" ห้ามใส่ F1 = 0

## 4. ขั้นตอนที่แนะนำ

1. ตรวจ checksum ในโฟลเดอร์นี้:

   ```bash
   sha256sum -c checksums.sha256
   ```

2. เขียนและทดสอบ pipeline ด้วย `mock_for_pipeline_dev/` (join → leave-one-group-out 3×3 → confusion matrix / P / R / F1 → Gap)
3. ตรวจด้วยการสลับ label: F1 ต้องลดลงไปที่ระดับเดา
4. ลองใช้ features ทำนาย `source_llm` เพื่อดูว่า feature บอกตัวโมเดลได้แค่ไหน
5. รอ `approved_labels_pilot_v0.2.csv` จาก P1 แล้วรันกับ `features_package/`
6. รายงานผลในฐานะ "pipeline validation" พร้อมข้อจำกัดใน `HANDOFF_P4.md` ข้อ 6

มีคำถามเรื่อง feature หรือรูปแบบไฟล์ ถาม P3 ได้เลย
