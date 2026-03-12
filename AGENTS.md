# Hướng dẫn nhanh cho Codex ở phiên mới

Nếu bạn vừa mở repo này, hãy đọc theo thứ tự sau trước khi sửa code:

1. `README.md`
2. `docs/codex-handoff.md`
3. `docs/onboarding.md`
4. `docs/botkit.md`

## Boundary quan trọng

- `sdk/transports.py`: chỉ chứa Telegram primitives, không chứa bot-specific parsing.
- `sdk/client.py`: facade public `TelegramSDK`.
- `sdk/services/bot_search.py`: wrapper/service cho `@en_SearchBot` và legacy bot flows.
- `sdk/botkit/`: bot orchestration layer (`BotSDK`, `BaseBotAdapter`, adapter cụ thể).
- `sdk/botkit/adapters/en_searchbot.py`: luồng thật cho `@en_SearchBot`, bao gồm pagination, retry, checkpoint/resume.

## Trạng thái hiện tại

- `@en_SearchBot` đã dùng được để search keyword.
- Full crawl đã được harden theo hướng: hoặc đi đủ số trang bot báo, hoặc fail rõ ràng.
- Đã có mode crawl lớn với:
  - `checkpoint_path`
  - `resume_checkpoint`
  - `keep_page_snapshots_in_memory`
  - `page_snapshot_memory_limit`

## Lệnh verify cơ bản

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m compileall sdk tests examples
```

## Lưu ý vận hành

- Không commit runtime artifact như file checkpoint JSONL trong `artifacts/`.
- Nếu sửa `@en_SearchBot`, phải giữ nguyên nguyên tắc: không trả thiếu trang trong im lặng.
- Nếu thêm bot mới, đi qua `sdk/botkit/adapters/`, không nhét logic vào transport.
