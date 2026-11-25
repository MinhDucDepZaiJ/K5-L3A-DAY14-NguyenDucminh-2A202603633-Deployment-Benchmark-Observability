# Part 3 — Cloud Deployment

**Trạng thái:** Chưa có URL public hoặc kết quả kiểm tra cloud. Đích triển khai là Railway, thư mục nguồn `06-lab-complete/`. Tạo Redis trong cùng project, nối `REDIS_URL` của agent với URL Redis nội bộ và đặt `AGENT_API_KEY` bằng secret riêng. Dịch vụ đọc cổng từ `PORT`. Có thể cấu hình `RATE_LIMIT_PER_MINUTE`, `DAILY_BUDGET_USD` và `ENVIRONMENT=production`.

## Kiểm tra trên Ubuntu sau khi cấp domain

```bash
read -rp 'Public URL: ' BASE
read -rsp 'Agent API key: ' AGENT_API_KEY
echo
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Mã kỳ vọng lần lượt là 200, 200, 401, 200. Sau khi kiểm tra, ghi URL, kết quả thực tế và lưu ba ảnh dashboard.png, running.png, test.png trong screenshots/.
