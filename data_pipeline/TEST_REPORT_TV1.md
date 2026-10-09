# Báo cáo kiểm thử TV1

Lệnh: `python -m unittest discover -s tests -v` (Python 3.12, pandas 3.0.2, numpy 2.4.4)
Kết quả: **26 test, tất cả đạt** (log đầy đủ: tests/last_test_run.txt).

Phạm vi: toàn bộ test dùng **dữ liệu mock** (không có mạng, chưa cài vnstock) → xác nhận logic, không xác nhận nguồn thật.

| Yêu cầu | Test |
|---|---|
| Chuẩn hóa dữ liệu hợp lệ / múi giờ | test_valid_standardization, test_timezone_aware_dates |
| Thiếu / sai kiểu | test_wrong_types_and_missing, test_missing_required_column, test_missing_volume_kept_as_nan, test_empty_input |
| Trùng | test_duplicates_keep_last, test_rerun_no_duplicates_and_skip |
| OHLC sai, giá/khối lượng âm | test_ohlc_invalid_negative_zero |
| Biến động lớn không bị xóa | test_big_move_not_removed_and_zero_volume_kept |
| Nguồn rỗng / mã không có dữ liệu | test_fetch_prices_fallback_and_empty, test_continue_after_failure_and_resume |
| Lỗi mạng, retry hữu hạn, giới hạn truy cập, SystemExit | test_retry_*, test_rate_limit_and_systemexit, test_all_sources_fail, test_circuit_breaker_on_rate_limit |
| Tiếp tục sau lỗi một mã / chạy lại | test_continue_after_failure_and_resume, test_incremental_update_and_forced_overlap, test_extend_history_backwards_refetches |
| Đọc dữ liệu đã lưu | test_read_saved_data_and_filters |
| Lọc cổ phiếu vs ETF/CW/chưa xác định, tự phát hiện danh sách | test_symbol_classification, test_symbols_discovery_and_save |
| BCTC quý/năm không trộn, trường thiếu để trống | test_statement_long_format, test_financial_statements_mocked |
| Báo cáo chất lượng | test_quality_report |

Chưa kiểm thử (cần mạng): gọi vnstock thật, giới hạn truy cập thật, đơn vị giá thật, bố cục thật của Company/Finance.
