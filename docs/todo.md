# TODO メモ

最終更新: 2026-04-06（更新）

## authorization 実装後の軽微警告（対応済み）

### Frontend（完了）

- `frontend/src/features/auth/components/LoginPage.tsx`
  - inline style を `auth.css` へ移管済み
- `frontend/src/features/auth/components/PasswordStrengthIndicator.tsx`
  - inline style を `auth.css` へ移管済み
- `frontend/tsconfig.app.json`
  - `forceConsistentCasingInFileNames: true` 追加済み

## 残タスク（軽微）

1. Backend テスト時の DeprecationWarning 対応
   - FastAPI の `@app.on_event("startup")` を lifespan へ移行
   - `datetime.utcnow()` の使用を timezone-aware な `datetime.now(timezone.utc)` へ置換
