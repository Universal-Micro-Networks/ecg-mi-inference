import { ExamSearchForm } from '@/features/exam-list/components/ExamSearchForm';
import { Route, Routes } from 'react-router-dom';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto flex flex-col gap-4 py-6 px-4 sm:px-6 lg:px-8">
          <ExamSearchForm
            initialFilters={{
              examDate: new Date().toISOString().split('T')[0], // 当日を初期値に設定
            }}
            onSearch={(filters) => {
              // TODO: 検索結果の画面遷移 / クエリ同期などを実装
              // eslint-disable-next-line no-console
              console.log('search filters:', filters);
            }}
            onClear={() => {
              // TODO: クリア時の処理を実装
              // eslint-disable-next-line no-console
              console.log('filters cleared');
            }}
          />
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<div className="px-4 py-6">Welcome to ECG MI Inference</div>} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
