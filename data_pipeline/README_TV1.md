# TV1 – Dữ liệu: thu thập & chuẩn hóa toàn bộ cổ phiếu Việt Nam

Module nền tảng cung cấp dữ liệu cho TV2–TV6. Python 3.10+, Windows/VS Code.

> **Trạng thái thực tế:** code đã được viết theo API vnstock 3.x đối chiếu với tài liệu chính thức và đã qua **26 kiểm thử logic dùng dữ liệu mock** (pass).
> Môi trường phát triển **không có Internet nên CHƯA có lần chạy nào với nguồn thật**; repo **không kèm dữ liệu mẫu** để tránh nhầm với dữ liệu thật.
> Bước đầu tiên của bạn là `python run_pipeline.py --probe` (mục 3).

## 1. Cài đặt (Windows / VS Code)
```powershell
cd TV1
python -m venv .venv
.venv\Scripts\Activate.ps1          # nếu bị chặn: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
```
Nếu dùng API key của vnstock để tăng giới hạn truy cập, cấu hình theo hướng dẫn của vnstock (biến môi trường/lệnh đăng ký của họ) — **không ghi key vào code**.

## 2. Cấu trúc
| File | Vai trò |
|---|---|
| `config.py` | Nguồn, ngày mặc định (2015-01-01 → hôm nay), đường dẫn, giới hạn tốc độ/retry, ngưỡng kiểm tra |
| `data_loader.py` | Lấy danh sách mã, giá, hồ sơ DN, BCTC; **hàm đọc dữ liệu đã lưu** cho TV2–TV4 |
| `data_cleaning.py` | Chuẩn hóa, kiểm tra OHLC/trùng/âm/thiếu, phân loại cổ phiếu vs ETF/TP/CW, BCTC → dạng dài |
| `data_quality.py` | Báo cáo chất lượng + độ hoàn thành → `data/data_quality_report.json` |
| `storage.py` | CSV theo mã (ghi nguyên tử, gộp không trùng) + SQLite trạng thái |
| `run_pipeline.py` | CLI chạy toàn thị trường / cập nhật / probe |
| `tests/test_tv1.py` | 26 kiểm thử (mock) |
| `examples_integration.py` | Ví dụ cho TV2, TV3, TV4 |

Dữ liệu sinh ra trong `data/`: `symbols.csv` (cổ phiếu), `symbols_unclassified.csv` (ETF/TP/CW/chưa xác định, để rà soát), `prices/<MÃ>.csv`, `stock_prices.csv` (gộp), `company_profiles/`, `financial_statements/`, `quality/issues/<MÃ>.csv` (dòng bị loại + lý do), `collection_status.csv` + `state.sqlite` (trạng thái từng mã), `logs/`, `run_reports/`.

## 3. Chạy lần đầu: kiểm chứng API (bắt buộc)
```powershell
python run_pipeline.py --probe
```
In ra: số mã theo sàn/loại, **giá trị cột `type` thô của nguồn** (để xác nhận bước lọc cổ phiếu), cột/kiểu dữ liệu giá của FPT/VNM/ACB. Đối chiếu:
1. **Đơn vị giá**: `close` của FPT ≈ 100 hay ≈ 100.000? Nếu nguồn trả theo *nghìn đồng* và bạn muốn VND: `set TV1_PRICE_MULTIPLIER=1000` (PowerShell: `$env:TV1_PRICE_MULTIPLIER="1000"`). Mặc định giữ nguyên đơn vị nguồn.
2. **Giá có điều chỉnh không**: tài liệu không nêu rõ → đối chiếu một mã có chia cổ tức/tách cổ phiếu với bảng giá. Pipeline **không** tự tính giá điều chỉnh.
3. Nếu `unknown` quá nhiều trong phân loại, xem `symbols_unclassified.csv` và chỉnh `STOCK_TYPE_TOKENS` trong `data_cleaning.py`.

## 4. Lệnh chạy
```powershell
# Thử nhỏ trước (5 mã đầu)
python run_pipeline.py --mode full --limit 5

# Toàn thị trường, lịch sử từ 2015 (CÓ THỂ DỪNG BẰNG Ctrl+C VÀ CHẠY LẠI ĐỂ TIẾP TỤC)
python run_pipeline.py --mode full --with-profiles --with-financials

# Cập nhật hằng ngày (chỉ lấy phần mới; làm mới danh sách mã mỗi 7 ngày)
python run_pipeline.py --mode update

# Tuỳ chọn: --start 2020-01-01 --end 2025-12-31 --exchanges HOSE,HNX --symbols FPT,VNM --force --refresh-symbols
```
Ước lượng thời gian: mặc định giãn cách 3,1 giây/request (~19 request/phút, bảo thủ vì **chưa kiểm chứng giới hạn thật**). Với ~1.500–1.700 mã, giá mất khoảng 1,5–2 giờ; thêm hồ sơ + BCTC (mỗi mã nhiều request) có thể mất nhiều giờ → chạy nhiều đêm/lô là bình thường. Chỉnh `TV1_INTERVAL` hoặc `config.py` khi biết giới hạn tài khoản của bạn.

**Lập lịch hằng ngày (Windows Task Scheduler):** chương trình `...\TV1\.venv\Scripts\python.exe`, đối số `run_pipeline.py --mode update`, thư mục bắt đầu là `...\TV1`.

Mã thoát: `0` bình thường, `2` pipeline tự dừng vì nguồn giới hạn truy cập (chạy lại sau ít phút sẽ tiếp tục đúng chỗ).

## 5. Cơ chế an toàn / phục hồi
* Trạng thái từng mã (`success`, `no_data`, `source_error`, `data_error`, `rate_limited`) lưu trong SQLite; ghi **ngay sau từng mã**.
* Chạy lại: bỏ qua mã đã hoàn thành đến ngày kết thúc; mã mới/lỗi được thử lại; mã `success` chỉ tải từ phiên cuối đã có (chồng 1 phiên). Lùi `--start` về sớm hơn sẽ tải lại lịch sử.
* Retry hữu hạn (3 lần, chờ 2s/4s/8s); lỗi giới hạn tốc độ chờ 65s; **3 mã liên tiếp bị chặn → dừng** để khỏi bị khóa. Lỗi một mã không dừng mã khác. Nguồn dự phòng (VCI) chỉ dùng khi nguồn chính **lỗi**.
* `data_error` (có dữ liệu nhưng toàn bộ bị loại do sai) được tách khỏi `no_data` (nguồn trống).

## 6. Schema đầu ra
Giá: `date, symbol, open, high, low, close, volume, source, fetched_at` (+ `trading_value` chỉ khi nguồn có). Không có cột giá điều chỉnh vì chưa xác định được nguồn cung cấp.
Quy tắc: mã viết hoa; ngày `YYYY-MM-DD` (tz-aware được đổi về giờ Việt Nam rồi bỏ tz); **không** nội suy/điền 0; dòng sai (OHLC mâu thuẫn, giá ≤ 0, khối lượng âm, ngày sai/tương lai, thiếu giá) bị loại khỏi bảng sạch và ghi vào `quality/issues/`; trùng (mã, ngày) giữ bản mới nhất; thiếu khối lượng giữ dòng với NaN; biến động mạnh chỉ được đếm trong báo cáo, **không xóa**.

BCTC (dạng dài, `financial_statements/<MÃ>_quarter|year.csv`): `symbol, statement, period_type, period_label, item, item_id, unit, value, report_scope, published_date, source, fetched_at`. Quý và năm lưu **riêng**. `report_scope` (riêng/hợp nhất) và `published_date` để **trống** vì nguồn KBS không cung cấp trong bố cục đã đối chiếu — TV3 cần lưu ý, không được suy đoán.

## 7. Tích hợp (không cần gọi lại API)
```python
from data_loader import get_all_stock_symbols, get_price_history, load_stock_prices, load_financial_statements, load_company_info
symbols = get_all_stock_symbols()                       # list mã cổ phiếu từ symbols.csv
fpt = get_price_history("FPT", "2024-01-01", "2025-01-01")          # TV2
panel = load_stock_prices(["FPT", "VNM"], "2023-01-01")             # TV4 (nhiều mã)
bs = load_financial_statements("FPT", "year", "balance_sheet")      # TV3
```
Gọi trực tiếp API (có retry/giới hạn tốc độ): `fetch_stock_prices("FPT", start_date="2024-01-01", end_date="2025-01-01")`. Xem thêm `examples_integration.py`.

## 8. Kiểm thử
```powershell
python -m unittest discover -s tests -v
```
Các test dùng dữ liệu mock → kiểm tra logic, **không** chứng minh nguồn thật chạy đúng.

## 9. Giới hạn đã biết (trung thực)
1. Chưa chạy với nguồn thật; tên hàm/tham số đã đối chiếu tài liệu vnstock nhưng **cấu trúc phản hồi thực tế (cột, giá trị `type`, đơn vị giá) cần xác nhận bằng `--probe`**.
2. Giới hạn truy cập thật của nguồn/vnstock chưa kiểm chứng; mặc định bảo thủ.
3. Danh sách cổ phiếu: nguồn không nêu trạng thái niêm yết/hủy niêm yết nên **không có cột trạng thái**; mã phân loại bằng `type` của nguồn + danh sách ETF/TP/CW; mã chỉ nhận diện theo mẫu 3 chữ cái được gắn `pattern_inferred`, mã khó phân loại nằm ở `symbols_unclassified.csv`.
4. Hồ sơ doanh nghiệp: dùng `Company.overview()/profile()`; lưu nguyên cấu trúc nguồn (+ symbol, source, fetched_at). Phương thức nguồn không hỗ trợ sẽ được ghi `no_data`.
5. BCTC: chỉ bố cục KBS (cột kỳ `2024` / `2024-Q1`) được hỗ trợ; không có ngày công bố, riêng/hợp nhất.
6. Không phân biệt hoàn toàn được "ngày không giao dịch / chưa niêm yết / lỗi truy xuất" vì nguồn không cung cấp lịch giao dịch hay ngày niêm yết; `no_data` + khoảng trống >12 ngày chỉ để rà soát.
7. Chưa kiểm chứng dữ liệu "đầy đủ/chính xác tuyệt đối"; cần đối chiếu mẫu với nguồn thứ hai (HOSE/HNX, CafeF…).
