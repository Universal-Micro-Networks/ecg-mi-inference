import { useState } from 'react';

export interface JudgmentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  examId?: string;
}

/**
 * 判定結果ダイアログコンポーネント
 * - リスクあり（陽性）の判定結果を表示
 * - クリップボードにコピー機能付き
 */
export function JudgmentDialog({ isOpen, onClose, examId }: JudgmentDialogProps) {
  const [copied, setCopied] = useState(false);

  const judgmentResult = 'リスクあり（陽性）';

  const handleCopyToClipboard = async () => {
    const textToCopy = `判定結果: ${judgmentResult}\n検査ID: ${examId || 'N/A'}\n判定日時: ${new Date().toLocaleString('ja-JP')}`;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('クリップボードへのコピーに失敗しました:', err);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* オーバーレイ */}
      <div
        className="fixed inset-0 z-50 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* ダイアログ */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="relative w-full max-w-2xl transform rounded-lg bg-white shadow-xl transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {/* コンテンツ */}
          <div className="px-8 py-10">
            {/* アイコンとメッセージ */}
            <div className="flex flex-col items-center justify-center text-center">
              {/* 警告アイコン */}
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-red-100">
                <svg
                  className="h-12 w-12 text-red-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>

              {/* 判定結果メッセージ */}
              <h2 className="mb-4 text-3xl font-bold text-gray-900">{judgmentResult}</h2>
              <p className="text-lg text-gray-600">
                心筋梗塞のリスクが検出されました。医師による確認をお願いします。
              </p>
            </div>
          </div>

          {/* フッター */}
          <div className="border-t border-gray-200 bg-gray-50 px-8 py-4">
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={handleCopyToClipboard}
                className={`flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors ${
                  copied
                    ? 'border-green-300 bg-green-50 text-green-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                } focus:outline-none focus:ring-2 focus:ring-gray-500`}
              >
                {copied ? (
                  <>
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span>コピーしました</span>
                  </>
                ) : (
                  <>
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                    <span>判定結果をクリップボードにコピー</span>
                  </>
                )}
              </button>
              <button
                onClick={onClose}
                className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                閉じる
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
