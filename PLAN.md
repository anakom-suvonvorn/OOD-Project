# แผนงานโปรเจกต์ Distributed Hilbert's Hotel (PLAN.md)

> **อ่านไฟล์นี้ให้จบก่อนเริ่มเขียนโค้ด**
> ทุกอย่างที่ "ตกลงกันแล้ว" อยู่ในไฟล์นี้: โจทย์คืออะไร, design ที่เลือก, ใครทำอะไร, timeline, โครงสร้างไฟล์, ชื่อ method / parameter / return / error, tests, การทดลอง, โครงรายงาน
> ถ้าต้องการ **เปลี่ยน contract** (ชื่อ method, parameter, return type, error, รูปแบบข้อมูล) → คุยในกลุ่มก่อน แล้วแก้ไฟล์นี้ใน PR เดียวกับโค้ด

## สารบัญ

1. [โจทย์คืออะไร](#1-โจทย์คืออะไร-the-problem)
2. [แนวคิดหลักที่ต้องเข้าใจ](#2-แนวคิดหลักที่ต้องเข้าใจ-core-concepts)
3. [Design ที่เลือกและเหตุผล](#3-design-ที่เลือก-bucket-per-ring-point-และเหตุผล)
4. [บทบาท P1–P5](#4-บทบาท-roles-p1p5)
5. [Timeline และใครรอใคร](#5-timeline-และใครรอใคร)
6. [โครงสร้างไฟล์](#6-โครงสร้างไฟล์-folder-structure)
7. [Conventions](#7-conventions-ข้อตกลงการเขียนโค้ดและ-git)
8. [API contract](#8-api-contract)
9. [Algorithm เพิ่ม/ลบอาคาร](#9-algorithm-เพิ่มลบอาคาร-p3)
10. [Tests](#10-tests-ที่ต้องมี)
11. [การทดลอง](#11-การทดลอง-experiments-p4)
12. [โครงรายงาน](#12-โครงรายงาน-google-docs--word--pdf)
13. [การนำเสนอ](#13-การนำเสนอ)
14. [Checklist ก่อนส่ง](#14-checklist-ก่อนส่ง)

---

## 1. โจทย์คืออะไร (The problem)

เขียนโปรแกรม Python จัดแขกเข้า **เครือโรงแรม** ที่มีหลายอาคาร (building = node) แต่ละอาคารมีห้องไม่จำกัด

แขกแต่ละคนมีรหัส **`(c, s)`**
- `c` = **channel** ช่องทางที่แขกมา (1, 2, 3, ...)
- `s` = **sequence** ลำดับของแขกในช่องทางนั้น เริ่มที่ 1

จากรหัสนี้ โปรแกรมต้อง **คำนวณ** (ไม่ใช่สุ่ม ไม่ใช่ "ห้องล่าสุด + 1") คำตอบ 2 อย่าง:

| คำถาม | คำนวณยังไง | เปลี่ยนเมื่อไหร่ |
|---|---|---|
| **room_no** อยู่ห้องเลขอะไร | สูตร Cantor pairing จาก `(c, s)` อย่างเดียว | **ไม่เคยเปลี่ยน** |
| **node_id** อยู่อาคารไหน | Consistent hashing ring | เปลี่ยนได้เฉพาะตอนเพิ่ม/ลบอาคาร |

**เป้าหมายหลักของโจทย์:** เมื่อเพิ่มหรือลบอาคาร ต้องมีแขกย้ายอาคาร **น้อยที่สุด** (ประมาณ K/N คน)
ถ้าใช้วิธีง่าย `hash(guest) mod N` พอ N เปลี่ยน แขก **เกือบทุกคน** ต้องย้าย → เราต้องพิสูจน์ด้วยการทดลองว่า consistent hashing ดีกว่า

**สิ่งที่ต้องส่ง** (ZIP เดียวผ่าน MS Teams):
1. โค้ด Python ทั้งหมด + สคริปต์ทดสอบอัตโนมัติ + README
2. รายงาน Word + PDF (เนื้อหาเหมือนกัน)
3. CSV: ข้อมูลแขกตัวอย่าง, รายการย้าย, ผลการทดลอง (พร้อม parameter และ salt)
4. ตารางหน้าที่สมาชิก + % การทำงาน + ลายเซ็น (ใส่ในรายงาน)

**คะแนน 30:** ความถูกต้อง+tests 9 · โครงสร้างข้อมูล+OOP 6 · Big-O 5 · การทดลอง 5 · รายงาน+สาธิต 5
⚠️ **คะแนนเป็นรายคน** ตามหลักฐานที่แต่ละคนทำ และทุกคนต้องเขียนโค้ด + เทสต์ + อธิบายงานตัวเองได้

---

## 2. แนวคิดหลักที่ต้องเข้าใจ (Core concepts)

### 2.1 Room number — Cantor pairing

ให้ `a = c − 1`, `b = s − 1`:

```
room_no = ((a + b) * (a + b + 1)) // 2 + b + 1        # integer เท่านั้น ห้ามใช้ float
```

| (c, s) | (1,1) | (2,1) | (1,2) | (3,1) | (2,2) |
|---|---|---|---|---|---|
| room_no | 1 | 2 | 3 | 4 | 5 |

สูตรนี้ไล่เลขตาม "เส้นทแยง" ของตาราง c × s → รหัสต่างกัน **ได้เลขห้องต่างกันเสมอ** และย้อนกลับได้ (room_no → (c, s))
เพราะเลขห้องไม่ขึ้นกับคนอื่น แขกใหม่จึงไม่มีทางไปกระทบห้องของแขกเดิม และเวลาย้ายอาคาร room_no ก็ยังเหมือนเดิม

### 2.2 Hash ring

- ring คือตำแหน่งจำนวนเต็ม `0 … 2^64 − 1` ที่วนเป็นวงกลม
- ทั้ง **อาคาร** และ **แขก** ถูกวางบน ring ตามค่า hash ของตัวเอง
- กติกา: แขกอยู่อาคารของ **จุดแรกที่ตำแหน่ง ≥ ตำแหน่งแขก** (เดินตามเข็มนาฬิกา) ถ้าไม่มีเลย → **วนกลับไปจุดแรกของ ring**
- ถ้าหลายจุดอยู่ตำแหน่งเดียวกัน → เรียงด้วย key `(pos, node_id, j)` แล้วใช้จุดแรก

### 2.3 ข้อความที่เอาไป hash (`guest:c:s` และ `node:node_id:j`)

ก่อนจะวางอะไรบน ring ต้องแปลงเป็น **ข้อความ (string)** ก่อน แล้วค่อย hash ข้อความนั้นเป็นตัวเลข 64 bit
รูปแบบข้อความนี้ **เรากำหนดเอง** ตามที่ PDF ข้อ 4.3 ข้อ 2 แนะนำ:

| สิ่งที่วาง | ข้อความ | ตัวอย่าง |
|---|---|---|
| แขก `(c, s)` | `guest:{c}:{s}` | แขก (1, 2) → `"guest:1:2"` |
| virtual node ที่ `j` ของอาคาร `node_id` (j = 0 … V−1) | `node:{node_id}:{j}` | อาคาร 3, V = 4 → `"node:3:0"`, `"node:3:1"`, `"node:3:2"`, `"node:3:3"` |
| มี salt (ใช้ตอนทดลอง) | `{salt}\|` นำหน้า | salt `"1"` → `"1\|guest:1:2"`, `"1\|node:3:0"` |

- **ทำไมต้องมี `guest:` / `node:` นำหน้า?** ถ้าไม่มี ข้อความ `"1:2"` จะเป็นได้ทั้งแขก (1, 2) และ vnode ที่ 2 ของอาคาร 1 → hash ออกมาตำแหน่งเดียวกันเป๊ะ
- **ทำไมต้องมี j?** อาคารหนึ่งมี V จุด แต่ละจุดต้องมีข้อความไม่ซ้ำกันถึงจะได้ตำแหน่งต่างกัน
- **salt คืออะไร?** ข้อความสั้น ๆ ที่เติมหน้า เพื่อให้ได้ตำแหน่งชุดใหม่ทั้งหมด ทั้งที่แขกและอาคารยังเป็นชุดเดิม → ใช้ทดลองซ้ำ 3 รอบ (salt `"0"`, `"1"`, `"2"`) โหมดปกติไม่มี salt

**hash64(text):** `SHA-256(text.encode("utf-8"))` → เอา **8 byte แรก** → `int.from_bytes(..., "big")` → ได้ค่า 0 … 2^64 − 1
❌ **ห้ามใช้ `hash()` ของ Python** เพราะค่าเปลี่ยนทุกครั้งที่เปิดโปรแกรมใหม่

### 2.4 Virtual nodes (V)

ถ้าอาคารหนึ่งมีจุดเดียวบน ring ช่วงที่แต่ละอาคารรับผิดชอบจะยาวไม่เท่ากันมาก → โหลดเบ้
แก้โดยให้อาคารละ **V จุด** กระจายทั่ว ring → ยิ่ง V มาก ยิ่งสมดุล (CV ต่ำ) แต่ ring ใหญ่ขึ้น (M = N × V จุด)

### 2.5 ตัวอย่าง ring เล็ก (PDF ข้อ 9.1) — ใช้เป็น test

ring ขนาด 100, V = 1, A=20, B=50, C=80 (ในโค้ดใช้ node_id 1, 2, 3 และ D = 4)

| ตำแหน่งแขก | เริ่มต้น A B C | เพิ่ม D ที่ 35 | ลบ B (จากสถานะเริ่มต้น) |
|---|---|---|---|
| 10 | A | A | A |
| 20 | A | A | A |
| 25 | B | **D** | **C** |
| 35 | B | **D** | **C** |
| 50 | B | B | **C** |
| 70 | C | C | C |
| 90 | A (วนกลับ) | A | A |

เพิ่ม D → ย้าย 2 คน (เข้า D เท่านั้น) · ลบ B → ย้าย 3 คน (เฉพาะแขกของ B) · room_no ของทุกคนไม่เปลี่ยน

---

## 3. Design ที่เลือก: bucket per ring point และเหตุผล

### 3.1 แนวคิด

- **ring** = sorted Python `list` ของ `RingPoint(pos, node_id, j)` → หาเจ้าของด้วย `bisect` O(log M)
- **ทุกจุดบน ring มี "bucket"** = set ของแขกที่จุดนั้นเป็นเจ้าของ
- **เพิ่มอาคาร:** จุดใหม่แต่ละจุดจะ "แย่ง" แขกจาก bucket ของ **จุดเก่าถัดไปทางตามเข็ม** เท่านั้น → ไม่ต้องตรวจแขกทั้ง K คน
- **ลบอาคาร:** แขกใน bucket ของแต่ละจุดที่ลบ ย้ายไปจุดถัดไปที่ยังอยู่ → ไม่ต้องค้นหาเลยว่าใครได้รับผลกระทบ
- นี่คือ **แบบ ข** ใน PDF ข้อ 4.7 (หาเฉพาะช่วงที่ได้รับผลกระทบ)

### 3.2 โครงสร้างข้อมูลทั้งหมด

| โครงสร้าง | ชนิด | เก็บอะไร | ใช้ทำอะไร | Owner |
|---|---|---|---|---|
| `HashRing._points` | `list[RingPoint]` sorted | ทุกจุด (M จุด) | หาเจ้าของ O(log M) | P1 |
| `HashRing._points_by_node` | `dict[node_id, list[RingPoint]]` | จุดของแต่ละอาคาร | รู้ว่าต้องลบจุดไหน | P1 |
| `Guest.pos` | `int` | ตำแหน่ง hash ของแขก | hash ครั้งเดียวตอนสร้าง ไม่คำนวณซ้ำ | P2 |
| `GuestStore.guests` | `dict[(c,s), Guest]` | แขกทุกคน | ค้นด้วยรหัส O(1) | P2 |
| `GuestStore.room_index` | `dict[(node_id, room_no), (c,s)]` | reverse index | ค้นด้วยที่อยู่ห้อง O(1) | P2 |
| `GuestStore.buckets` | `dict[RingPoint, set[(c,s)]]` | แขกของแต่ละจุด | เพิ่ม/ลบอาคารแตะเฉพาะแขกที่เกี่ยว | P2 (สร้าง), P3 (ใช้) |
| `GuestStore.node_counts` | `dict[node_id, int]` | จำนวนแขกต่ออาคาร | load stats O(N) | P2 |

**กฎความสอดคล้อง (consistency rule):** 4 โครงสร้างใน `GuestStore` ถูกแก้ผ่าน `place()` / `unplace()` / `move()` **เท่านั้น** ไม่มีใครแก้ dict ตรง ๆ → ข้อมูลไม่มีทางขัดกัน และ `verify_integrity()` ตรวจได้ทุกเมื่อ (นี่คือตัวอย่าง "ข้อมูลหลายส่วนต้องปรับให้สอดคล้องกัน" ที่รายงานต้องมี)

### 3.3 ทำไมเลือก design นี้

เราเทียบหลายแบบ (ดูรายละเอียดในรายงานส่วน design):

| แบบ | ข้อเสียหลัก |
|---|---|
| 1. sorted ring + dicts + ตรวจแขกใหม่ทุกคน (แบบ ก) | เพิ่ม/ลบอาคาร O(K log M) แม้ย้ายจริงไม่กี่คน |
| 2. + list แขกเรียงตามตำแหน่ง | เพิ่ม/ลบแขกทีละคน O(K) เพราะต้อง shift list |
| **3. bucket ต่อจุด (ที่เลือก)** | โค้ดซับซ้อนขึ้นเล็กน้อย — ไม่ช้ากว่าแบบอื่นในทุก operation |
| 4. list เดียวรวม vnode + แขก | เพิ่ม/ลบแขก O(M + K), ค้นหาต้องเดินหา vnode |
| 5. circular linked list | ใน Python ช้าและกินหน่วยความจำ ต้องมี array คู่อยู่ดี |
| 6. ไม่เก็บอะไร คำนวณสดทุกครั้ง | ค้นหา/สถิติ/เพิ่มลบอาคาร ต้องคำนวณแขกทุกคนใหม่ |

**ข้อสังเกตสำคัญ:** ring เล็กมาก (M ≤ 21 × 32 = 672 จุดในการทดลอง) แต่ K ใหญ่ถึง 100,000 → สิ่งที่มีผลต่อความเร็วจริงคือ "งานต่อแขก" ไม่ใช่งานบน ring
Design 3 ทำงานกับแขกเฉพาะที่ได้รับผลกระทบจริง → **เร็วที่สุดโดยรวม**

### 3.4 Big-O โดยสรุป (ต้องเขียนละเอียดจากโค้ดจริงในรายงาน)

m = จำนวนแขกที่ย้าย (คาดหวัง ≈ K/N), สมมติ: ขนาดรหัสคงที่ → hash/เปรียบเทียบ O(1)

| Operation | Time (expected) | Worst case |
|---|---|---|
| สร้าง ring | O(M log M) | เท่ากัน |
| จัดแขกเริ่มต้น K คน | O(K log M) | เท่ากัน |
| เพิ่มแขก 1 คน / กลุ่ม b คน | O(log M) / O(b log M) | เท่ากัน |
| นำแขกออก | O(1) | O(K) ถ้า dict ชนหนัก (ปกติไม่เกิด) |
| ค้นด้วยรหัส / ด้วยห้อง | O(1) | — |
| คำนวณอาคารสดจาก ring | O(log M) | — |
| เรียงรายการห้อง | O(K log K) | — |
| load stats | O(N) | — |
| เพิ่มอาคาร | O(M + V log M + (K/N) log M) | O(M + K log M) ถ้าแฮชเบ้ |
| ลบอาคาร | O(M + (K/N) log M) | O(M + K log M) |
| Space | O(M + K) | — |

---

## 4. บทบาท (Roles) P1–P5

แต่ละคน **เป็นเจ้าของส่วนของตัวเองตั้งแต่ต้นจนจบ:** โค้ด + tests + ส่วนในรายงาน + Big-O ของส่วนนั้น + พูดส่วนนั้นตอนนำเสนอ
**Cross-review:** แต่ละคนรีวิว PR และรัน tests ของอีกคน: P1 → P2 → P3 → P4 → P5 → P1 (P1 รีวิวงาน P2, P2 รีวิว P3, …, P5 รีวิว P1) **----- note จาก anakom: no need to ทำตามนี้ก็ได้ เดียวมันยาก/มั่วเกินๆ เอาเป็นว่า review/test ส่วนของตัวเองให้ดีๆ ละกันๆ -----**

| Role | ชื่อ | ไฟล์ที่เป็นเจ้าของ | งานโค้ด | Tests | รายงาน |
|---|---|---|---|---|---|
| **P1 Ring** | _____ | `hotel/hashing.py`, `hotel/ring.py`, `hotel/mod_n.py`, `tests/test_ring.py`, `tests/test_mod_n.py` | hash64, HashRing (build, add/remove node, lookup, ties, wrap-around, successor), ModNRouter | ring 9.1, ties, wrap, hash เหมือนเดิมทุก run, add/remove ไม่เปลี่ยนจุดเดิม, mod N | hashing + ring design, Big-O ของ ring, **ตาราง hash mod N vs consistent hashing (PDF 8.2)** |
| **P2 Guests** | _____ | `hotel/guest.py`, `hotel/guest_store.py`, ส่วน guest ใน `hotel/hotel_system.py`, `tests/test_guest.py`, `tests/test_hotel_guests.py` | room_number + inverse, Guest, GuestStore, initialize, clone, add/batch/remove guest, find ทั้ง 2 ทาง, list_rooms, load_stats | ตารางเลขห้อง, ไม่ซ้ำ, เพิ่มแขกแล้วแขกเดิมไม่ย้าย, batch ซ้ำบางส่วนต้องไม่เปลี่ยนอะไร, edge cases แขก, K = 0 | room number + **พิสูจน์ความไม่ซ้ำ**, guest data structures, Big-O ข้อ 1–4 |
| **P3 Buildings** | _____ | ส่วน building ใน `hotel/hotel_system.py`, `tests/test_buildings.py` | add_building, remove_building, MoveReport, compute_node, assignments, verify_integrity, edge cases อาคาร | 9.1 ผ่าน HotelSystem, ผู้ย้ายเข้าอาคารใหม่เท่านั้น, ลบแล้วคนอื่นไม่ขยับ, จำนวนรวมไม่เปลี่ยน, count == len(moves), **bucket method == recheck-everyone** แบบสุ่มหลายรอบ | algorithm ย้ายแขก, **ตัวอย่าง consistency**, Big-O ข้อ 5 |
| **P4 Experiments** | _____ | `experiments/*`, `tests/test_experiments.py`, `results/` | measure helpers, run A/B/C × 3 salts, median/min/max, CSV ผล, กราฟ 3 รูป, benchmark_system / compare_with_mod_n ให้เมนู | salt เดิม → ผลเดิม, channel_sizes ถูก | วิธีทดลอง, ตาราง, กราฟ, **อธิบายผลที่ต่างจากค่าคาดหวัง** |
| **P5 UI & files** | _____ | `ui/*`, `main.py`, `README.md`, `tests/test_csv_menu.py` | เมนูข้อความ + ตรวจ input + ข้อความ error สุภาพ, CSV export, README, ZIP | เมนูไม่ crash กับ input แปลก ๆ, แถว CSV == จำนวนแขก, moves CSV == moved_count | class diagram, วิธีรัน, ข้อจำกัด, อ้างอิง, **รวมเล่มรายงาน + ตารางหน้าที่สมาชิก** |

Big-O ของ PDF ข้อ 8: ข้อ 1–4 → P2 (ring ส่วนสร้าง/lookup → P1), ข้อ 5 → P3 (5ก การปรับ ring → P1), ข้อ 6 space → แต่ละคนส่วนของตัวเอง รวมโดย P1

---

## 5. Timeline และใครรอใคร

> ยังไม่ประกาศวันส่ง — วันด้านล่างเป็นเป้าหมายภายในกลุ่ม ถ้าประกาศวันส่งแล้วจะปรับไฟล์นี้ **----- note จาก anakom: phase/ลำดับ ตามนี้ถูกละ แต่ไอวันที่อะ ai มันมั่วมา/รู้สึกเหมือนมันช้าเกินไป ไม่ต้องไปตามมันให้แปะๆ เนอะ เอาเป็นว่าแค่ให้รีบๆ ทำ จะได้จบๆ กันเร็วๆ ได้ไปทำอย่างอื่นกันต่อน่ะสมาชิกๆๆ (คนที่รอต่อๆ ไปจะได้ไม่ต้องไปรีบทำอยู่ตอนท้ายๆ ด้วยๆ)-----**

| Phase | ช่วง | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|---|
| **0 Kickoff** | 4–6 ต.ค. | อ่าน PLAN, เลือก role, ประชุมยืนยัน contract | ← | ← | ← | ← |
| **1 Core pieces** | 7–13 ต.ค. | **hashing + ring + tests เสร็จก่อน 10 ต.ค.** แล้วทำ mod_n | guest.py + GuestStore + tests | เขียน tests ของ building (9.1, กติกาย้าย) + ร่าง algorithm | measure.py, channel_sizes, โครงทดลองด้วยข้อมูลปลอม | เมนู + CSV โดยใช้ stub / ข้อมูลปลอม |
| **2 HotelSystem** | 14–24 ต.ค. | ช่วยรีวิว + เริ่มเขียนรายงานส่วน ring | guest methods ใน HotelSystem (เสร็จ 18 ต.ค.) | building methods (เสร็จ 22 ต.ค.) | รันทดลองรอบแรกกับโค้ดจริง, กราฟร่าง | ต่อเมนูกับ HotelSystem จริง |
| **3 Integrate & freeze** | 25 ต.ค.–1 พ.ย. | ทุกคน: แก้บั๊ก, tests เขียวทั้งหมด, **code freeze 1 พ.ย.** | ← | ← | รันทดลองรอบจริงหลัง freeze | README, export ตัวอย่าง |
| **4 Report & present** | 2–8 พ.ย. | ทุกคน: Big-O จากโค้ดจริง, ส่วนรายงานของตัวเอง, ซ้อมนำเสนอ | ← | ← | ← | รวมเล่ม Word + PDF, ZIP |

**ใครรอใคร (dependencies):**

```
P1 ring ──► P2 HotelSystem.add_guest (ต้องใช้ ring.lookup)
P1 ring ──► P3 add/remove_building (ต้องใช้ add_node / remove_node / lookup / successor)
P2 GuestStore.move ──► P3 add/remove_building
P1 + P2 + P3 ──► P4 ผลการทดลองจริง          (ก่อนหน้านั้น P4 เตรียมโค้ดวัดผลได้เลย)
P2 + P3 API (stubs) ──► P5 เมนู             (เริ่มได้ทันทีเพราะชื่อ method ตกลงแล้ว)
code freeze ──► ทุกคนเขียน Big-O + P4 รันทดลองรอบจริง
```

P1 อยู่บน critical path → ทำ ring ให้เสร็จก่อน ส่วนที่เล็กที่สุดแต่ทุกคนรอ

---

## 6. โครงสร้างไฟล์ (Folder structure)

```
project-code/
├── PLAN.md                     ← ไฟล์นี้
├── README.md                   (P5) Python version, วิธีรัน, วิธีรัน tests
├── requirements.txt            matplotlib (ใช้วาดกราฟเท่านั้น)
├── main.py                     (P5) python main.py
├── hotel/                      core logic — ห้าม print / input
│   ├── __init__.py
│   ├── errors.py               ✅ SHARED CONTRACT (เขียนเสร็จแล้ว)
│   ├── models.py               ✅ SHARED CONTRACT (เขียนเสร็จแล้ว)
│   ├── hashing.py              (P1)
│   ├── ring.py                 (P1)
│   ├── mod_n.py                (P1)
│   ├── guest.py                (P2)
│   ├── guest_store.py          (P2)
│   └── hotel_system.py         (P2 guest methods, P3 building methods)
├── ui/
│   ├── menu.py                 (P5)
│   └── csv_export.py           (P5)
├── experiments/
│   ├── measure.py              (P4)
│   ├── run_experiments.py      (P4)
│   └── plot_results.py         (P4)
├── tests/                      แต่ละคนสร้างไฟล์ test ของตัวเอง (ชื่อตาม section 4)
└── results/                    CSV ผลทดลอง + graphs/ (commit ตอนท้ายเพื่อส่ง)
```

ไฟล์ทุกไฟล์มี **stub** แล้ว: ชื่อ method, parameter, return type, error, docstring อธิบายพฤติกรรม → แค่เติม body แทน `raise NotImplementedError("Px")`

---

## 7. Conventions (ข้อตกลงการเขียนโค้ดและ git)

### 7.1 โค้ด
- **Python 3.12**
- `hotel/` ใช้ standard library เท่านั้น: `hashlib`, `bisect`, `dataclasses`, `typing` (ห้ามใช้ library consistent hashing สำเร็จรูป) — integer square root เขียนเอง
- matplotlib ใช้ได้เฉพาะ `experiments/plot_results.py`
- ตัวแปร/ฟังก์ชัน `snake_case`, class `PascalCase`, ใส่ type hints, docstring + comment เป็นภาษาอังกฤษ (ข้อความในเมนูเป็นไทยได้)
- **`hotel/` ห้าม `print()` / `input()`** → ถ้าผิดพลาดให้ `raise` error จาก `hotel/errors.py`, UI เป็นคน catch แล้วแสดงข้อความ
- ตำแหน่ง ring และเลขห้องเป็น `int` ตลอด ห้ามมี float
- **node_id เป็น `int` ≥ 1** — initialize สร้างอาคาร 1 … N, อาคารใหม่ใช้ id อะไรก็ได้ที่ยังไม่มี (เมนูเสนอ max + 1 เป็นค่าเริ่มต้น)
- c, s, room_no, V เป็น `int` ≥ 1, count ของ batch เป็น `int` ≥ 0 (`bool` ไม่นับเป็น int)
- standard deviation ใช้แบบ **population** (หารด้วย N)

### 7.2 Error → edge cases (PDF 4.5)

| กรณี | Error | ผล |
|---|---|---|
| เพิ่มอาคารที่มีอยู่แล้ว | `DuplicateNodeError` | ไม่เปลี่ยนอะไร |
| ลบอาคารที่ไม่มี | `NodeNotFoundError` | ไม่เปลี่ยนอะไร, ไม่รายงานการย้าย |
| ลบอาคารสุดท้าย | `LastNodeError` | ไม่เปลี่ยนอะไร |
| เพิ่มแขกซ้ำ (เดี่ยว/กลุ่ม) | `DuplicateGuestError` | ไม่เพิ่มใครเลย (ทั้งกลุ่ม) |
| นำแขกที่ไม่มีออก | `GuestNotFoundError` | K ไม่ลด |
| ค้นหาไม่พบ | `GuestNotFoundError` / `RoomNotFoundError` | เมนูบอก "ไม่พบ" |
| input ผิดชนิด/ช่วง | `InvalidInputError` | ไม่เปลี่ยนอะไร |
| ยังไม่มีอาคาร | `EmptyRingError` | — |
| K = 0 | ไม่ใช่ error | stats เป็น 0, `cv = None`, `move_rate = None` |

### 7.3 Git / GitHub
- **ห้าม push ตรงเข้า `main`** → ทำงานใน branch ของตัวเอง: `p1-ring`, `p2-guests`, `p3-buildings`, `p4-experiments`, `p5-ui` (แตก branch ย่อยได้)
- เปิด Pull Request → **คนรีวิวตาม cross-review** อนุมัติ + tests ผ่าน → merge **----- note จาก anakom: เหมือนที่บอกมาก่อนหน้านี้ no need to ทำตามนี้ก็ได้ๆ เดียวมันยาก/มั่วเกินๆ เอาเป็นว่า review/test ส่วนของตัวเองให้ดีๆ ละกันๆ แล้วถ้า test อะไรผ่านหมดแล้วก็ merge pull request เข้า main ได้เลยๆ -----**
- `git pull origin main` บ่อย ๆ, commit เล็ก ๆ, ข้อความ commit ขึ้นต้นด้วย role เช่น `[P1] implement HashRing.lookup`
- ห้ามแก้ไฟล์ของคนอื่นโดยไม่บอก, ห้าม force-push `main`
- **รัน tests ทั้งหมดก่อนเปิด PR ทุกครั้ง**

---

## 8. API contract

ดู docstring เต็มในไฟล์ stub — ด้านล่างคือสรุป

### 8.1 `hotel/models.py` ✅
- `GuestId = tuple[int, int]`
- `RingPoint(pos, node_id, j)` — NamedTuple, sort ได้ตาม key ที่ PDF กำหนด, ใช้เป็น dict key ได้
- `Move(c, s, old_node, new_node, room_no)`
- `MoveReport(action, node_id, total_guests, moves)` + `.moved_count`, `.move_rate` (None ถ้า K = 0)
- `LoadStats(counts, total, maximum, minimum, mean, std, cv)`

### 8.2 `hotel/hashing.py` (P1)
- `RING_SIZE = 2**64`
- `guest_key(c, s, salt="") -> str` ✅, `node_key(node_id, j, salt="") -> str` ✅
- `hash64(text) -> int`

### 8.3 `hotel/ring.py` — `HashRing(V, salt="", hash_fn=None)` (P1)
| Method | Return | Raises |
|---|---|---|
| `build(node_ids)` | None | InvalidInput, DuplicateNode |
| `add_node(node_id)` | `list[RingPoint]` ที่เพิ่ม | InvalidInput, DuplicateNode |
| `remove_node(node_id)` | `list[RingPoint]` ที่ลบ | NodeNotFound, LastNode |
| `lookup(pos)` | `RingPoint` | EmptyRing |
| `node_for(pos)` | `int` | EmptyRing |
| `successor(point)` | `RingPoint` ถัดไปตามเข็ม | — |
| `has_node(id)`, `node_ids()`, `points()`, `node_count`, `len()` | | |

`hash_fn` ให้ test ส่ง function ปลอมเข้ามาเพื่อวางจุดตามตำแหน่งที่กำหนดเอง เช่น ตัวอย่าง 9.1

### 8.4 `hotel/mod_n.py` — `ModNRouter()` (P1)
`build(node_ids)`, `add_node(id)` (ต่อท้าย), `remove_node(id)` (รักษาลำดับที่เหลือ), `node_for(pos)` = `nodes[pos % N]`, `node_ids()`
ใช้ `guest.pos` ชุดเดียวกับ consistent hashing → hash ชุดเดียวกันตามที่ PDF กำหนด

### 8.5 `hotel/guest.py`, `hotel/guest_store.py` (P2)
- `validate_guest_id(c, s)`, `room_number(c, s)`, `guest_id_from_room(room_no)`
- `Guest(c, s, pos)` — `.id`, `.room_no`, `.point`, `.node_id`
- `GuestStore`: `get`, `get_by_room`, `place`, `unplace`, `move`, `guests_at`, `len`, `in`, iteration

### 8.6 `hotel/hotel_system.py` — `HotelSystem(V, salt="", hash_fn=None)`
| Method | Owner | Return | Raises |
|---|---|---|---|
| `HotelSystem.initialize(num_nodes, V, channel_sizes, salt="", hash_fn=None)` | P2 | HotelSystem | InvalidInput |
| `clone()` | P2 | HotelSystem | — |
| `add_guest(c, s)` | P2 | Guest | InvalidInput, DuplicateGuest, EmptyRing |
| `add_guests(c, s_start, count)` | P2 | list[Guest] | InvalidInput, DuplicateGuest |
| `remove_guest(c, s)` | P2 | Guest | InvalidInput, GuestNotFound |
| `find_guest(c, s)` | P2 | Guest | InvalidInput, GuestNotFound |
| `find_by_room(node_id, room_no)` | P2 | Guest | InvalidInput, RoomNotFound |
| `list_rooms()` | P2 | list[Guest] เรียง (node_id, room_no) | — |
| `load_stats()` | P2 | LoadStats | — |
| `add_building(node_id)` | P3 | MoveReport | InvalidInput, DuplicateNode |
| `remove_building(node_id)` | P3 | MoveReport | NodeNotFound, LastNode |
| `compute_node(c, s)` | P3 | int | — |
| `assignments()` | P3 | dict[(c,s), node_id] | — |
| `verify_integrity()` | P3 | None | AssertionError |
| `V`, `guest_count`, `node_ids()`, `guests()` | ✅ | | |

### 8.7 UI (P5)
เมนู: `1` สร้างระบบใหม่ (N, V, จำนวนช่องทาง, จำนวนแขกแต่ละช่องทาง) · `2` เพิ่มแขก · `3` เพิ่มเป็นกลุ่ม · `4` นำแขกออก · `5` เพิ่มอาคาร · `6` ลบอาคาร · `7` ค้นด้วยรหัสแขก · `8` ค้นด้วย (อาคาร, ห้อง) · `9` รายการห้อง · `10` รายงานโหลด · `11` วัดเวลา/หน่วยความจำ · `12` เทียบกับ hash mod N · `13` ส่งออก CSV · `0` ออก
- รายการยาวแสดง 50 แถวแรก + **บอกจำนวนทั้งหมด** (ไฟล์ CSV ต้องครบ)
- หลังเพิ่ม/ลบอาคาร แสดง: จำนวนย้าย, อัตราย้าย (หรือ "ไม่คำนวณเพราะไม่มีแขก"), รายการย้าย, และถามว่าจะ export CSV ไหม
- CSV: `export_guests` (channel_id, sequence_id, node_id, room_no), `export_moves`, `export_rows` — UTF-8

### 8.8 Experiments (P4)
`time_call`, `measure_memory`, `channel_sizes`, `run_experiment_a/b/c`, `benchmark_system(system)`, `compare_with_mod_n(system, action, node_id)` — สองตัวหลังเมนูเรียกใช้ และ **ต้องไม่แก้ system ตัวจริง** (ใช้ `clone()`)

---

## 9. Algorithm เพิ่ม/ลบอาคาร (P3)

### 9.1 `add_building(node_id)`

```
K = guest_count
new_points = ring.add_node(node_id)                 # raises ก่อนแก้อะไร ถ้า id ซ้ำ
candidates = set()
for p in new_points:
    q = ring.successor(p)
    while q.node_id == node_id:                     # ข้ามจุดใหม่ที่อยู่ติดกัน
        q = ring.successor(q)
    candidates.add(q)                               # จุดเก่าที่เคยเป็นเจ้าของช่วงนี้
moves = []
for q in candidates:
    for gid in store.guests_at(q):                  # คาดหวัง ≈ K/M คนต่อจุด → รวม ≈ K/N
        g = store.guests[gid]
        new_owner = ring.lookup(g.pos)              # คำนวณใหม่ → ถูกต้องแม้ตำแหน่งชนกัน
        if new_owner != q:                          # ต้องเป็นจุดของอาคารใหม่เท่านั้น
            old = store.move(g, new_owner)
            moves.append(Move(g.c, g.s, old, node_id, g.room_no))
return MoveReport("add", node_id, K, moves)
```

### 9.2 `remove_building(node_id)`

```
K = guest_count
removed = ring.remove_node(node_id)                 # raises ก่อนแก้อะไร ถ้าไม่มี / เป็นอาคารสุดท้าย
moves = []
for p in removed:
    for gid in store.guests_at(p):
        g = store.guests[gid]
        new_owner = ring.lookup(g.pos)              # ring ไม่มีจุดของ node_id แล้ว
        store.move(g, new_owner)
        moves.append(Move(g.c, g.s, node_id, new_owner.node_id, g.room_no))
return MoveReport("remove", node_id, K, moves)
```

ทั้งสองแบบ: ทำ validation ทั้งหมด **ก่อน** แก้ข้อมูล → ถ้า error ข้อมูลเดิมไม่เปลี่ยน
ใน tests ใช้ `assignments()` ก่อน/หลัง (= แบบ ก ตรวจทุกคน) เทียบกับ `MoveReport` → ต้องตรงกันทุกคน

---

## 10. Tests ที่ต้องมี

- ใช้ `unittest`, ไฟล์ชื่อ `tests/test_*.py`
- รันทั้งหมด: `python -m unittest discover -s tests -v` (รันจากโฟลเดอร์ `project-code/`)
- tests ต้อง **รันซ้ำได้ผลเดิม** (ใช้ salt / seed คงที่) — screenshot อย่างเดียวไม่นับเป็นหลักฐาน

| PDF 9.2 | Test | Owner |
|---|---|---|
| 1 | เพิ่มแขกช่องทางเดิมและช่องทางใหม่ → ที่อยู่แขกเดิมไม่เปลี่ยนแม้แต่คนเดียว | P2 |
| 2 | เลขห้องตามตาราง (1,1)→1 … (2,2)→5, inverse ถูก, ไม่มีที่อยู่ซ้ำ | P2 |
| 3 | ปฏิเสธรหัสซ้ำ รวม batch ที่ซ้ำบางรายการ → ข้อมูลเดิมไม่เปลี่ยน | P2 |
| 4 | lookup ตรงจุดพอดี / ระหว่างจุด / หลังจุดสุดท้าย (วนกลับ) / vnode ชนกัน (hash_fn ปลอม) | P1 |
| 5 | เพิ่ม/ลบอาคารเมื่อ V > 1: ย้ายตามกติกา, จำนวนรวมคงที่, จำนวนรายการ == ยอดรายงาน, ผลตรงกับแบบตรวจทุกคน | P3 |
| 6 | edge cases ทั้งหมดใน 7.2 + จำนวนแถว CSV == จำนวนแขก | P2 (แขก), P3 (อาคาร), P5 (CSV) |
| 9.1 | ตัวอย่าง ring ขนาด 100 ทั้งที่ระดับ HashRing (P1) และ HotelSystem (P3) | P1, P3 |
| extra | hash64 ได้ค่าเดิมทุก run (เทียบกับตัวเลขที่บันทึกไว้), `verify_integrity()` ผ่านหลังทุก operation | P1, P3 |

ตัวอย่าง hash_fn ปลอมสำหรับ 9.1 (ใช้ทั้ง P1 และ P3):

```python
POS = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80, "node:4:0": 35}
GUEST_POS = [10, 20, 25, 35, 50, 70, 90]          # แขก (1, 1) … (1, 7)
POS.update({f"guest:1:{i + 1}": p for i, p in enumerate(GUEST_POS)})
fake_hash = POS.__getitem__
system = HotelSystem.initialize(3, 1, [7], hash_fn=fake_hash)
```

---

## 11. การทดลอง (Experiments, P4)

### 11.1 ชุดการทดลอง

| | เปลี่ยน | คงที่ | วัด |
|---|---|---|---|
| **A** | K = 1,000 / 10,000 / 100,000 | N = 10, V = 32 | เวลาสร้าง ring, จัดแขก, ค้นหา (ทั้ง 2 แบบ), เรียงรายการห้อง; memory |
| **B** | N = 5 / 10 / 20 | K = 10,000, V = 32 | เพิ่ม 1 อาคาร และ ลบ 1 อาคาร: จำนวนย้าย, อัตราย้าย, เวลา — consistent hashing **และ** hash mod N |
| **C** | V = 1 / 8 / 32 | N = 10, K = 10,000 | แขกต่ออาคาร, max/min/mean/std/CV, memory, การย้าย |

### 11.2 กติกา
- แขกจาก 10 ช่องทาง กระจายเท่า ๆ กัน (`channel_sizes`), อาคาร id 1 … N
- **B:** เพิ่มอาคาร id `N + 1`, ลบอาคาร id `N // 2 + 1` (อาคารกลาง ๆ ไม่ใช่ตัวแรกหรือตัวสุดท้าย ซึ่งจะเอื้อหรือเสียเปรียบ mod N เกินจริง) — แต่ละกรณีเริ่มจากสถานะเริ่มต้นใหม่
- salt `"0"`, `"1"`, `"2"` — รอบเดียวกันใช้ salt เดียวกันทั้งสองวิธี
- เวลา: `time.perf_counter()` ไม่รวม input/แสดงผล/เขียนไฟล์; ค้นหาวัดเป็นชุด 1,000 ครั้งแล้วหารต่อครั้ง
- memory: `tracemalloc` รอบแยกจากรอบจับเวลา, รายงาน current + peak เป็น MiB (หน่วยความจำที่ Python ติดตาม ไม่ใช่ทั้ง process)
- รายงาน **median ของ 3 รอบ** + min–max
- ใช้เครื่องเดียวกันและ Python เดียวกันตลอด บันทึกสเปกเครื่อง + Python version ในรายงาน
- ถ้าเครื่องรันชุดใหญ่ไม่ไหว: เก็บหลักฐาน + รายงานขอบเขตที่ทำได้

### 11.3 รูปแบบ CSV ผลการทดลอง (long format)

`experiment, method, salt, K, N, V, metric, value, unit`

ตัวอย่าง: `B, consistent, 1, 10000, 10, 32, moved_add, 912, guests`
method = `consistent` หรือ `mod_n` · ไฟล์: `results/experiment_a.csv`, `experiment_b.csv`, `experiment_c.csv`

### 11.4 กราฟ (อย่างน้อย 3 รูป, `results/graphs/`)
(ก) เวลาเทียบ K · (ข) อัตราการย้ายเทียบ N ของทั้งสองวิธี · (ค) ผลของ V ต่อ CV และ memory
ทุกกราฟ: ชื่อแกน + หน่วย + parameter + ความแปรปรวน 3 รอบ (median + ช่วง min–max)

---

## 12. โครงรายงาน (Google Docs → Word + PDF)

เขียนร่วมกันใน Google Docs, **แต่ละคนเขียนส่วนของตัวเอง**, P5 รวมเล่มและจัดรูปแบบตอนท้าย (export เป็น .docx แล้วแก้ font/รูปแบบใน Word จากนั้น save เป็น PDF จากไฟล์ Word เดียวกัน → เนื้อหาตรงกันแน่นอน)

| # | หัวข้อ | Owner |
|---|---|---|
| 1 | บทนำ: ปัญหา Hilbert's Hotel, ทำไม mod N ไม่พอ, เป้าหมาย | P1 |
| 2 | ภาพรวมระบบ + **class diagram** + หน้าที่ของแต่ละคลาส | P5 (ทุกคนตรวจ) |
| 3 | กติกาการคำนวณ: hashing + key strings + salt (P1), room number + **พิสูจน์ความไม่ซ้ำ** (P2), การเลือกอาคาร + tie-break (P1) | P1, P2 |
| 4 | โครงสร้างข้อมูลและเหตุผล + เปรียบเทียบ design ที่พิจารณา (section 3 ของไฟล์นี้) | P1 ring, P2 guest/index, P3 buckets |
| 5 | การเพิ่ม/ลบอาคารและการย้าย + **ตัวอย่าง consistency** | P3 |
| 6 | Big-O: ข้อ 1–6 ตาม PDF ข้อ 8 แยกขั้นตอน ระบุ worst/expected + สมมติฐาน | ตาม section 4 |
| 7 | ตารางเปรียบเทียบ hash mod N vs consistent hashing (ค่าวิเคราะห์ vs ค่าวัดจริง) | P1 + P4 |
| 8 | การทดลอง: วิธีทดลอง, parameter, salt, เครื่อง, ตาราง, กราฟ, อธิบายผล | P4 |
| 9 | การทดสอบ: รายการ tests + ผลผ่าน/ไม่ผ่าน + อธิบายกรณีไม่ผ่าน | แต่ละคน, รวมโดย P5 |
| 10 | ข้อจำกัด | ทุกคน, รวมโดย P5 |
| 11 | แหล่งอ้างอิง (ที่ใช้จริง) | P5 |
| 12 | ตารางหน้าที่สมาชิก + % การทำงาน + ลายเซ็น | P5 |
| ภาคผนวก | วิธีรันโปรแกรมและ tests | P5 |

---

## 13. การนำเสนอ

- **ทุกคนพูดส่วนของตัวเอง** (คะแนนเป็นรายคน และ PDF กำหนดให้ทุกคนอธิบายงานตัวเองได้)
- ลำดับ: P1 โจทย์ + ring → P2 เลขห้อง + ข้อมูลแขก → P3 การย้าย (สาธิตเพิ่ม/ลบอาคาร) → P4 ผลทดลอง + กราฟ → P5 สาธิตเมนู + CSV + สรุป
- ทุกคนควรตอบคำถามพื้นฐานของทั้งระบบได้: ทำไมแขกเดิมไม่ย้าย, ทำไมย้ายแค่ ≈ K/N, ทำไม room_no ไม่เปลี่ยน
- รูปแบบ/เวลานำเสนอยังไม่ประกาศ — ถามอาจารย์แล้วอัปเดตตรงนี้

---

## 14. Checklist ก่อนส่ง

- [ ] เพิ่มแขกใหม่แล้ว ที่อยู่ห้องของแขกเดิมไม่เปลี่ยนแม้แต่คนเดียว
- [ ] เลขห้องคำนวณจากรหัสแขกล้วน ๆ ไม่มี "เลขล่าสุด + 1"
- [ ] เพิ่มอาคารแล้วผู้ย้ายเข้าอาคารใหม่เท่านั้น ลบอาคารแล้วแขกอาคารอื่นไม่ขยับ
- [ ] จำนวนที่รายงานว่าย้าย == จำนวนรายการย้ายที่แสดงจริง
- [ ] ปิดแล้วเปิดโปรแกรมใหม่ ค่า hash เหมือนเดิม (ไม่ใช้ `hash()`)
- [ ] edge cases ทั้งหมดไม่ทำให้โปรแกรมหยุดทำงาน
- [ ] จำนวนแถวใน CSV == จำนวนแขกในระบบ
- [ ] กราฟทุกรูปมีชื่อแกน หน่วย parameter
- [ ] Big-O ในรายงานตรงกับโค้ดที่ส่งจริง
- [ ] `python -m unittest discover -s tests -v` ผ่านทั้งหมด
- [ ] README: Python version, `python main.py`, วิธีรัน tests, วิธีรันการทดลอง
- [ ] ZIP: เปิดแล้วเจอ README ทันที, ไม่มี venv / `__pycache__`
- [ ] รายงาน Word + PDF เนื้อหาตรงกัน, มีตารางสมาชิก % + ลายเซ็น
- [ ] CSV: แขกตัวอย่าง, รายการย้าย, ผลทดลอง (มี parameter + salt)
