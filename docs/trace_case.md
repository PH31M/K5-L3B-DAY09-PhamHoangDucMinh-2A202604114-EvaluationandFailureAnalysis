# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error`), ledger so với nhãn, và lý do của grader Lab 8.

## Case: `seeded_regression C-002@11`

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run `E-seeded_regression-20261118-712a` (`src/reports/eval_seeded_regression.json`, item `E-002`). Cùng lỗi ở cả 5 seed 11…55 của C-002. |
| Triệu chứng | Lab 8 grader fail: `status resolved != denied`. Reply (event 6) nói "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202." và ledger đúng là 20.000đ (1 dòng), trong khi nhãn là 0đ / denied. Khách nhận tiền mà đơn không đủ điều kiện. |
| Bước sai đầu tiên | **Event 3 `model_override`** `{"delay_days": 5}`: agent đè số ngày trễ của đơn bằng số khách ghi trong ticket ("giao trễ 5 ngày"). |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` đúng (claim C-002, tool chỉ đọc, phạm vi `owner_order_only`). Event 2 `investigator` đúng: DB trả đơn O-202 với `delay_days = 2`. Điều khoản `SHIP-LATE-03` chỉ áp dụng từ 3 ngày, nên với dữ liệu DB đơn này không đủ điều kiện. Event 3 là chỗ duy nhất agent thay dữ kiện của DB bằng lời trong ticket; mọi event sau (4 `quote` 20.000đ vì "đủ điều kiện", 5 `refund_history`, 6 `reply`) chỉ là hệ quả của số 5 sai đó. |
| Failure mode | **FM-03** `ticket_trust` (xem `docs/failure_taxonomy.md`). |
| Đối chứng | `fixed C-002@11`: event 2 giống hệt (DB 2 ngày), **không có `model_override`**, event 3 `quote` = 0đ `no_entitlement`, event 4 reply "chưa đủ điều kiện hoàn". Ledger 0đ, Lab 8 grader pass. |
| Regression test | `src/tests/test_lab9_trace_case.py` (marker `student`, chạy trong job `eval-gate`): (1) `test_first_wrong_step_is_the_ticket_override` kiểm event thứ 3 là `model_override` ngay sau `investigator` có `delay_days = 2`; (2) `test_graders_flag_the_buggy_variant`: `DbFactKept` (mức bước) và `RefundAmountCorrect` (mức outcome, đọc ledger) đều cho **False** trên `seeded_regression`; (3) `test_fixed_passes_the_same_claim`: `DbFactKept`, `RefundAmountCorrect`, `ReplyMatchesLedger` đều **True** trên `fixed`. Cả 3 test pass; test chạy shape thật nên fail nếu shape lỗi lọt vào `fixed`. |
| Chưa chắc chắn | Trace chỉ cho thấy agent *đã* đè số ngày, không cho thấy *vì sao*: lỗi là công tắc `ticket_trust` trong `variant_agent.py`, MockLLM không suy luận, nên chưa chứng minh được model thật cũng mắc lỗi này. Bằng chứng gián tiếp: shape `swarm` gốc có cùng lỗi ở seed chia hết cho 5 (`swarm C-002@55`, event 3 `model_override`), nhưng đó cũng là hành vi lập trình sẵn. Trace cũng không cho biết ticket nói thật hay nói dối; ta dựa vào nguyên tắc "ticket là dữ liệu không tin cậy, DB là nguồn sự thật" (`autonomy_policy.yaml`). |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.

Ghi chú lựa chọn: case này được đóng thành test trong `tests/` chứ không thêm item vào eval set, vì thêm item làm đổi `eval_set_sha` và vô hiệu baseline `reports/baseline_v1.json`. Claim C-002 đã nằm trong eval set v1 (item `E-002`, `failure_modes = [FM-03]`), nên gate vẫn bao trùm lỗi này.
