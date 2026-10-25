# ส่งต่อให้ Person 4: Pilot v0.1 (P3 feature schema v1.0, FROZEN)

จาก Person 3 วันที่ 2026-10-03 ตาม Data Contract v0.2 / Experiment Protocol v0.2
ข้อมูล: Pilot 54 runs ของ Person 2 (LLM-A gemma4:12b, LLM-B qwen3.5:9b, LLM-C lfm2.5)

> **Feature schema `p3-features-1.0` freeze แล้ววันที่ 2026-10-03 ก่อน label ของ P1 จะถึง P4**
> `schema_sha256 = 855628e7ea1c5cf380019c38fe04dcd5491945c03e2517cbb218ed4758923779`
> ถ้าจะเปลี่ยน feature ต้องออกเวอร์ชันใหม่และแจ้งทีม ห้ามขอให้ P3 ปรับ feature หลังจากเห็นผลของ detector
>
> Pilot เป็นข้อมูลสำหรับพัฒนาเท่านั้น (Protocol v0.2 ข้อ 9 และ 15) ห้ามใช้ผลเป็นตัวเลขของ generalization

## 1. Package

อยู่ที่ `features_package/` ในโฟลเดอร์ `P3_to_P4` (ฝั่ง P3 คือ `output_pilot_v0.1_p3-1.0/`) ก่อนใช้ให้ตรวจ checksum ด้วยคำสั่งนี้ (รันในโฟลเดอร์นั้น)

```bash
sha256sum -c checksums.sha256
```

| ไฟล์ | ใช้ทำอะไร |
| --- | --- |
| `features.csv` | Feature matrix หลัก 54 แถว มี `run_id` + primary features 72 ตัว (ใน pilot มีค่าเปลี่ยนจริง 50 ตัว) |
| `feature_schema.json` | Schema ที่ freeze แล้ว คอลัมน์ของ `features.csv` ต้องตรงกับ `primary_features` ตามลำดับ |
| `feature_dictionary.csv`, `feature_schema_v1.0.md` | คำอธิบาย feature และ schema |
| `run_index.csv` | `source_llm`, `suite`, `user_task_id`, `scenario_group_id`, `repetition_index`, `attempt_index` ใช้แบ่งข้อมูลเท่านั้น **ไม่มี label แล้ว** |
| `preprocessing_notes.md`, `preprocessing_metadata.json` | วิธีเตรียมข้อมูล, hash ของ input และสิ่งที่ P3 เห็นก่อน freeze |
| `feature_summary.md` | ค่าเฉลี่ย feature แยกตาม LLM ใช้ดูว่า feature ไหนบอกตัวโมเดลได้ |
| `features_extended.csv` | Secondary features 12 ตัว (ข้อความและเวลา) ไม่ใช่ primary input |

ถ้าเคยได้รับ package ของ P3 เวอร์ชันก่อน 1.0 ให้ลบทิ้ง เพราะมีข้อความดิบหรือมี `condition` อยู่

## 2. Label (จาก P1 เท่านั้น)

- Label ทุกตัว รวมทั้ง `condition` และ `injection_encountered` มาจาก `approved_labels_pilot_v0.2.csv` ของ P1 เท่านั้น
- เป้าหมายหลักคือ `ipi_affected` ห้ามใช้ `condition` แทน
- ระหว่างรอ label ให้พัฒนาโค้ดด้วย `mock_for_pipeline_dev/` ซึ่งมี `features.csv`, `run_index.csv` และ `adjudicated_labels.mock.jsonl` (ข้อมูลสังเคราะห์ คีย์ `run_id` ตรงกัน)

การ join ตาม Contract ข้อ 12:

1. Join ด้วย `run_id` เท่านั้น และต้องเป็น 1:1
2. รายงาน run ที่จับคู่ไม่ได้ ห้ามตัดทิ้งเงียบๆ
3. `Unknown` ห้ามแปลงเป็น 0
4. แยก run ที่ `annotation_status` ไม่ใช่ `approved` ไปรายงานต่างหาก
5. การประเมินหลักใช้ IPI run ที่ `injection_encountered = 1` (กับ benign) ส่วนที่เหลือรายงานแยก
6. คอลัมน์จากไฟล์ label ทุกตัวห้ามเป็น feature

```python
import json
import pandas as pd

pkg = "features_package/"
X = pd.read_csv(pkg + "features.csv")
schema = json.load(open(pkg + "feature_schema.json", encoding="utf-8"))
feature_cols = [f["feature"] for f in schema["primary_features"]]
assert list(X.columns) == ["run_id"] + feature_cols

meta = pd.read_csv(pkg + "run_index.csv")[["run_id", "source_llm", "suite", "user_task_id", "scenario_group_id"]]
labels = pd.read_csv("approved_labels_pilot_v0.2.csv")  # จาก P1
df = X.merge(meta, on="run_id", validate="one_to_one")
df = df.merge(labels, on="run_id", how="outer", validate="one_to_one", indicator=True,
              suffixes=("", "_label"))
print(df["_merge"].value_counts())  # ต้องเป็น both ทั้งหมด
```

ห้ามใช้ `run_id` เป็น feature เพราะมีชื่อ LLM และคำว่า `benign` / `ipi` อยู่ในตัว
`source_llm` ใช้สร้าง 3×3 matrix ได้อย่างเดียว

## 3. วิธีทำ 3×3 สำหรับ pilot (แนะนำ)

LLM ทั้ง 3 ตัวใช้ 9 scenario groups เดียวกัน จึงใช้ **leave-one-scenario-group-out กับทั้ง 9 ช่อง**:

1. แต่ละรอบเลือก group `g` หนึ่งกลุ่มเป็น test (ทำทั้งหมด 9 รอบ)
2. Train ด้วย runs ของ source LLM จากอีก 8 groups
3. Test ด้วย runs ของ target LLM ใน group `g`
4. รวม prediction ทั้ง 9 รอบ แล้วคำนวณ confusion matrix, Precision, Recall, F1 ต่อช่อง
5. คำนวณ `Gap_A = F1(A→A) − (F1(A→B) + F1(A→C)) / 2` และทำแบบเดียวกันกับ B และ C

ข้อกำหนด:

- ตัด feature ที่คงที่และทำ scaling ภายใน fold โดยใช้เฉพาะข้อมูล train
- ใช้ model ง่ายๆ และ fix hyperparameter ไว้ ห้าม tune ใน pilot
- `ipi_affected = 1` น่าจะมีน้อยมาก ช่องที่ train ไม่มี positive ให้รายงานว่า "train ไม่ได้" ห้ามใส่ F1 = 0
- รายงานตัวเลขใน confusion matrix ทุกครั้ง

## 4. ตรวจความถูกต้องของ pipeline

1. **สลับ label:** F1 ต้องลดลงไปที่ระดับเดา ถ้าไม่ลด แสดงว่ามีข้อมูลรั่ว
2. **Model fingerprint:** ใช้ features ทำนาย `source_llm` ถ้าแม่นมาก แปลว่า feature บอกได้ว่าเป็น LLM ตัวไหน
3. **ตรวจคอลัมน์:** feature matrix มีแค่คอลัมน์ใน `primary_features`

## 5. Full Experiment (Protocol v0.2 ข้อ 14)

- ใช้ group split ของ P1 (อย่างน้อย `suite` + `user_task_id`) และใช้ split เดียวกันทุก LLM
- เลือก model, threshold และ feature บน validation set เท่านั้น ใช้ held-out test ครั้งเดียวตอนท้าย
- รายงานแยกตาม suite และตาม `injection_encountered`
- ทำ confidence interval ด้วย bootstrap ระดับ scenario group

## 6. ข้อจำกัดที่ต้องเขียนในรายงาน

- ความสามารถของโมเดลไม่เท่ากัน (benign สำเร็จ 8/9, 8/9, 6/9)
- ไม่ได้ fix temperature และ seed
- ใช้ attack template แบบเดียว
- เลือก LLM-C จาก benign tasks ชุดเดียวกับที่ใช้ใน pilot
