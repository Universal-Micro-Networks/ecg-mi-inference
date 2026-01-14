/**
 * 心電図誘導チャートコンポーネント（プレースホルダー）
 * - 各誘導の波形を表示するためのコンポーネント
 * - 現時点ではプレースホルダーとして実装
 */
export interface EcgLeadChartProps {
  leadName: string; // 誘導名（例: "I", "II", "V1"など）
  data?: number[]; // 心電図データ（将来的に使用）
}

export function EcgLeadChart({ leadName, data }: EcgLeadChartProps) {
  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-300 bg-white p-3 shadow-sm">
      <div className="mb-2 text-xs font-semibold text-gray-700">{leadName}</div>
      <div className="flex-1 overflow-hidden rounded bg-gray-50">
        {/* グラフエリア（プレースホルダー） */}
        <div className="flex h-full items-center justify-center">
          <svg
            className="h-full w-full"
            viewBox="0 0 200 100"
            preserveAspectRatio="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* グリッド線 */}
            <defs>
              <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#e5e7eb" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="200" height="100" fill="url(#grid)" />
            {/* ベースライン */}
            <line
              x1="0"
              y1="50"
              x2="200"
              y2="50"
              stroke="#9ca3af"
              strokeWidth="1"
              strokeDasharray="2,2"
            />
            {/* サンプル波形（正弦波） */}
            <path
              d="M 0,50 Q 50,30 100,50 T 200,50"
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
