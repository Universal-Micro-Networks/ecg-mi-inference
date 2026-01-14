import { FormEvent, useId, useState } from 'react';

export interface ExamSearchFilters {
  examDate?: string; // YYYY-MM-DD形式
  patientId?: string;
  patientName?: string;
}

export interface ExamSearchFormProps {
  initialFilters?: ExamSearchFilters;
  onSearch?: (filters: ExamSearchFilters) => void;
  onClear?: () => void;
}

/**
 * 診察（検査）検索フォーム
 * - 検査日（カレンダー選択）、患者ID（フリーテキスト）、氏名（フリーテキスト）
 * - クリアボタンと更新ボタンを提供
 */
export function ExamSearchForm({
  initialFilters,
  onSearch,
  onClear,
}: ExamSearchFormProps) {
  const examDateId = useId();
  const patientIdId = useId();
  const patientNameId = useId();

  const [examDate, setExamDate] = useState(initialFilters?.examDate || '');
  const [patientId, setPatientId] = useState(initialFilters?.patientId || '');
  const [patientName, setPatientName] = useState(initialFilters?.patientName || '');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const filters: ExamSearchFilters = {};
    if (examDate) filters.examDate = examDate;
    if (patientId.trim()) filters.patientId = patientId.trim();
    if (patientName.trim()) filters.patientName = patientName.trim();
    onSearch?.(filters);
  };

  const handleClear = () => {
    setExamDate('');
    setPatientId('');
    setPatientName('');
    onClear?.();
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex flex-wrap items-end gap-3">
        {/* 検査日 */}
        <div className="flex flex-col">
          <label htmlFor={examDateId} className="mb-1 text-xs font-medium text-gray-700">
            検査日
          </label>
          <input
            id={examDateId}
            name="examDate"
            type="date"
            value={examDate}
            onChange={(e) => setExamDate(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          />
        </div>

        {/* 患者ID */}
        <div className="flex flex-col">
          <label htmlFor={patientIdId} className="mb-1 text-xs font-medium text-gray-700">
            患者ID
          </label>
          <input
            id={patientIdId}
            name="patientId"
            type="text"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="例: P-001"
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            autoComplete="off"
          />
        </div>

        {/* 氏名 */}
        <div className="flex flex-col">
          <label htmlFor={patientNameId} className="mb-1 text-xs font-medium text-gray-700">
            氏名
          </label>
          <input
            id={patientNameId}
            name="patientName"
            type="text"
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            placeholder="例: 山田太郎"
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            autoComplete="off"
          />
        </div>

        {/* ボタン群 */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleClear}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-200"
          >
            クリア
          </button>
          <button
            type="submit"
            className="flex items-center gap-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            <span>🔄</span>
            <span>更新</span>
          </button>
        </div>
      </div>
    </form>
  );
}

