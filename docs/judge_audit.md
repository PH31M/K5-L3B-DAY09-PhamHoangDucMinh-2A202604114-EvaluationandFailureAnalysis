# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

FAIL là lớp dương (judge có nhiệm vụ *tìm* lỗi). Ma trận nhầm lẫn viết theo thứ tự `tp / fp / fn / tn` với `human` là chuẩn.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | **Đạt** cả 3 (tp 24 · fp 4 · fn 6 · tn 66) | **dùng** (sau khi sửa rubric, xem dưới) |
| helpful | 100 | 0.375 | 1.000 | 0.300 | **Không đạt**: κ và recall dưới sàn (tp 9 · fp 0 · fn 21 · tn 70) | **loại** khỏi gate |

Tỉ lệ FAIL sau hiệu chỉnh Rogan-Gladen (dùng recall làm sensitivity, tn/(tn+fp) làm specificity):

| Tiêu chí | Judge báo | Sau hiệu chỉnh | Ý nghĩa |
|---|---|---|---|
| tone_ok | 0.28 | 0.30 | Judge gần như trung thực về tỉ lệ lỗi. |
| helpful | 0.09 | 0.30 | Judge **đánh giá thấp lỗi ~3 lần**: nhìn vào chỉ thấy 9% lỗi trong khi thực tế 30%. |

## ≥5 case audit thủ công
Toàn bộ 10 bất đồng của `tone_ok` (CSV chỉ có reply và ghi chú, không có ticket gốc nên "ai đúng" dựa trên ghi chú và rubric hiện hành).

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú và hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha, anh check giúp em." | PASS | FAIL | Người | Xưng "em/anh" và "nha" quá suồng sã; judge nhầm "thân thiện" với "đúng giọng CSKH". **Sửa rubric:** thêm mục "Xưng hô và từ đệm": chỉ dùng "Dạ … ạ" với "LogiX/anh/chị"; cấm "nha/nhé", "em–anh". |
| 2 | H-017 "Dạ, bạn ơi LogiX đã hoàn 25.000đ … rồi nha." | PASS | FAIL | Người | Xưng "bạn" với khách lớn tuổi. **Sửa rubric:** gộp vào mục xưng hô ở trên, thêm ví dụ FAIL "bạn ơi". |
| 3 | H-029 "Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm." | PASS | FAIL | Người | Giọng ra lệnh ("không cần nhắn thêm"); judge chỉ bắt chữ "Dạ, vui lòng". **Sửa rubric:** thêm "không dùng câu mệnh lệnh phủ định với khách" và cho judge xét cả câu, không chỉ phần mở đầu. |
| 4 | H-042 "Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người | Ngắn nhưng đủ ý; judge phạt vì "thiếu xin lỗi". **Sửa rubric:** ghi rõ "lời xin lỗi chỉ bắt buộc khi có sự cố hoặc từ chối, không bắt buộc khi hoàn tiền thành công". |
| 5 | H-051 "Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ." | FAIL | PASS | Người | "refund" là thuật ngữ CSKH LogiX cho phép; judge phạt vì tiếng Anh. **Sửa rubric:** thêm danh sách từ cho phép (refund, ship, ticket). |
| 6 | H-063 "Dạ, LogiX đã hoàn 20.000đ và sẽ hoàn thêm cho anh/chị ạ." | PASS | FAIL | **Judge** (đúng về tiêu chí tone) | Giọng điệu lịch sự; lỗi thật là **hứa "sẽ hoàn thêm" ngoài kết quả hệ thống**, đó là lỗi sự thật, không phải tone. Người gộp hai tiêu chí vào một nhãn. **Sửa rubric/quy trình:** tách tiêu chí; lời hứa vượt kết quả hệ thống và số tiền do code chấm (FM-08, `reply_matches_ledger`), không để judge tone gánh. |
| 7 | H-070 "… hoàn 90.000đ cho đơn O-909 ạ 😂😂" | PASS | FAIL | Người | Emoji cười trong ngữ cảnh khiếu nại là thiếu tôn trọng. **Sửa rubric:** thêm "không emoji/ký hiệu cảm xúc trong phản hồi khiếu nại". |
| 8 | H-081 "Dạ, đơn O-107 chưa đủ điều kiện hoàn theo chính sách hiện hành ạ." | FAIL | PASS | **Chưa xác minh được**; ghi chú của dữ liệu nói "nhãn người sai (đọc nhầm ticket), judge đúng" | CSV không có ticket nên mình không kiểm lại được; câu này nhìn riêng thì lịch sự. **Hành động:** thêm cột ticket vào CSV, cho người thứ hai gán lại nhãn, rồi mới kết luận. Đây là bằng chứng rằng nhãn người cũng có thể sai và cần đối soát hai người. |
| 9 | H-088 "Dạ, dạ, LogiX đã hoàn 40.000đ cho đơn O-233 ạ." | FAIL | PASS | Người (về tone) | Lặp "Dạ" là lỗi gõ, không làm đổi giọng điệu; judge quá khắt khe. **Sửa rubric:** "lỗi gõ/lặp từ thuộc tiêu chí chính tả, không tính vào tone_ok". |
| 10 | H-094 "Da, LogiX da hoan 40.000đ cho don O-341, xin loi vi su bat tien." | PASS | FAIL | Người | Dịch máy, mất dấu tiếng Việt; judge bỏ sót vì nội dung có xin lỗi. **Sửa rubric:** thêm "phải viết tiếng Việt có dấu đầy đủ", kèm ví dụ FAIL không dấu. |

Nhận xét: trong 6 ca judge bỏ sót (false negative) có 5 ca là lỗi xưng hô/giọng điệu mà rubric hiện chưa liệt kê cụ thể; trong 4 ca judge phạt oan (false positive) có 3 ca là rubric thiếu ngoại lệ (xin lỗi không bắt buộc, từ "refund", lỗi gõ). Sửa rubric theo hai nhóm trên là hành động có tác dụng nhất.

## Vì sao `helpful` không được dùng làm gate
- **Recall 0.30, κ 0.375**: trong 30 trường hợp người đánh dấu FAIL, judge chỉ bắt 9 và bỏ lọt **21** (ma trận: tp 9 · fp 0 · fn 21 · tn 70). Precision 1.0 không cứu được: một judge không bao giờ báo nhầm nhưng bỏ lọt 70% lỗi sẽ cho gate xanh giả.
- **Bỏ lọt có hệ thống, không phải ngẫu nhiên:**
  - **18/21** ca là "sai tiền": reply nêu số tiền khác ledger (ví dụ HL-015 nói 55.000đ, ledger ghi 40.000đ). Judge không có ledger trong đầu vào nên không thể biết. Đây đúng là FM-08 và phải chấm bằng code (`reply_matches_ledger`), không bằng judge.
  - **13 trong 18** ca đó là reply dài, lặp lời xin lỗi (HL-016, HL-028, HL-035, …): judge bị "lịch sự và dài" đánh lừa (thiên lệch độ dài). 5 ca còn lại là reply ngắn (HL-015, HL-020, HL-062, HL-087, HL-100) vẫn lọt vì không có ledger.
  - **3/21** ca là "sai xưng hô" ("Ok bạn, đơn … xử lý rồi nhé", HL-047, HL-091, HL-097): trùng với tiêu chí `tone_ok`, nên `helpful` đang đo lẫn hai thứ.
- **Hệ quả đo lường:** judge báo 9% lỗi trong khi tỉ lệ thật sau Rogan-Gladen là 30%, nên mọi kết luận "phiên bản mới tốt hơn" dựa trên `helpful` đều lạc quan quá mức.
- **Quy tắc rút ra:** tiền và approval luôn chấm bằng code; judge chỉ dùng cho tiêu chí không có đáp án máy kiểm được (giọng điệu) và chỉ sau khi qua calibration.

## Kết luận
- **Loại `helpful`** (κ 0.375 < 0.6, recall 0.30 < 0.7; ma trận tp 9 / fp 0 / fn 21 / tn 70). Nếu muốn giữ tiêu chí này, phải viết lại rubric theo hướng "giải quyết đúng yêu cầu với dữ kiện đúng", đưa ledger vào đầu vào của judge, tách phần xưng hô sang `tone_ok`, rồi calibrate lại trên nhãn mới.
- **Giữ `tone_ok`** (κ 0.757, P 0.857, R 0.80). Điều kiện: áp dụng 8 sửa đổi rubric ở bảng trên, rồi chạy lại calibration trước khi đưa vào gate.
- **Rủi ro còn lại:**
  - Judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới (held-out) mới biết kết quả có tổng quát hay không.
  - `tone_ok` chỉ có 30 mẫu FAIL: recall 0.80 có khoảng tin cậy Wilson 95% xấp xỉ [0.63, 0.90], cận dưới nằm dưới sàn 0.7, nên "đạt" hiện nay là sát ngưỡng chứ không chắc chắn.
  - Một ca (H-081) cho thấy nhãn người cũng có thể sai; chưa có người gán nhãn thứ hai để đo độ nhất quán giữa hai người.
  - Replay không gọi model thật; hành vi judge thật có thể khác.
