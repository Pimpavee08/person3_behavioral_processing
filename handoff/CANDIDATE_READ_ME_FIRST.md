# P3 → P1 / P4: Features ของ candidate set (1,158 trajectories)

จาก Person 3 วันที่ 2026-10-10
Input: `P2_P3_candidate_package` (blinded trajectories ของ P2)
Feature schema: **`p3-features-1.2` (FROZEN)**
- `schema_sha256 = 1c8adb151a5687f4fb4543bfb167c35766947cd7f17af588894983c7ec6f31d3`
- `code_sha256 = e5e40caf6ebad8394ec90adce94bd20aed82f7cd68215a6dc0b711ec13b68be7`

> **ฉบับล่าสุด: code `p3` 1.2.1** ปรับโครงสร้างโค้ดให้อ่านง่ายและเร็วขึ้น ไฟล์ข้อมูลทุกไฟล์ (features, trajectories, id check) **เหมือน v1.2 ที่ส่งก่อนหน้าทุก byte** ต่างกันแค่โค้ดใน `code/` เลขเวอร์ชันในรายงาน และเวลาที่สร้าง
>
> **ใช้ชุดนี้แทน v1.1 ที่ส่งไปก่อนหน้า** ถ้าได้ `P3_to_P1_P4_candidate_v1.1` ไปแล้วให้ลบทิ้ง (ดูข้อ 4)
>
> **สถานะ: candidate** README ของ P2 เขียนว่า package นี้ "NOT released until P1 approval" ผลชุดนี้จึงเป็น candidate ด้วยจนกว่า P1 จะอนุมัติ
> P3 ไม่ได้รับและไม่ได้พยายามสร้างกลับ: label, ชื่อโมเดล, split, ข้อความของ assistant, ผลลัพธ์ของ tool, ID เดิม และ mapping ของ `trajectory_id`
> คำถามเรื่อง label หรือที่มาของข้อมูลให้ถาม P1

## 1. สิ่งที่ต้องส่งกลับ (ตามที่ P2 ระบุ)

| สิ่งที่ต้องส่ง | ไฟล์ | สถานะ |
| --- | --- | --- |
| Normalized trajectory representation | `features_package/canonical_trajectories.jsonl` | ✅ 1,158 records มีแต่โครงสร้าง ไม่มีข้อความหรือค่าใดๆ |
| ตาราง feature สุดท้าย (คีย์ `trajectory_id` เท่านั้น ห้ามมี label / โมเดล / split) | `features_package/features.csv` | ✅ 1,158 แถว × `trajectory_id` + 77 features |
| Feature dictionary / schema | `features_package/feature_dictionary.csv`, `feature_schema.json`, `feature_schema_v1.2.md` | ✅ freeze แล้ว |
| โค้ด normalization และสกัด feature | `code/` (`code/README_CODE.md` บอกวิธีรัน) | ✅ รันจากโฟลเดอร์นี้แล้วได้ `features.csv` ตรงกันทุก byte |
| README อธิบายแต่ละ feature | `features_package/feature_readme.md` | ✅ ทีละตัวตามลำดับคอลัมน์ |
| ผลตรวจ `trajectory_id` ไม่ซ้ำครบ 1,158 ไม่มีหายหรือซ้ำ | `features_package/id_validation.json` | ✅ PASS: 1,158 unique, ซ้ำ 0, หาย 0, ตรงกับแถว feature 1:1 |

ไฟล์อื่นใน `features_package/`:
- `trajectory_index.csv`: `trajectory_id` + `suite` + `input_schema_version` เป็น metadata เท่านั้น **ห้ามใช้เป็น feature**
- `preprocessing_notes_v1.2.md`, `preprocessing_metadata.json`: การตัดสินใจ, ข้อจำกัด, hash ของ input และกฎที่ใช้
- `quality_report.md`, `quality_issues.csv`, `feature_summary.md`: คุณภาพข้อมูลและสถิติเชิงพรรณนา
- `checksums.sha256`: ใช้ตรวจไฟล์ใน `features_package/` ส่วน `checksums.sha256` ที่ระดับบนใช้ตรวจทั้งโฟลเดอร์

## 2. ผลโดยสรุป

| รายการ | ผล |
| --- | --- |
| Trajectories | 1,158 ทุกตัวได้แถว feature |
| Issues | error 0 / warning 13 (tool ที่โมเดลแต่งชื่อเอง) / info 1,136 |
| ตรวจกับ `validation_report.json` ของ P2 | จำนวน error แต่ละชนิด (187/13/2/13), tool call (4,476) และ agent_final (1,154) ตรงกันทุกตัว |
| ไม่มี `agent_final` | 4 trajectories (ใช้ครบ 15 steps) ตามที่ P2 แจ้ง ถือว่าปกติและถูกต้อง |
| Primary features ที่คงที่ในชุดนี้ | `n_calls_without_result`, `n_unparseable_args` |

## 3. สิ่งที่ P4 ต้องรู้

1. **คีย์คือ `trajectory_id` เท่านั้น** ให้ join กับ label ของ P1 แบบ 1:1 และรายงานแถวที่จับคู่ไม่ได้
2. **ทุกคอลัมน์ใน `features.csv` (ยกเว้น `trajectory_id`) คือ primary feature** ส่วน `suite` อยู่ใน `trajectory_index.csv` ห้ามใช้เป็น feature
3. **P3 ไม่ได้ fit อะไรกับข้อมูลทั้งชุด** scaling, imputation, feature selection และ PCA ต้อง fit จาก training set เท่านั้น ส่วน feature ที่คงที่ให้ตัดภายใน fold
4. **ไม่มี `features_extended.csv`** เพราะข้อมูล blinded ไม่มีข้อความและเวลา
5. **อย่ารวมกับ features ของ pilot** pilot ใช้ schema 1.0 ซึ่งชื่อคอลัมน์บางตัวต่างกัน

## 4. เปลี่ยนอะไรจาก v1.1 ที่ส่งไปก่อนหน้า

ได้จากการรีวิวโค้ด รายละเอียดอยู่ใน `feature_schema_v1.2.md` ข้อ 1

- **`n_retry_after_error` แก้แล้ว:** เดิมนับ call ที่ส่งพร้อมกันใน turn เดียวกันเป็น "retry" ด้วย ทั้งที่ call นั้นออกไปก่อนโมเดลจะเห็น error ค่าเปลี่ยนใน **9 จาก 1,158 trajectories**
- **`action_entropy`:** ไม่เขียนค่าเป็น `-0.0` อีก ค่าตัวเลขเท่าเดิม
- **feature อีก 75 ตัว:** ตรงกับ v1.1 ทุก byte
- **ส่วนอื่นที่แก้:** ความทนทานต่อ record ที่เสีย, การกรอง event `actor=runner`, การแยก raw กับ blinded, การเขียนไฟล์ output, การ escape สูตรใน CSV และ freeze ที่ตอนนี้ครอบคลุมโค้ดที่คำนวณ feature ด้วย ข้อเหล่านี้ไม่เปลี่ยนค่าใดๆ ในชุดนี้

## 5. ขอให้ P1 ช่วย

1. **อนุมัติ** P2 candidate package และ feature schema 1.2
2. **ยืนยัน hash ของ zip ของ P2:** P3 ได้ไฟล์ที่แตกแล้ว จึงตรวจ zip SHA-256 `4C107981…0BDC` ไม่ได้ hash ของ `trajectories_sanitized.jsonl` ที่ใช้คือ `50f29859…d807`
3. **ส่ง label ของ candidate set ให้ P4** โดยใช้ `trajectory_id` ชุดเดียวกัน
