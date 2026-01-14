export interface ExamListFooterProps {
  lastUpdated?: Date | string; // DateオブジェクトまたはISO文字列
}

/**
 * 検査一覧フッターコンポーネント
 * - 最終更新日時を表示
 */
export function ExamListFooter({ lastUpdated }: ExamListFooterProps) {
  // 最終更新日時をフォーマット
  const formatLastUpdated = (date: Date | string | undefined): string => {
    if (!date) {
      // デフォルトは現在時刻
      const now = new Date();
      return now.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    }

    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  return (
    <footer className="mt-6 border-t border-gray-200 pt-4">
      <div className="text-right text-sm text-gray-500">
        最終更新: {formatLastUpdated(lastUpdated)}
      </div>
    </footer>
  );
}
