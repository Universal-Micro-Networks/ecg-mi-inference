import type { ExamListItem } from '../types';

// ランダムな日本語の名前を生成
const firstNames = [
  '太郎',
  '花子',
  '一郎',
  '次郎',
  '三郎',
  '美咲',
  'さくら',
  'あかり',
  '健太',
  '大輔',
  '優子',
  '麻衣',
  '翔太',
  '美香',
  '直樹',
];

const lastNames = [
  '山田',
  '佐藤',
  '鈴木',
  '田中',
  '渡辺',
  '伊藤',
  '中村',
  '小林',
  '加藤',
  '吉田',
  '山本',
  '松本',
  '井上',
  '木村',
  '林',
];

// ランダムな整数を生成
const randomInt = (min: number, max: number): number => {
  return Math.floor(Math.random() * (max - min + 1)) + min;
};

// ランダムな日時を生成（過去30日間）
const randomDateTime = (): string => {
  const now = new Date();
  const daysAgo = randomInt(0, 30);
  const hours = randomInt(0, 23);
  const minutes = randomInt(0, 59);
  const date = new Date(now);
  date.setDate(date.getDate() - daysAgo);
  date.setHours(hours, minutes, 0, 0);
  return date.toISOString();
};

// ランダムな性別を生成
const randomGender = (): ExamListItem['gender'] => {
  const genders: ExamListItem['gender'][] = ['male', 'female'];
  return genders[randomInt(0, genders.length - 1)];
};

/**
 * ランダムな検査データを生成
 */
export const generateMockExams = (count: number): ExamListItem[] => {
  const exams: ExamListItem[] = [];

  for (let i = 0; i < count; i++) {
    const lastName = lastNames[randomInt(0, lastNames.length - 1)];
    const firstName = firstNames[randomInt(0, firstNames.length - 1)];
    const patientId = `P-${String(i + 1).padStart(3, '0')}`;
    const gender = randomGender();
    const age = randomInt(20, 90);

    exams.push({
      id: `exam-${String(i + 1).padStart(3, '0')}`,
      examDateTime: randomDateTime(),
      patientId,
      patientName: `${lastName}${firstName}`,
      gender,
      age,
    });
  }

  // 検査日時で降順ソート（新しい順）
  return exams.sort((a, b) => {
    return new Date(b.examDateTime).getTime() - new Date(a.examDateTime).getTime();
  });
};
