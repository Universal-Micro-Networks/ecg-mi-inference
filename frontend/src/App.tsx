import type { ExamSearchFilters } from '@/features/exam-list/components';
import {
  ExamDetailCard,
  ExamListFooter,
  ExamListTable,
  ExamSearchForm,
  JudgmentDialog,
} from '@/features/exam-list/components';
import type { ExamListItem } from '@/features/exam-list/types';
import { generateMockExams } from '@/features/exam-list/utils/generateMockData';
import { useState } from 'react';
import { Route, Routes } from 'react-router-dom';

// ランダムなモックデータ100件を生成
const mockExams = generateMockExams(100);

function App() {
  const [exams, setExams] = useState<ExamListItem[]>(mockExams);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const [selectedExam, setSelectedExam] = useState<ExamListItem | null>(null);
  const [isDetailCardOpen, setIsDetailCardOpen] = useState(false);
  const [isJudgmentDialogOpen, setIsJudgmentDialogOpen] = useState(false);
  const [judgmentExamId, setJudgmentExamId] = useState<string | null>(null);

  const handleSearch = (filters: ExamSearchFilters) => {
    // TODO: バックエンドAPI呼び出しを実装
    // eslint-disable-next-line no-console
    console.log('search filters:', filters);
    // 現時点ではモックデータを表示
    setExams(mockExams);
    // 検索実行時に最終更新日時を更新し、ページを1にリセット
    setLastUpdated(new Date());
    setCurrentPage(1);
  };

  const handleClear = () => {
    // TODO: クリア時の処理を実装
    // eslint-disable-next-line no-console
    console.log('filters cleared');
    setExams(mockExams);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleExamSelect = (examId: string) => {
    const exam = exams.find((e: ExamListItem) => e.id === examId);
    if (exam) {
      setSelectedExam(exam);
      setIsDetailCardOpen(true);
    }
  };

  const handleCloseDetailCard = () => {
    setIsDetailCardOpen(false);
    // アニメーション完了後に選択をクリア
    setTimeout(() => {
      setSelectedExam(null);
    }, 300);
  };

  const handleJudgment = (examId: string) => {
    // TODO: 判定処理を実装（心筋梗塞リスク推論の実行）
    // eslint-disable-next-line no-console
    console.log('judgment requested for exam:', examId);
    setJudgmentExamId(examId);
    setIsJudgmentDialogOpen(true);
  };

  const handleCloseJudgmentDialog = () => {
    setIsJudgmentDialogOpen(false);
    setTimeout(() => {
      setJudgmentExamId(null);
    }, 300);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto flex flex-col gap-4 py-6 px-4 sm:px-6 lg:px-8">
          <ExamSearchForm
            initialFilters={{
              examDate: new Date().toISOString().split('T')[0], // 当日を初期値に設定
            }}
            onSearch={handleSearch}
            onClear={handleClear}
          />
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route
            path="/"
            element={
              <div className="px-4">
                <ExamListTable
                  exams={exams}
                  isLoading={isLoading}
                  error={error}
                  onExamSelect={handleExamSelect}
                  currentPage={currentPage}
                  itemsPerPage={itemsPerPage}
                  onPageChange={handlePageChange}
                />
                <ExamListFooter lastUpdated={lastUpdated} />
              </div>
            }
          />
        </Routes>
      </main>

      {/* 検査詳細カード */}
      <ExamDetailCard
        exam={selectedExam}
        isOpen={isDetailCardOpen}
        onClose={handleCloseDetailCard}
        onJudgment={handleJudgment}
      />

      {/* 判定結果ダイアログ */}
      <JudgmentDialog
        isOpen={isJudgmentDialogOpen}
        onClose={handleCloseJudgmentDialog}
        examId={judgmentExamId || undefined}
      />
    </div>
  );
}

export default App;
