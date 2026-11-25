# Benchmark & Observability — Day 14

Nguyễn Đức Minh · 25/11/2026 · Linux, Python 3.12, HTTP local, mock LLM. Mỗi phép đo tải gửi 300 request. Eval tắt lỗi upstream ngẫu nhiên để đo riêng chất lượng.

## 1. SLO

Dùng ngưỡng mặc định của script: p95 500 ms, lỗi 2%, accuracy tối thiểu 80%. Mục tiêu sau sửa KB là 100% trên bộ câu hỏi công khai.

## 2. Hiệu năng

| Concurrency | RPS | p50 ms | p95 ms | p99 ms | Lỗi | Đạt cả hai SLO |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 4.14 | 188.5 | 223.0 | 1698.8 | 2.00% | True |
| 10 | 42.52 | 187.4 | 219.1 | 1680.3 | 1.67% | True |
| 50 | 105.49 | 191.0 | 253.7 | 1705.6 | 1.00% | True |
| 100 | 90.24 | 301.4 | 2236.1 | 2498.2 | 1.67% | False |

| Tỷ lệ chậm | Trung bình ms | p95 ms | p99 ms |
|---:|---:|---:|---:|
| 0 | 188.8 | 216.8 | 231.0 |
| 0.03 | 260.6 | 233.9 | 1710.9 |
| 0.1 | 367.7 | 1685.5 | 1710.2 |

Request chậm hiếm xuất hiện rõ ở p99. Khi tỷ lệ tăng lên 10%, cả p95 cũng có thể rơi vào nhóm chậm. HTTP song song giúp tăng thông lượng khi mock đợi I/O, nhưng hàng đợi và chi phí xử lý giới hạn mức tăng.

## 3. Chất lượng

| Phiên bản | Đúng/tổng | Accuracy | Tokens/câu | Tổng USD | USD/câu đúng | Gate |
|---|---:|---:|---:|---:|---:|---|
| v1 | 1/23 | 4.3% | 57.4 | 0.000408 | 0.00040815 | FAIL |
| v2 | 21/23 | 91.3% | 108.7 | 0.000756 | 3.599e-05 | PASS |
| v2_fixed | 23/23 | 100.0% | 112.8 | 0.000783 | 3.404e-05 | PASS |

V2 ban đầu thiếu tài liệu cho security-02 (JWT, chữ ký, hết hạn) và scaling-03 (HPA, CPU, memory, custom metrics). Bổ sung hai tài liệu vào knowledge base và chạy lại cùng dataset. Trong CI, khởi động agent, chờ health, chạy run_eval.py với --min-accuracy 1.0 và --baseline reports/eval_v2.json. Đặt job làm required check để exit code khác 0 chặn merge.

## 4–5. Observability và scaling

### Scaling với Locust

Hai lượt headless dùng 100 users, ramp 10 users/giây và thời lượng 120 giây. Số liệu lấy từ dòng Aggregated của hai CSV.

| Replica | Request | Lỗi | Tỷ lệ lỗi | RPS | p50 ms | p95 ms | p99 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7443 | 68 | 0.91% | 63.99 | 200 | 670 | 1700 |
| 3 | 7742 | 68 | 0.88% | 64.97 | 200 | 360 | 1700 |

Tăng từ 1 lên 3 replica giảm p95 khoảng 46,3%, tăng RPS khoảng 1,5% và giữ p99 ở 1.700 ms. Với ngưỡng p95 500 ms và tỷ lệ lỗi 2% của bài benchmark local, lượt 3 replica đạt cả hai ngưỡng. Dữ liệu gốc nằm trong [CSV 1 replica](benchmark-results/scale_1_stats.csv) và [CSV 3 replica](benchmark-results/scale_3_stats.csv).

### Grafana và Prometheus

Sau hai lượt đo, áp dụng MOCK_ERROR_RATE=0.2 và MOCK_SLOW_RATE=0.3, chạy 30 Locust users trên 3 replica. [Grafana](screenshots/grafana-dashboard.png) ghi nhận 15,3 req/s, 17,64% lỗi và p95 khoảng 1,90 giây. Hai alert cùng firing trong [ảnh Prometheus](screenshots/prometheus-alert-firing.png).

| Alert | Ngưỡng và thời gian duy trì | Giá trị lúc chụp | Thời gian đến firing ước tính |
|---|---|---:|---:|
| AgentHighErrorRate | Lỗi vượt 5% trong 1 phút | 19,70% | Khoảng 3 phút 01 giây |
| AgentHighLatencyP95 | p95 vượt 1 giây trong 2 phút | 1,891 giây | Khoảng 4 phút 09 giây |

Mốc áp dụng cấu hình là 14:23:12 UTC. Thời gian firing được ước tính từ dấu giờ trong tên ảnh (14:31:33 và 14:31:41 UTC), trừ thời gian Active Since (6m20.243s và 6m19.595s), rồi cộng thời gian duy trì của mỗi rule. Các mốc này chưa được đối chiếu với lịch sử chuỗi ALERTS của Prometheus.

### Jaeger và structured logs

| Trace | Trace ID | Kết quả |
|---|---|---|
| [Chậm](screenshots/jaeger-slow-trace.png) | `b215a76a3efe4f7bdbe6c6796a55e4ad` | HTTP 200 sau 1.673,6 ms. Mock LLM mất 1.649,7 ms, khoảng 98,6% thời gian xử lý. |
| [Lỗi](screenshots/jaeger-error-trace.png) | `e6650605f064dc30e72dcba699a4273e` | HTTP 503 sau 117,8 ms. Log ghi lỗi upstream từ mock LLM. |

```jsonl
{"event":"llm_call","trace_id":"b215a76a3efe4f7bdbe6c6796a55e4ad","request_id":"7650988d00eb","llm_ms":1649.7}
{"event":"http_request","trace_id":"b215a76a3efe4f7bdbe6c6796a55e4ad","request_id":"7650988d00eb","status":200,"ms":1673.6}
{"event":"llm_error","trace_id":"e6650605f064dc30e72dcba699a4273e","request_id":"06b6d5a24026","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
{"event":"http_request","trace_id":"e6650605f064dc30e72dcba699a4273e","request_id":"06b6d5a24026","status":503,"ms":117.8}
```

## 6. Kết luận

Theo dõi p95/p99 để phát hiện nhóm request chậm, cost/câu đúng để so sánh chi phí với chất lượng và trace_id để nối span chậm với log. Có thể bổ sung cảnh báo khi accuracy trên bộ kiểm tra định kỳ giảm dưới ngưỡng.
