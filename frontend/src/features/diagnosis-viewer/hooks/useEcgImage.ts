import { useEffect, useState } from "react";

import { apiFetch } from "../../../lib/auth";

/**
 * 心電図 PNG を取得する。404 / 422 / その他失敗時は imageUrl=null（パネルは空メッセージ表示）。
 */
export const useEcgImage = (examinationId: string, cacheKey = 0) => {
	const [imageUrl, setImageUrl] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		if (!examinationId) {
			setImageUrl((prev) => {
				if (prev) URL.revokeObjectURL(prev);
				return null;
			});
			setIsLoading(false);
			return;
		}

		let objectUrl: string | null = null;
		const controller = new AbortController();

		const fetchImage = async () => {
			try {
				const qs = cacheKey ? `?v=${encodeURIComponent(String(cacheKey))}` : "";
				const response = await apiFetch(
					`/api/examinations/${examinationId}/ecg-image${qs}`,
					{
						signal: controller.signal,
					},
				);

				if (response.status === 404 || response.status === 422) {
					setImageUrl(null);
					return;
				}

				if (!response.ok) {
					setImageUrl(null);
					return;
				}

				const blob = await response.blob();
				if (controller.signal.aborted) {
					return;
				}
				objectUrl = URL.createObjectURL(blob);
				setImageUrl(objectUrl);
			} catch (fetchError) {
				if (
					fetchError instanceof DOMException &&
					fetchError.name === "AbortError"
				) {
					return;
				}
				setImageUrl(null);
			} finally {
				if (!controller.signal.aborted) {
					setIsLoading(false);
				}
			}
		};

		setImageUrl((prev) => {
			if (prev) URL.revokeObjectURL(prev);
			return null;
		});
		setIsLoading(true);
		fetchImage();

		return () => {
			controller.abort();
			if (objectUrl) {
				URL.revokeObjectURL(objectUrl);
			}
		};
	}, [examinationId, cacheKey]);

	return { imageUrl, isLoading };
};
