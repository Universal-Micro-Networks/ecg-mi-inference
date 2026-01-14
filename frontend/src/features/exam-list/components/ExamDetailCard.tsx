import type { ExamListItem } from '../types';
import { EcgLeadChart } from './EcgLeadChart';

export interface ExamDetailCardProps {
  exam: ExamListItem | null;
  isOpen: boolean;
  onClose: () => void;
  onJudgment?: (examId: string) => void;
}

// 心電図12誘導の定義
const ECG_LEADS = [
  ['I', 'II'],
  ['III', 'aVR'],
  ['aVL', 'aVF'],
  ['V1', 'V2'],
  ['V3', 'V4'],
  ['V5', 'V6'],
];

/**
 * 検査詳細カードコンポーネント
 * - 右からスライドインするサイドパネル形式
 * - 検査の詳細情報を表示
 */
export function ExamDetailCard({
  exam,
  isOpen,
  onClose,
  onJudgment,
}: ExamDetailCardProps) {
  if (!exam) {
    return null;
  }

  // 日付と時刻をフォーマット
  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    const dateStr = date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    const timeStr = date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    return { dateStr, timeStr };
  };

  // 性別を日本語で表示
  const formatGender = (gender: ExamListItem['gender']) => {
    return gender === 'male' ? '男性' : '女性';
  };

  const { dateStr, timeStr } = formatDateTime(exam.examDateTime);

  return (
    <>
      {/* オーバーレイ（背景を暗くする） */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* サイドパネル */}
      <div
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-5xl transform bg-white shadow-xl transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* ヘッダー */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-gray-900">検査詳細</h2>
            <button
              onClick={onClose}
              className="rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="閉じる"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* コンテンツ */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="space-y-6">
              {/* 患者氏名、患者ID、性別、年齢、検査日時（1行） */}
              <div className="grid grid-cols-5 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">患者氏名</label>
                  <p className="mt-1 text-base text-gray-900">{exam.patientName}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">患者ID</label>
                  <p className="mt-1 text-base text-gray-900">{exam.patientId}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">性別</label>
                  <p className="mt-1 text-base text-gray-900">{formatGender(exam.gender)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">年齢</label>
                  <p className="mt-1 text-base text-gray-900">{exam.age}歳</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">検査日時</label>
                  <p className="mt-1 text-base text-gray-900">
                    {dateStr} {timeStr}
                  </p>
                </div>
              </div>

              {/* 心電図12誘導グラフエリア */}
              <div className="mt-6">
                <label className="mb-3 block text-sm font-medium text-gray-700">
                  心電図12誘導
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {ECG_LEADS.map((row, rowIndex) =>
                    row.map((lead) => (
                      <div key={lead} className="h-32">
                        <EcgLeadChart leadName={lead} />
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* フッター */}
          <div className="border-t border-gray-200 px-6 py-4">
            <div className="flex items-center justify-end">
              <button
                onClick={() => {
                  onJudgment?.(exam.id);
                }}
                className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                判定
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
