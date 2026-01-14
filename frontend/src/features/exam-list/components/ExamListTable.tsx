import { ExamListItem } from '../types';
import { ExamListPagination } from './ExamListPagination';

export interface ExamListTableProps {
  exams: ExamListItem[];
  isLoading?: boolean;
  error?: string | null;
  onExamSelect?: (examId: string) => void;
  // ページネーション関連
  currentPage?: number;
  itemsPerPage?: number;
  onPageChange?: (page: number) => void;
}

/**
 * 検査一覧テーブルコンポーネント
 * - 測定日時、患者ID、氏名、年齢、性別を表示
 * - 測定日時は日付と時刻を1行で表示
 */
export function ExamListTable({
  exams,
  isLoading = false,
  error = null,
  onExamSelect,
  currentPage = 1,
  itemsPerPage = 10,
  onPageChange,
}: ExamListTableProps) {
  // ページネーション用のデータを計算
  const totalItems = exams.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedExams = exams.slice(startIndex, endIndex);

  const handlePageChange = (page: number) => {
    onPageChange?.(page);
    // ページ変更時にテーブルの上部にスクロール
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  // 日付と時刻を分離してフォーマット
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
    switch (gender) {
      case 'male':
        return '男性';
      case 'female':
        return '女性';
      default:
        return '-';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-300 bg-red-50 p-4">
        <p className="text-sm font-medium text-red-800">エラーが発生しました</p>
        <p className="mt-1 text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (exams.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
        <p className="text-gray-500">該当する検査データがありません</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
      {/* 上部ページネーション */}
      {totalPages > 1 && (
        <ExamListPagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          itemsPerPage={itemsPerPage}
          totalItems={totalItems}
        />
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                測定日時
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                氏名
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                患者ID
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                年齢
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                性別
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {paginatedExams.map((exam) => {
              const { dateStr, timeStr } = formatDateTime(exam.examDateTime);
              return (
                <tr
                  key={exam.id}
                  className={onExamSelect ? 'cursor-pointer hover:bg-gray-50' : ''}
                  onClick={() => onExamSelect?.(exam.id)}
                >
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {dateStr} {timeStr}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {exam.patientName}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {exam.patientId}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {exam.age}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {formatGender(exam.gender)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 下部ページネーション */}
      {totalPages > 1 && (
        <ExamListPagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          itemsPerPage={itemsPerPage}
          totalItems={totalItems}
        />
      )}
    </div>
  );
}
