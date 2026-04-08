/**
 * ISO 風の日時文字列を「24年05月07日 14:30:45」形式で表示（ローカルタイムゾーン・24時間制）。
 * 年は西暦下2桁（YY）、月・日・時分秒はゼロ埋めで桁を揃える。
 */
export function formatDateTimeJa(iso: string): string {
	const s = iso?.trim();
	if (!s) {
		return "—";
	}
	const d = new Date(s);
	if (Number.isNaN(d.getTime())) {
		return iso;
	}
	const yy = String(d.getFullYear() % 100).padStart(2, "0");
	const mo = String(d.getMonth() + 1).padStart(2, "0");
	const day = String(d.getDate()).padStart(2, "0");
	const h = String(d.getHours()).padStart(2, "0");
	const mi = String(d.getMinutes()).padStart(2, "0");
	const sec = String(d.getSeconds()).padStart(2, "0");
	return `${yy}年${mo}月${day}日 ${h}:${mi}:${sec}`;
}
